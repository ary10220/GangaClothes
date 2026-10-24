"""Pruebas de aislamiento multitenant.

El escenario de la demo:
- Tenant 'luna' (plan Profesional) con 2 sucursales.
- Tenant 'andina' (plan Basico) con 1 sucursal.

Un usuario de 'luna' no puede ver ni tocar los recursos de 'andina', y
viceversa, aunque los ids del otro existan en la base.
"""
from __future__ import annotations


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_cada_tenant_solo_ve_sus_sucursales(client, token_luna, token_andina):
    r_luna = client.get("/api/v1/sucursales", headers=_h(token_luna))
    assert r_luna.status_code == 200
    sucursales_luna = r_luna.json()
    assert len(sucursales_luna) == 2
    assert all(s["codigo"] in ("suc-01", "suc-02") for s in sucursales_luna)

    r_andina = client.get("/api/v1/sucursales", headers=_h(token_andina))
    assert r_andina.status_code == 200
    sucursales_andina = r_andina.json()
    assert len(sucursales_andina) == 1
    assert sucursales_andina[0]["codigo"] == "suc-01"

    # Garantia: los ids son distintos conjuntos
    ids_luna = {s["id"] for s in sucursales_luna}
    ids_andina = {s["id"] for s in sucursales_andina}
    assert ids_luna.isdisjoint(ids_andina)


def test_acceso_cruzado_por_id_devuelve_404(client, token_luna, token_andina):
    """Luna pide una sucursal de Andina por id directo. Debe dar 404 — el
    filtro central no le deja ni enterarse de que ese id existe."""
    r_andina = client.get("/api/v1/sucursales", headers=_h(token_andina))
    id_andina = r_andina.json()[0]["id"]

    r = client.get(f"/api/v1/sucursales/{id_andina}", headers=_h(token_luna))
    assert r.status_code == 404, r.text


def test_update_cruzado_por_id_devuelve_404(client, token_luna, token_andina):
    r_andina = client.get("/api/v1/sucursales", headers=_h(token_andina))
    id_andina = r_andina.json()[0]["id"]

    r = client.patch(
        f"/api/v1/sucursales/{id_andina}",
        json={"nombre": "intento de hijack"},
        headers=_h(token_luna),
    )
    assert r.status_code == 404


def test_delete_cruzado_por_id_devuelve_404(client, token_luna, token_andina):
    r_andina = client.get("/api/v1/sucursales", headers=_h(token_andina))
    id_andina = r_andina.json()[0]["id"]

    r = client.delete(f"/api/v1/sucursales/{id_andina}", headers=_h(token_luna))
    assert r.status_code == 404


def test_sin_token_no_entra(client):
    r = client.get("/api/v1/sucursales")
    assert r.status_code == 401


def test_mismo_email_puede_vivir_en_dos_tenants(client, token_super):
    """Luna y Andina pueden tener cada una un usuario con el mismo correo.
    El super agrega un segundo tenant con el admin usando un correo que ya
    existia en otro tenant: el UNIQUE es por tenant, no global.
    """
    body = {
        "razon_social": "Nueva Tienda SRL",
        "nit": "9999999999",
        "correo": "contacto@nueva.bo",
        "telefono": "+591 70000099",
        "codigo": "nueva",
        "admin": {
            "nombre": "Ana Nueva",
            "email": "ana@boutique-luna.bo",  # mismo correo que la admin de 'luna'
            "password": "NuevaSegura123",
        },
        "plan_codigo": "basico",
    }
    r = client.post("/api/v1/tenants", json=body, headers=_h(token_super))
    assert r.status_code == 201, r.text
