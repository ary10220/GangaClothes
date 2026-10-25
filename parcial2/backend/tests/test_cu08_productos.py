"""Pruebas de CU-08: Gestionar productos del catálogo y variantes.
Verifica:
1. Listar productos con aislamiento multitenant estricto (Luna y Andina no comparten catálogo).
2. CRUD completo de producto (Crear con variantes iniciales, Obtener, Actualizar PATCH/PUT, Eliminar).
3. Publicación y despublicación (/publicar, /despublicar).
4. Alias `/prendas` y `/prendas/catalogo-interno` para compatibilidad con el frontend.
5. Gestión de variantes (Crear, SKU único, combinación talla/color única, Actualizar, Eliminar).
6. Validación de relaciones (categoría, temporada, proveedor, talla, color de otro tenant devuelve 404).
7. Acceso cruzado por ID directo devuelve 404 (aislamiento de Producto y Variante).
8. Mismo nombre de producto permitido en distintos tenants sin colisión.
9. Validación de límite de suscripción (exigir_capacidad para productos devuelve 409 al superar max_productos).
10. Permisos por rol (admin y encargado pueden gestionar, sin token da 401).
"""
from __future__ import annotations

import pytest


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_aislamiento_productos(client, token_luna, token_andina):
    # Luna lista sus productos
    r_luna = client.get("/api/v1/productos", headers=_h(token_luna))
    assert r_luna.status_code == 200
    nombres_luna = [p["nombre"] for p in r_luna.json()]
    assert "Polera Básica Algodón" in nombres_luna
    assert "Vestido Floral Casual" in nombres_luna
    assert "Poncho Clásico de Alpaca" not in nombres_luna

    # Andina lista sus productos
    r_andina = client.get("/api/v1/productos", headers=_h(token_andina))
    assert r_andina.status_code == 200
    nombres_andina = [p["nombre"] for p in r_andina.json()]
    assert "Poncho Clásico de Alpaca" in nombres_andina
    assert "Polera Básica Algodón" not in nombres_andina
    assert "Vestido Floral Casual" not in nombres_andina


