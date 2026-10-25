"""Pruebas de CU-09: Gestionar categorias, tallas, colores y temporadas.
Verifica:
1. CRUD completo de cada catalogo.
2. Aislamiento multitenant estricto: Luna y Andina no comparten catalogos.
3. El mismo nombre puede existir en diferentes tenants (UNIQUE por tenant).
4. Duplicados dentro del mismo tenant son rechazados con 409.
5. Intento de acceder, modificar o borrar por id cruzado devuelve 404.
6. Permisos: lectura para cualquier usuario del tenant, escritura solo admin.
"""
from __future__ import annotations


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# Pruebas de Categorias
# ==============================================================================
def test_aislamiento_categorias(client, token_luna, token_andina):
    r_luna = client.get("/api/v1/categorias", headers=_h(token_luna))
    assert r_luna.status_code == 200
    nombres_luna = [c["nombre"] for c in r_luna.json()]
    assert "Poleras" in nombres_luna
    assert "Vestidos" in nombres_luna
    assert "Abrigos" not in nombres_luna

    r_andina = client.get("/api/v1/categorias", headers=_h(token_andina))
    assert r_andina.status_code == 200
    nombres_andina = [c["nombre"] for c in r_andina.json()]
    assert "Abrigos" in nombres_andina
    assert "Poleras" not in nombres_andina


