"""Pruebas de CU-10: Gestionar proveedores.
Verifica:
1. Listar proveedores con aislamiento multitenant estricto (Luna y Andina no comparten proveedores).
2. CRUD completo de proveedores (Crear, Obtener, Actualizar PATCH/PUT, Eliminar).
3. Rechazo de nombre duplicado dentro del mismo tenant (409).
4. El mismo nombre de proveedor puede existir en diferentes empresas contratantes.
5. Acceso cruzado por ID directo devuelve 404.
6. Permisos: admin y encargado pueden gestionar proveedores, sin token da 401.
"""
from __future__ import annotations


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_aislamiento_proveedores(client, token_luna, token_andina):
    # Luna lista sus proveedores
    r_luna = client.get("/api/v1/proveedores", headers=_h(token_luna))
    assert r_luna.status_code == 200
    nombres_luna = [p["nombre"] for p in r_luna.json()]
    assert "Textiles Andinos SRL" in nombres_luna
    assert "Confecciones Oriente" in nombres_luna
    assert "Lanas del Altiplano" not in nombres_luna

    # Andina lista sus proveedores
    r_andina = client.get("/api/v1/proveedores", headers=_h(token_andina))
    assert r_andina.status_code == 200
    nombres_andina = [p["nombre"] for p in r_andina.json()]
    assert "Lanas del Altiplano" in nombres_andina
    assert "Textiles Andinos SRL" not in nombres_andina


def test_crud_proveedor_luna(client, token_luna):
    # 1. Crear proveedor
    body = {
        "nombre": "Hilanderia Santa Cruz SA",
        "nit": "9080706050",
        "contacto": "Juan Perez",
        "telefono": "78912345",
        "email": "ventas@hilanderiasantacruz.bo",
        "direccion": "Av. Doble Via La Guardia Km 6",
    }
    r = client.post("/api/v1/proveedores", json=body, headers=_h(token_luna))
    assert r.status_code == 201
    prov = r.json()
    assert prov["nombre"] == "Hilanderia Santa Cruz SA"
    assert prov["nit"] == "9080706050"
    prov_id = prov["id"]

    # 2. Rechazo duplicado en mismo tenant
    r_dup = client.post("/api/v1/proveedores", json=body, headers=_h(token_luna))
    assert r_dup.status_code == 409
    assert "Ya existe un proveedor con el nombre" in r_dup.json()["detail"]

    # 3. Obtener por ID
    r_get = client.get(f"/api/v1/proveedores/{prov_id}", headers=_h(token_luna))
    assert r_get.status_code == 200
    assert r_get.json()["contacto"] == "Juan Perez"

    # 4. Actualizar con PATCH
    r_patch = client.patch(
        f"/api/v1/proveedores/{prov_id}",
        json={"contacto": "Juan Perez Junior", "telefono": "70000000"},
        headers=_h(token_luna),
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["contacto"] == "Juan Perez Junior"
    assert r_patch.json()["telefono"] == "70000000"

    # 5. Actualizar con PUT (compatibilidad frontend Angular)
    r_put = client.put(
        f"/api/v1/proveedores/{prov_id}",
        json={"direccion": "Nueva Direccion Zona Norte"},
        headers=_h(token_luna),
    )
    assert r_put.status_code == 200
    assert r_put.json()["direccion"] == "Nueva Direccion Zona Norte"

    # 6. Eliminar
    r_del = client.delete(f"/api/v1/proveedores/{prov_id}", headers=_h(token_luna))
    assert r_del.status_code == 204

    # 7. Verificar que ya no existe (404)
    r_get_del = client.get(f"/api/v1/proveedores/{prov_id}", headers=_h(token_luna))
    assert r_get_del.status_code == 404


def test_mismo_nombre_proveedor_en_distintos_tenants(client, token_luna, token_andina):
    body = {"nombre": "Distribuidora Nacional SRL"}

    r1 = client.post("/api/v1/proveedores", json=body, headers=_h(token_luna))
    assert r1.status_code == 201

    r2 = client.post("/api/v1/proveedores", json=body, headers=_h(token_andina))
    assert r2.status_code == 201


def test_acceso_cruzado_proveedor_devuelve_404(client, token_luna, token_andina):
    # ID de proveedor de Andina
    r_andina = client.get("/api/v1/proveedores", headers=_h(token_andina))
    id_andina = r_andina.json()[0]["id"]

    # Luna intenta leer por ID directo
    r_get = client.get(f"/api/v1/proveedores/{id_andina}", headers=_h(token_luna))
    assert r_get.status_code == 404

    # Luna intenta modificar
    r_patch = client.patch(
        f"/api/v1/proveedores/{id_andina}",
        json={"nombre": "Hack Proveedor"},
        headers=_h(token_luna),
    )
    assert r_patch.status_code == 404

    # Luna intenta borrar
    r_del = client.delete(f"/api/v1/proveedores/{id_andina}", headers=_h(token_luna))
    assert r_del.status_code == 404


def test_permisos_proveedores(client):
    # 1. Sin token da 401
    assert client.get("/api/v1/proveedores").status_code == 401

    # 2. Login como encargado de Luna (rol 'encargado')
    r_login = client.post(
        "/api/v1/auth/login",
        json={"codigo_tenant": "luna", "email": "encargado@boutique-luna.bo", "password": "Luna12345"},
    )
    token_encargado = r_login.json()["access_token"]

    # Encargado puede listar
    assert client.get("/api/v1/proveedores", headers=_h(token_encargado)).status_code == 200

    # Encargado puede registrar compras/proveedor
    r_crear = client.post(
        "/api/v1/proveedores",
        json={"nombre": "Proveedor Creado por Encargado"},
        headers=_h(token_encargado),
    )
    assert r_crear.status_code == 201
    prov_id = r_crear.json()["id"]

    # Encargado NO puede eliminar (eliminar requiere rol admin)
    r_del = client.delete(f"/api/v1/proveedores/{prov_id}", headers=_h(token_encargado))
    assert r_del.status_code == 403