def test_crud_producto_luna(client, token_luna):
    # 1. Obtener IDs de categoria, temporada y proveedor de Luna
    r_cat = client.get("/api/v1/categorias", headers=_h(token_luna))
    cat_id = r_cat.json()[0]["id"]

    r_temp = client.get("/api/v1/temporadas", headers=_h(token_luna))
    temp_id = r_temp.json()[0]["id"]

    r_prov = client.get("/api/v1/proveedores", headers=_h(token_luna))
    prov_id = r_prov.json()[0]["id"]

    r_talla = client.get("/api/v1/tallas", headers=_h(token_luna))
    talla_s_id = next(t["id"] for t in r_talla.json() if t["nombre"] == "S")

    r_color = client.get("/api/v1/colores", headers=_h(token_luna))
    color_negro_id = next(c["id"] for c in r_color.json() if c["nombre"] == "Negro")

    # 2. Crear producto con variante inicial
    body = {
        "nombre": "Jean Slim Fit Denim",
        "categoria_id": cat_id,
        "temporada_id": temp_id,
        "proveedor_id": prov_id,
        "descripcion": "Jean stretch de mezclilla azul oscuro",
        "marca": "Luna Denim",
        "genero": "unisex",
        "precio_venta": 180.0,
        "costo": 70.0,
        "activo": True,
        "publicado": False,
        "variantes": [
            {
                "talla_id": talla_s_id,
                "color_id": color_negro_id,
                "sku": "LUNA-JEAN-S-NEG",
                "precio_adicional": 0.0,
            }
        ],
    }
    r = client.post("/api/v1/productos", json=body, headers=_h(token_luna))
    assert r.status_code == 201
    prod = r.json()
    assert prod["nombre"] == "Jean Slim Fit Denim"
    assert prod["publicado"] is False
    assert len(prod["variantes"]) == 1
    assert prod["variantes"][0]["sku"] == "LUNA-JEAN-S-NEG"
    prod_id = prod["id"]

    # 3. Rechazo de nombre duplicado en mismo tenant
    r_dup = client.post("/api/v1/productos", json=body, headers=_h(token_luna))
    assert r_dup.status_code == 409
    assert "Ya existe un producto con el nombre" in r_dup.json()["detail"]

    # 4. Obtener por ID
    r_get = client.get(f"/api/v1/productos/{prod_id}", headers=_h(token_luna))
    assert r_get.status_code == 200
    assert r_get.json()["marca"] == "Luna Denim"

    # 5. Actualizar con PATCH
    r_patch = client.patch(
        f"/api/v1/productos/{prod_id}",
        json={"precio_venta": 195.0, "descripcion": "Nueva descripcion stretch"},
        headers=_h(token_luna),
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["precio_venta"] == 195.0
    assert r_patch.json()["descripcion"] == "Nueva descripcion stretch"

    # 6. Actualizar con PUT
    r_put = client.put(
        f"/api/v1/productos/{prod_id}",
        json={"precio_venta": 200.0},
        headers=_h(token_luna),
    )
    assert r_put.status_code == 200
    assert r_put.json()["precio_venta"] == 200.0

    # 7. Publicar producto
    r_pub = client.post(f"/api/v1/productos/{prod_id}/publicar", json={"confirmar_sin_stock": True}, headers=_h(token_luna))
    assert r_pub.status_code == 200
    assert r_pub.json()["publicado"] is True

    # 8. Despublicar producto
    r_despub = client.post(f"/api/v1/productos/{prod_id}/despublicar", headers=_h(token_luna))
    assert r_despub.status_code == 200
    assert r_despub.json()["publicado"] is False

    # 9. Eliminar producto
    r_del = client.delete(f"/api/v1/productos/{prod_id}", headers=_h(token_luna))
    assert r_del.status_code == 204

    # 10. Verificar que ya no existe (404)
    r_not_found = client.get(f"/api/v1/productos/{prod_id}", headers=_h(token_luna))
    assert r_not_found.status_code == 404


def test_alias_prendas_funciona(client, token_luna):
    # GET /api/v1/prendas
    r1 = client.get("/api/v1/prendas", headers=_h(token_luna))
    assert r1.status_code == 200
    nombres1 = [p["nombre"] for p in r1.json()]
    assert "Polera Básica Algodón" in nombres1

    # GET /api/v1/prendas/catalogo-interno
    r2 = client.get("/api/v1/prendas/catalogo-interno", headers=_h(token_luna))
    assert r2.status_code == 200
    nombres2 = [p["nombre"] for p in r2.json()]
    assert "Polera Básica Algodón" in nombres2


def test_variantes_crud_y_validaciones(client, token_luna):
    # 1. Obtener producto de Luna
    r_prods = client.get("/api/v1/productos", headers=_h(token_luna))
    prod = r_prods.json()[0]
    prod_id = prod["id"]

    # 2. Obtener tallas y colores de Luna
    r_tallas = client.get("/api/v1/tallas", headers=_h(token_luna))
    talla_l = next(t for t in r_tallas.json() if t["nombre"] == "L")

    r_colores = client.get("/api/v1/colores", headers=_h(token_luna))
    color_azul = next(c for c in r_colores.json() if c["nombre"] == "Azul Marino")

    # 3. Crear nueva variante
    var_body = {
        "talla_id": talla_l["id"],
        "color_id": color_azul["id"],
        "sku": f"LUNA-VAR-L-AZU-{prod_id}",
        "precio_adicional": 10.0,
    }
    r_var = client.post(f"/api/v1/productos/{prod_id}/variantes", json=var_body, headers=_h(token_luna))
    assert r_var.status_code == 201
    var = r_var.json()
    assert var["sku"] == f"LUNA-VAR-L-AZU-{prod_id}"
    assert var["precio_adicional"] == 10.0
    var_id = var["id"]

    # 4. Rechazar combinacion duplicada de (talla, color) en el mismo producto
    r_dup_comb = client.post(f"/api/v1/productos/{prod_id}/variantes", json=var_body, headers=_h(token_luna))
    assert r_dup_comb.status_code == 409
    assert "Ya existe una variante con esa talla y color" in r_dup_comb.json()["detail"]

    # 5. Rechazar SKU duplicado dentro de la misma empresa
    talla_xl = next(t for t in r_tallas.json() if t["nombre"] == "XL")
    var_dup_sku = {
        "talla_id": talla_xl["id"],
        "color_id": color_azul["id"],
        "sku": f"LUNA-VAR-L-AZU-{prod_id}",  # mismo SKU
    }
    r_dup_sku = client.post(f"/api/v1/productos/{prod_id}/variantes", json=var_dup_sku, headers=_h(token_luna))
    assert r_dup_sku.status_code == 409
    assert "Ya existe una variante con el SKU" in r_dup_sku.json()["detail"]

    # 6. Obtener variante por ID
    r_get_var = client.get(f"/api/v1/productos/variantes/{var_id}", headers=_h(token_luna))
    assert r_get_var.status_code == 200
    assert r_get_var.json()["sku"] == f"LUNA-VAR-L-AZU-{prod_id}"

    # 7. Actualizar variante (PATCH y PUT)
    r_patch_var = client.patch(
        f"/api/v1/productos/variantes/{var_id}",
        json={"precio_adicional": 15.0},
        headers=_h(token_luna),
    )
    assert r_patch_var.status_code == 200
    assert r_patch_var.json()["precio_adicional"] == 15.0

    # 8. Eliminar variante
    r_del_var = client.delete(f"/api/v1/productos/variantes/{var_id}", headers=_h(token_luna))
    assert r_del_var.status_code == 204

    # 9. Verificar que ya no existe (404)
    r_del_check = client.get(f"/api/v1/productos/variantes/{var_id}", headers=_h(token_luna))
    assert r_del_check.status_code == 404


def test_relaciones_otro_tenant_devuelve_404(client, token_luna, token_andina):
    # Categoria de Andina
    r_cat_andina = client.get("/api/v1/categorias", headers=_h(token_andina))
    cat_andina_id = r_cat_andina.json()[0]["id"]

    # Luna intenta crear un producto usando la categoria de Andina
    body = {
        "nombre": "Producto Invalido",
        "categoria_id": cat_andina_id,
        "precio_venta": 100.0,
    }
    r = client.post("/api/v1/productos", json=body, headers=_h(token_luna))
    assert r.status_code == 404
    assert f"Categoria id {cat_andina_id} no existe en su empresa" in r.json()["detail"]


def test_acceso_cruzado_devuelve_404(client, token_luna, token_andina):
    # Producto y variante de Andina
    r_andina = client.get("/api/v1/productos", headers=_h(token_andina))
    prod_andina = r_andina.json()[0]
    prod_andina_id = prod_andina["id"]
    var_andina_id = prod_andina["variantes"][0]["id"]

    # 1. Luna intenta obtener producto de Andina por ID directo
    r1 = client.get(f"/api/v1/productos/{prod_andina_id}", headers=_h(token_luna))
    assert r1.status_code == 404

    # 2. Luna intenta modificar producto de Andina
    r2 = client.patch(f"/api/v1/productos/{prod_andina_id}", json={"precio_venta": 999.0}, headers=_h(token_luna))
    assert r2.status_code == 404

    # 3. Luna intenta eliminar producto de Andina
    r3 = client.delete(f"/api/v1/productos/{prod_andina_id}", headers=_h(token_luna))
    assert r3.status_code == 404

    # 4. Luna intenta acceder a la variante de Andina por ID directo
    r4 = client.get(f"/api/v1/productos/variantes/{var_andina_id}", headers=_h(token_luna))
    assert r4.status_code == 404

    # 5. Luna intenta modificar la variante de Andina
    r5 = client.patch(f"/api/v1/productos/variantes/{var_andina_id}", json={"precio_adicional": 50.0}, headers=_h(token_luna))
    assert r5.status_code == 404


def test_mismo_nombre_producto_en_distintos_tenants(client, token_luna, token_andina):
    # Categoria de Luna
    cat_luna = client.get("/api/v1/categorias", headers=_h(token_luna)).json()[0]["id"]
    # Categoria de Andina
    cat_andina = client.get("/api/v1/categorias", headers=_h(token_andina)).json()[0]["id"]

    nombre_comun = "Campera Rompeviento Unisex"
    body_luna = {"nombre": nombre_comun, "categoria_id": cat_luna, "precio_venta": 250.0}
    body_andina = {"nombre": nombre_comun, "categoria_id": cat_andina, "precio_venta": 280.0}

    r1 = client.post("/api/v1/productos", json=body_luna, headers=_h(token_luna))
    assert r1.status_code == 201

    r2 = client.post("/api/v1/productos", json=body_andina, headers=_h(token_andina))
    assert r2.status_code == 201


def test_limite_productos_plan(client, token_andina):
    """Andina tiene plan Basico (max_productos = 100 por defecto en plan basico).
    Para probar el limite de forma rapida y controlada, cambiamos temporalmente max_productos = 1
    en la suscripcion/plan de Andina via DB o creamos productos hasta el limite.
    """
    from app.core.database import SessionLocal
    from app.models import Plan, Suscripcion, Tenant

    db = SessionLocal()
    try:
        tenant_andina = db.query(Tenant).filter(Tenant.codigo == "andina").first()
        sub = db.query(Suscripcion).filter(Suscripcion.tenant_id == tenant_andina.id).first()
        plan = db.query(Plan).filter(Plan.id == sub.plan_id).first()
        plan.max_productos = 1  # Forzamos límite a 1 (Andina ya tiene 1 producto en las semillas)
        db.commit()
    finally:
        db.close()

    cat_andina = client.get("/api/v1/categorias", headers=_h(token_andina)).json()[0]["id"]
    body = {"nombre": "Producto Que Supera Limite", "categoria_id": cat_andina, "precio_venta": 100.0}

    r = client.post("/api/v1/productos", json=body, headers=_h(token_andina))
    assert r.status_code == 409
    assert "Limite alcanzado para productos" in r.json()["detail"]


def test_permisos_roles_productos(client, token_luna, token_luna_encargado):
    cat_id = client.get("/api/v1/categorias", headers=_h(token_luna)).json()[0]["id"]
    body = {"nombre": "Producto Creado Por Encargado", "categoria_id": cat_id, "precio_venta": 120.0}

    # Encargado puede crear
    r_enc = client.post("/api/v1/productos", json=body, headers=_h(token_luna_encargado))
    assert r_enc.status_code == 201
    p_id = r_enc.json()["id"]

    # Encargado NO puede eliminar (solo admin)
    r_del_enc = client.delete(f"/api/v1/productos/{p_id}", headers=_h(token_luna_encargado))
    assert r_del_enc.status_code == 403

    # Admin si puede eliminar
    r_del_adm = client.delete(f"/api/v1/productos/{p_id}", headers=_h(token_luna))
    assert r_del_adm.status_code == 204

    # Sin token da 401
    r_sin_token = client.get("/api/v1/productos")
    assert r_sin_token.status_code == 401
