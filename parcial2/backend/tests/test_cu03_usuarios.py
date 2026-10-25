"""Pruebas de CU-03: Administrar usuarios y roles del tenant.
Verifica:
1. Listar usuarios con aislamiento multitenant estricto (Luna solo ve usuarios de Luna, Andina solo de Andina).
2. Crear usuario con hash de contrasena y rol.
3. El mismo correo puede existir en dos empresas distintas.
4. Duplicados dentro del mismo tenant se rechazan con 409.
5. Limite de usuarios por plan de suscripcion (ej: Plan Basico max 3 usuarios).
6. Actualizar usuario (PATCH y PUT).
7. Eliminar usuario y proteccion para no autoeliminarse.
8. Acceso cruzado por ID directo devuelve 404.
9. Permisos: solo usuarios con rol 'admin' pueden gestionar usuarios.
"""
from __future__ import annotations


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_aislamiento_usuarios(client, token_luna, token_andina):
    # Luna lista sus usuarios
    r_luna = client.get("/api/v1/usuarios", headers=_h(token_luna))
    assert r_luna.status_code == 200
    emails_luna = [u["email"] for u in r_luna.json()]
    assert "ana@boutique-luna.bo" in emails_luna
    assert "encargado@boutique-luna.bo" in emails_luna
    assert "rodrigo@modaandina.bo" not in emails_luna

    # Andina lista sus usuarios
    r_andina = client.get("/api/v1/usuarios", headers=_h(token_andina))
    assert r_andina.status_code == 200
    emails_andina = [u["email"] for u in r_andina.json()]
    assert "rodrigo@modaandina.bo" in emails_andina
    assert "ana@boutique-luna.bo" not in emails_andina


def test_crear_usuario_y_login(client, token_luna):
    body = {
        "nombre": "Carlos Cajero",
        "apellido": "Vaca",
        "email": "carlos@boutique-luna.bo",
        "password": "Password123",
        "telefono": "70099887",
        "rol": "cajero",
    }
    r = client.post("/api/v1/usuarios", json=body, headers=_h(token_luna))
    assert r.status_code == 201
    nuevo = r.json()
    assert nuevo["nombre"] == "Carlos Cajero"
    assert nuevo["apellido"] == "Vaca"
    assert nuevo["email"] == "carlos@boutique-luna.bo"
    assert nuevo["rol"] == "cajero"
    assert "roles" in nuevo and "cajero" in nuevo["roles"]
    assert "password_hash" not in nuevo  # No debe exponer el hash

    # El nuevo usuario puede iniciar sesion
    r_login = client.post(
        "/api/v1/auth/login",
        json={
            "codigo_tenant": "luna",
            "email": "carlos@boutique-luna.bo",
            "password": "Password123",
        },
    )
    assert r_login.status_code == 200
    token_carlos = r_login.json()["access_token"]
    assert token_carlos is not None


def test_rechazo_correo_duplicado_mismo_tenant(client, token_luna):
    body = {
        "nombre": "Intento Duplicado",
        "email": "ana@boutique-luna.bo",
        "password": "OtraPassword123",
        "rol": "cajero",
    }
    r = client.post("/api/v1/usuarios", json=body, headers=_h(token_luna))
    assert r.status_code == 409
    assert "Ya existe un usuario con correo" in r.json()["detail"]


def test_mismo_correo_permitido_en_diferentes_tenants(client, token_luna, token_andina):
    correo_compartido = "empleado.compartido@empresa.bo"

    r1 = client.post(
        "/api/v1/usuarios",
        json={"nombre": "Empleado Luna", "email": correo_compartido, "password": "Password123", "rol": "cajero"},
        headers=_h(token_luna),
    )
    assert r1.status_code == 201

    r2 = client.post(
        "/api/v1/usuarios",
        json={"nombre": "Empleado Andina", "email": correo_compartido, "password": "Password123", "rol": "cajero"},
        headers=_h(token_andina),
    )
    assert r2.status_code == 201