def test_crud_categoria_luna(client, token_luna):
    # 1. Crear
    body = {"nombre": "Calzados", "descripcion": "Zapatos y zapatillas"}
    r = client.post("/api/v1/categorias", json=body, headers=_h(token_luna))
    assert r.status_code == 201
    cat = r.json()
    assert cat["nombre"] == "Calzados"
    cat_id = cat["id"]

    # 2. Rechazo duplicado en mismo tenant
    r_dup = client.post("/api/v1/categorias", json=body, headers=_h(token_luna))
    assert r_dup.status_code == 409

    # 3. Obtener por ID
    r_get = client.get(f"/api/v1/categorias/{cat_id}", headers=_h(token_luna))
    assert r_get.status_code == 200
    assert r_get.json()["descripcion"] == "Zapatos y zapatillas"

    # 4. Actualizar
    r_patch = client.patch(
        f"/api/v1/categorias/{cat_id}",
        json={"descripcion": "Calzados formales y urbanos"},
        headers=_h(token_luna),
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["descripcion"] == "Calzados formales y urbanos"

    # 5. Eliminar
    r_del = client.delete(f"/api/v1/categorias/{cat_id}", headers=_h(token_luna))
    assert r_del.status_code == 204

    # 6. Ya no existe
    r_get_del = client.get(f"/api/v1/categorias/{cat_id}", headers=_h(token_luna))
    assert r_get_del.status_code == 404


def test_acceso_cruzado_categoria_devuelve_404(client, token_luna, token_andina):
    # Obtener ID de categoria en Andina
    r_andina = client.get("/api/v1/categorias", headers=_h(token_andina))
    id_andina = r_andina.json()[0]["id"]

    # Luna intenta leer por ID directo
    r = client.get(f"/api/v1/categorias/{id_andina}", headers=_h(token_luna))
    assert r.status_code == 404

    # Luna intenta actualizar por ID directo
    r_patch = client.patch(
        f"/api/v1/categorias/{id_andina}",
        json={"nombre": "Hack"},
        headers=_h(token_luna),
    )
    assert r_patch.status_code == 404

    # Luna intenta borrar por ID directo
    r_del = client.delete(f"/api/v1/categorias/{id_andina}", headers=_h(token_luna))
    assert r_del.status_code == 404


def test_mismo_nombre_categoria_en_distintos_tenants(client, token_luna, token_andina):
    # Ambos pueden tener "Accesorios"
    body = {"nombre": "Accesorios"}
    r1 = client.post("/api/v1/categorias", json=body, headers=_h(token_luna))
    assert r1.status_code == 201

    r2 = client.post("/api/v1/categorias", json=body, headers=_h(token_andina))
    assert r2.status_code == 201


# ==============================================================================
# Pruebas de Tallas
# ==============================================================================
def test_crud_tallas(client, token_luna, token_andina):
    # Listar iniciales
    r = client.get("/api/v1/tallas", headers=_h(token_luna))
    assert r.status_code == 200
    assert any(t["nombre"] == "M" for t in r.json())

    # Crear talla nueva
    body = {"nombre": "XXL", "orden": 5}
    r_crear = client.post("/api/v1/tallas", json=body, headers=_h(token_luna))
    assert r_crear.status_code == 201
    talla_id = r_crear.json()["id"]

    # Andina no la ve
    r_andina = client.get(f"/api/v1/tallas/{talla_id}", headers=_h(token_andina))
    assert r_andina.status_code == 404

    # Actualizar orden
    r_up = client.patch(f"/api/v1/tallas/{talla_id}", json={"orden": 10}, headers=_h(token_luna))
    assert r_up.status_code == 200
    assert r_up.json()["orden"] == 10

    # Eliminar
    r_del = client.delete(f"/api/v1/tallas/{talla_id}", headers=_h(token_luna))
    assert r_del.status_code == 204


# ==============================================================================
# Pruebas de Colores
# ==============================================================================
def test_crud_colores(client, token_luna, token_andina):
    # Crear color
    body = {"nombre": "Verde Esmeralda", "codigo_hex": "#00FF00"}
    r = client.post("/api/v1/colores", json=body, headers=_h(token_luna))
    assert r.status_code == 201
    color_id = r.json()["id"]

    # Duplicado
    r_dup = client.post("/api/v1/colores", json=body, headers=_h(token_luna))
    assert r_dup.status_code == 409

    # Andina intenta leer
    r_cross = client.get(f"/api/v1/colores/{color_id}", headers=_h(token_andina))
    assert r_cross.status_code == 404

    # Actualizar hex
    r_up = client.patch(f"/api/v1/colores/{color_id}", json={"codigo_hex": "#50C878"}, headers=_h(token_luna))
    assert r_up.status_code == 200
    assert r_up.json()["codigo_hex"] == "#50C878"

    # Eliminar
    r_del = client.delete(f"/api/v1/colores/{color_id}", headers=_h(token_luna))
    assert r_del.status_code == 204


# ==============================================================================
# Pruebas de Temporadas
# ==============================================================================
def test_crud_temporadas(client, token_luna, token_andina):
    body = {
        "nombre": "Otoño 2026",
        "fecha_inicio": "2026-03-21",
        "fecha_fin": "2026-06-20",
    }
    r = client.post("/api/v1/temporadas", json=body, headers=_h(token_luna))
    assert r.status_code == 201
    temp_id = r.json()["id"]

    # Cross tenant 404
    r_cross = client.get(f"/api/v1/temporadas/{temp_id}", headers=_h(token_andina))
    assert r_cross.status_code == 404

    # Actualizar
    r_up = client.patch(
        f"/api/v1/temporadas/{temp_id}",
        json={"nombre": "Otoño - Invierno 2026"},
        headers=_h(token_luna),
    )
    assert r_up.status_code == 200
    assert r_up.json()["nombre"] == "Otoño - Invierno 2026"

    # Eliminar
    r_del = client.delete(f"/api/v1/temporadas/{temp_id}", headers=_h(token_luna))
    assert r_del.status_code == 204


# ==============================================================================
# Pruebas de Seguridad y Roles
# ==============================================================================
def test_seguridad_sin_token_rechaza(client):
    assert client.get("/api/v1/categorias").status_code == 401
    assert client.get("/api/v1/tallas").status_code == 401
    assert client.get("/api/v1/colores").status_code == 401
    assert client.get("/api/v1/temporadas").status_code == 401


def test_rol_no_admin_no_puede_crear_categoria(client):
    # Login como encargado de Luna (rol 'encargado', no 'admin')
    r_login = client.post(
        "/api/v1/auth/login",
        json={"codigo_tenant": "luna", "email": "encargado@boutique-luna.bo", "password": "Luna12345"},
    )
    assert r_login.status_code == 200
    token_encargado = r_login.json()["access_token"]

    # Encargado puede leer
    assert client.get("/api/v1/categorias", headers=_h(token_encargado)).status_code == 200

    # Encargado NO puede crear (requiere rol admin)
    r_post = client.post(
        "/api/v1/categorias",
        json={"nombre": "Intento Encargado"},
        headers=_h(token_encargado),
    )
    assert r_post.status_code == 403
