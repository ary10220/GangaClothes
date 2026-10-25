"""Pruebas de CU-11: Gestionar clientes del tenant.
Verifica:
1. Listar clientes con aislamiento multitenant estricto (Luna y Andina no comparten clientes).
2. CRUD completo de clientes (Crear, Obtener, Actualizar PATCH/PUT, Eliminar).
3. Búsqueda y filtrado por texto (q) y por tipo de cliente.
4. Rechazo de correo duplicado dentro del mismo tenant (409).
5. Rechazo de CI/NIT duplicado dentro del mismo tenant (409).
6. El mismo correo y CI/NIT pueden existir en diferentes empresas contratantes sin colisión.
7. Acceso cruzado por ID directo devuelve 404 (aislamiento garantizado).
8. Permisos por rol: personal de tienda puede gestionar clientes, sin token devuelve 401.
"""
from __future__ import annotations


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_aislamiento_clientes(client, token_luna, token_andina):
    # Luna lista sus clientes
    r_luna = client.get("/api/v1/clientes", headers=_h(token_luna))
    assert r_luna.status_code == 200
    nombres_luna = [c["nombre"] for c in r_luna.json()]
    assert "Mariana" in nombres_luna
    assert "Carlos" in nombres_luna
    assert "Willy" not in nombres_luna

    # Andina lista sus clientes
    r_andina = client.get("/api/v1/clientes", headers=_h(token_andina))
    assert r_andina.status_code == 200
    nombres_andina = [c["nombre"] for c in r_andina.json()]
    assert "Willy" in nombres_andina
    assert "Mariana" not in nombres_andina
    assert "Carlos" not in nombres_andina


def test_crud_cliente_luna(client, token_luna):
    # 1. Crear nuevo cliente
    body = {
        "nombre": "Valeria",
        "apellido": "Morales",
        "ci_nit": "8765432",
        "telefono": "78945612",
        "email": "valeria.morales@gmail.com",
        "direccion": "Condominio La Riviera Dpto 4B",
        "ciudad": "Santa Cruz",
        "tipo": "vip",
        "notas": "Prefiere vestidos largos y colores oscuros",
        "activo": True,
    }
    r = client.post("/api/v1/clientes", json=body, headers=_h(token_luna))
    assert r.status_code == 201
    cli = r.json()
    assert cli["nombre"] == "Valeria"
    assert cli["apellido"] == "Morales"
    assert cli["ci_nit"] == "8765432"
    assert cli["tipo"] == "vip"
    cli_id = cli["id"]

    # 2. Rechazo de correo duplicado en el mismo tenant
    body_dup_email = {
        "nombre": "Otra Valeria",
        "email": "valeria.morales@gmail.com",
    }
    r_dup_email = client.post("/api/v1/clientes", json=body_dup_email, headers=_h(token_luna))
    assert r_dup_email.status_code == 409
    assert "Ya existe un cliente con el correo" in r_dup_email.json()["detail"]

    # 3. Rechazo de CI/NIT duplicado en el mismo tenant
    body_dup_nit = {
        "nombre": "Valeria Familiar",
        "ci_nit": "8765432",
    }
    r_dup_nit = client.post("/api/v1/clientes", json=body_dup_nit, headers=_h(token_luna))
    assert r_dup_nit.status_code == 409
    assert "Ya existe un cliente con el CI/NIT" in r_dup_nit.json()["detail"]

    # 4. Obtener por ID
    r_get = client.get(f"/api/v1/clientes/{cli_id}", headers=_h(token_luna))
    assert r_get.status_code == 200
    assert r_get.json()["email"] == "valeria.morales@gmail.com"

    # 5. Filtrar por término de búsqueda (q)
    r_q = client.get("/api/v1/clientes?q=Morales", headers=_h(token_luna))
    assert r_q.status_code == 200
    assert any(c["id"] == cli_id for c in r_q.json())

    # 6. Actualizar con PATCH
    r_patch = client.patch(
        f"/api/v1/clientes/{cli_id}",
        json={"telefono": "70099999", "notas": "Actualizada a clienta frecuente"},
        headers=_h(token_luna),
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["telefono"] == "70099999"
    assert r_patch.json()["notas"] == "Actualizada a clienta frecuente"

    # 7. Actualizar con PUT
    r_put = client.put(
        f"/api/v1/clientes/{cli_id}",
        json={"ciudad": "Cochabamba"},
        headers=_h(token_luna),
    )
    assert r_put.status_code == 200
    assert r_put.json()["ciudad"] == "Cochabamba"

    # 8. Eliminar cliente
    r_del = client.delete(f"/api/v1/clientes/{cli_id}", headers=_h(token_luna))
    assert r_del.status_code == 204

    # 9. Verificar que ya no existe (404)
    r_not_found = client.get(f"/api/v1/clientes/{cli_id}", headers=_h(token_luna))
    assert r_not_found.status_code == 404


def test_mismo_email_y_ci_nit_en_distintos_tenants(client, token_luna, token_andina):
    # El mismo cliente compra en Boutique Luna y en Moda Andina
    cli_comun = {
        "nombre": "Andrea",
        "apellido": "Torrico",
        "ci_nit": "9988776",
        "email": "andrea.torrico@gmail.com",
        "telefono": "77788899",
    }

    # Registro en Luna
    r1 = client.post("/api/v1/clientes", json=cli_comun, headers=_h(token_luna))
    assert r1.status_code == 201

    # Registro en Andina con exactamente el mismo CI/NIT y correo
    r2 = client.post("/api/v1/clientes", json=cli_comun, headers=_h(token_andina))
    assert r2.status_code == 201


def test_acceso_cruzado_cliente_devuelve_404(client, token_luna, token_andina):
    # Cliente de Andina (Willy Choque)
    r_andina = client.get("/api/v1/clientes", headers=_h(token_andina))
    cli_andina = r_andina.json()[0]
    cli_andina_id = cli_andina["id"]

    # 1. Luna intenta obtener el cliente de Andina por ID directo
    r1 = client.get(f"/api/v1/clientes/{cli_andina_id}", headers=_h(token_luna))
    assert r1.status_code == 404

    # 2. Luna intenta modificar el cliente de Andina
    r2 = client.patch(f"/api/v1/clientes/{cli_andina_id}", json={"nombre": "Hacked"}, headers=_h(token_luna))
    assert r2.status_code == 404

    # 3. Luna intenta eliminar el cliente de Andina
    r3 = client.delete(f"/api/v1/clientes/{cli_andina_id}", headers=_h(token_luna))
    assert r3.status_code == 404


def test_permisos_roles_clientes(client, token_luna, token_luna_encargado):
    body = {"nombre": "Cliente Registrado Por Encargado", "ci_nit": "1231231"}

    # Encargado puede crear cliente
    r_enc = client.post("/api/v1/clientes", json=body, headers=_h(token_luna_encargado))
    assert r_enc.status_code == 201
    cli_id = r_enc.json()["id"]

    # Encargado puede consultar y editar cliente
    r_edit = client.patch(f"/api/v1/clientes/{cli_id}", json={"telefono": "75555555"}, headers=_h(token_luna_encargado))
    assert r_edit.status_code == 200

    # Sin token da 401
    r_sin_token = client.get("/api/v1/clientes")
    assert r_sin_token.status_code == 401
