"""CU-05 + CU-07: suscripcion con limites que se aplican de verdad.

- Andina esta en plan Basico (max_sucursales=1) y ya tiene 1 sucursal.
- Intentar crear la 2a debe dar 409 con mensaje claro que nombre el plan.
- Luna esta en Profesional (max_sucursales=3) y ya tiene 2.
  La 3a entra; la 4a rebota.
- GET /suscripciones/estado reporta el consumo real contra el limite.
"""
from __future__ import annotations


def _h(t): return {"Authorization": f"Bearer {t}"}


def test_estado_suscripcion_muestra_consumo(client, token_luna):
    r = client.get("/api/v1/suscripciones/estado", headers=_h(token_luna))
    assert r.status_code == 200
    data = r.json()
    assert data["tiene_suscripcion"] is True
    assert data["plan"]["codigo"] == "profesional"
    assert data["estado"] == "activa"
    recursos = {c["recurso"]: c for c in data["consumos"]}
    assert recursos["sucursales"]["actual"] == 2
    assert recursos["sucursales"]["limite"] == 3
    assert recursos["sucursales"]["disponible"] == 1


def test_andina_rechaza_segunda_sucursal_por_limite(client, token_andina):
    body = {
        "codigo": "suc-02",
        "nombre": "Andina Cochabamba",
        "ciudad": "Cochabamba",
        "direccion": "Av. Heroinas 123",
    }
    r = client.post("/api/v1/sucursales", json=body, headers=_h(token_andina))
    assert r.status_code == 409, r.text
    detail = r.json()["detail"]
    assert "Limite alcanzado" in detail
    assert "sucursales" in detail
    assert "Basico" in detail
    # El mensaje debe nombrar el consumo actual y el limite
    assert "1 de 1" in detail


def test_luna_llena_el_plan_y_rechaza(client, token_luna):
    # Luna tiene 2 sucursales, plan permite 3 -> entra la 3a
    r_ok = client.post(
        "/api/v1/sucursales",
        json={"codigo": "suc-03", "nombre": "Luna 3", "ciudad": "Santa Cruz", "direccion": "x"},
        headers=_h(token_luna),
    )
    assert r_ok.status_code == 201, r_ok.text

    # La 4a rebota
    r_fail = client.post(
        "/api/v1/sucursales",
        json={"codigo": "suc-04", "nombre": "Luna 4", "ciudad": "Santa Cruz", "direccion": "y"},
        headers=_h(token_luna),
    )
    assert r_fail.status_code == 409
    assert "Profesional" in r_fail.json()["detail"]


def test_al_contratar_plan_superior_el_limite_sube(client, token_andina):
    # Andina contrata empresarial -> ahora puede crear mas sucursales
    r = client.post(
        "/api/v1/suscripciones/contratar",
        json={"plan_codigo": "empresarial"},
        headers=_h(token_andina),
    )
    assert r.status_code == 200, r.text
    assert r.json()["plan"]["codigo"] == "empresarial"

    r2 = client.post(
        "/api/v1/sucursales",
        json={"codigo": "suc-02", "nombre": "Andina Santa Cruz", "ciudad": "Santa Cruz", "direccion": "Av. Pirai"},
        headers=_h(token_andina),
    )
    assert r2.status_code == 201, r2.text

    estado = client.get("/api/v1/suscripciones/estado", headers=_h(token_andina)).json()
    assert estado["plan"]["codigo"] == "empresarial"
    sucursales_consumo = next(c for c in estado["consumos"] if c["recurso"] == "sucursales")
    assert sucursales_consumo["actual"] == 2
    assert sucursales_consumo["limite"] == 10


def test_super_lista_todas_las_empresas(client, token_super):
    r = client.get("/api/v1/tenants", headers=_h(token_super))
    assert r.status_code == 200
    tenants = r.json()
    codigos = {t["codigo"] for t in tenants}
    assert "luna" in codigos
    assert "andina" in codigos
    luna = next(t for t in tenants if t["codigo"] == "luna")
    assert luna["plan_actual"] == "Profesional"


def test_super_registra_tenant_completo(client, token_super):
    body = {
        "razon_social": "Textil del Sur SA",
        "nit": "7777777777",
        "correo": "info@textilsur.bo",
        "telefono": "+591 72222222",
        "codigo": "sur",
        "admin": {"nombre": "Sofia Rios", "email": "sofia@textilsur.bo", "password": "SurSegura123"},
        "plan_codigo": "basico",
    }
    r = client.post("/api/v1/tenants", json=body, headers=_h(token_super))
    assert r.status_code == 201, r.text

    # El nuevo admin ya puede loguearse
    r_login = client.post(
        "/api/v1/auth/login",
        json={"codigo_tenant": "sur", "email": "sofia@textilsur.bo", "password": "SurSegura123"},
    )
    assert r_login.status_code == 200
    token = r_login.json()["access_token"]

    # Y ver su estado con su plan Basico recien contratado
    estado = client.get("/api/v1/suscripciones/estado", headers=_h(token)).json()
    assert estado["tiene_suscripcion"] is True
    assert estado["plan"]["codigo"] == "basico"


def test_un_tenant_no_puede_usar_endpoint_de_super(client, token_luna):
    r = client.get("/api/v1/tenants", headers=_h(token_luna))
    assert r.status_code == 403


def test_super_no_puede_crear_sucursal_porque_no_tiene_tenant(client, token_super):
    r = client.post(
        "/api/v1/sucursales",
        json={"codigo": "suc-x", "nombre": "x", "ciudad": "x", "direccion": "x"},
        headers=_h(token_super),
    )
    assert r.status_code == 403