def test_rechazo_limite_usuarios_por_plan(client, token_andina):
    # Andina tiene plan Basico (max_usuarios=3) y ya tiene a Rodrigo (1 usuario).
    # Crear usuario 2
    r2 = client.post(
        "/api/v1/usuarios",
        json={"nombre": "Usuario 2", "email": "u2@modaandina.bo", "password": "Password123", "rol": "cajero"},
        headers=_h(token_andina),
    )
    assert r2.status_code == 201

    # Crear usuario 3 (limite alcanzado)
    r3 = client.post(
        "/api/v1/usuarios",
        json={"nombre": "Usuario 3", "email": "u3@modaandina.bo", "password": "Password123", "rol": "cajero"},
        headers=_h(token_andina),
    )
    assert r3.status_code == 201

    # Crear usuario 4 (debe ser rechazado con 409)
    r4 = client.post(
        "/api/v1/usuarios",
        json={"nombre": "Usuario 4", "email": "u4@modaandina.bo", "password": "Password123", "rol": "cajero"},
        headers=_h(token_andina),
    )
    assert r4.status_code == 409
    detail = r4.json()["detail"]
    assert "Limite alcanzado para usuarios" in detail
    assert "3 de 3" in detail
    assert "Basico" in detail


def test_actualizar_usuario_patch_y_put(client, token_luna):
    # Crear usuario temporal
    r_crear = client.post(
        "/api/v1/usuarios",
        json={"nombre": "Pedro", "email": "pedro@boutique-luna.bo", "password": "Password123", "rol": "cajero"},
        headers=_h(token_luna),
    )
    user_id = r_crear.json()["id"]

    # PATCH: ascender a encargado
    r_patch = client.patch(
        f"/api/v1/usuarios/{user_id}",
        json={"rol": "encargado", "apellido": "Perez"},
        headers=_h(token_luna),
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["rol"] == "encargado"
    assert r_patch.json()["apellido"] == "Perez"

    # PUT: desactivar usuario
    r_put = client.put(
        f"/api/v1/usuarios/{user_id}",
        json={"activo": False},
        headers=_h(token_luna),
    )
    assert r_put.status_code == 200
    assert r_put.json()["activo"] is False


def test_eliminar_usuario_y_proteccion_autoeliminacion(client, token_luna):
    # Crear usuario para borrar
    r_crear = client.post(
        "/api/v1/usuarios",
        json={"nombre": "Para Borrar", "email": "borrar@boutique-luna.bo", "password": "Password123", "rol": "cajero"},
        headers=_h(token_luna),
    )
    user_id = r_crear.json()["id"]

    # Borrarlo exitosamente
    r_del = client.delete(f"/api/v1/usuarios/{user_id}", headers=_h(token_luna))
    assert r_del.status_code == 204

    # Verificar que ya no existe (404)
    r_get = client.get(f"/api/v1/usuarios/{user_id}", headers=_h(token_luna))
    assert r_get.status_code == 404

    # Intentar autoeliminarse como admin logueado
    r_me = client.get("/api/v1/auth/me", headers=_h(token_luna))
    my_id = r_me.json()["user_id"]
    r_self_del = client.delete(f"/api/v1/usuarios/{my_id}", headers=_h(token_luna))
    assert r_self_del.status_code == 400
    assert "No puedes eliminar tu propia cuenta" in r_self_del.json()["detail"]


def test_acceso_cruzado_usuario_devuelve_404(client, token_luna, token_andina):
    # Rodrigo es de Andina
    r_andina = client.get("/api/v1/usuarios", headers=_h(token_andina))
    id_rodrigo = r_andina.json()[0]["id"]

    # Luna intenta leer a Rodrigo por ID
    r_get = client.get(f"/api/v1/usuarios/{id_rodrigo}", headers=_h(token_luna))
    assert r_get.status_code == 404

    # Luna intenta modificar a Rodrigo
    r_patch = client.patch(
        f"/api/v1/usuarios/{id_rodrigo}",
        json={"nombre": "Hack"},
        headers=_h(token_luna),
    )
    assert r_patch.status_code == 404

    # Luna intenta borrar a Rodrigo
    r_del = client.delete(f"/api/v1/usuarios/{id_rodrigo}", headers=_h(token_luna))
    assert r_del.status_code == 404


def test_seguridad_permisos_usuario_no_admin(client):
    # Sin token
    assert client.get("/api/v1/usuarios").status_code == 401

    # Login como encargado de Luna (no es admin)
    r_login = client.post(
        "/api/v1/auth/login",
        json={"codigo_tenant": "luna", "email": "encargado@boutique-luna.bo", "password": "Luna12345"},
    )
    token_encargado = r_login.json()["access_token"]

    # Encargado NO puede listar usuarios
    assert client.get("/api/v1/usuarios", headers=_h(token_encargado)).status_code == 403

    # Encargado NO puede crear usuarios
    r_crear = client.post(
        "/api/v1/usuarios",
        json={"nombre": "X", "email": "x@boutique-luna.bo", "password": "Password123", "rol": "cajero"},
        headers=_h(token_encargado),
    )
    assert r_crear.status_code == 403
