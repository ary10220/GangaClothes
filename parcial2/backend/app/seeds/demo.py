"""Semillas de demostracion.
Ejecucion:  python -m app.seeds.demo
Resultado:  3 planes, 1 superadmin, 2 empresas contratantes con sus admins,
            sucursales y suscripciones. Suficiente para probar aislamiento
            y limites.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from ..core.database import SessionLocal, init_db
from ..core.security import hash_password
from ..models import Plan, Sucursal, SuperAdmin, Suscripcion, Tenant, User


PLANES = [
    dict(
        codigo="basico",
        nombre="Basico",
        descripcion="Plan de arranque: 1 sucursal, 3 usuarios, 100 productos.",
        max_sucursales=1,
        max_usuarios=3,
        max_productos=100,
        modulos=["ventas", "inventario"],
        precio_mensual=19.0,
    ),
    dict(
        codigo="profesional",
        nombre="Profesional",
        descripcion="Hasta 3 sucursales, 10 usuarios, 1000 productos.",
        max_sucursales=3,
        max_usuarios=10,
        max_productos=1000,
        modulos=["ventas", "inventario", "reportes", "promociones"],
        precio_mensual=49.0,
    ),
    dict(
        codigo="empresarial",
        nombre="Empresarial",
        descripcion="Hasta 10 sucursales, 50 usuarios, productos ilimitados en la practica.",
        max_sucursales=10,
        max_usuarios=50,
        max_productos=100000,
        modulos=["ventas", "inventario", "reportes", "promociones", "ia", "sincronizacion_offline"],
        precio_mensual=129.0,
    ),
]


SUPERADMIN = dict(
    email="root@plataforma.bo",
    password="SuperSegura123",
    nombre="Root Plataforma",
)


EMPRESAS = [
    dict(
        tenant=dict(
            razon_social="Boutique Luna SRL",
            nit="1023456789",
            correo="contacto@boutique-luna.bo",
            telefono="+591 70000001",
            codigo="luna",
        ),
        plan="profesional",
        admin=dict(nombre="Ana Luna", email="ana@boutique-luna.bo", password="Luna12345"),
        extra_users=[
            dict(nombre="Encargado Luna", email="encargado@boutique-luna.bo", password="Luna12345", rol="encargado"),
        ],
        sucursales=[
            dict(codigo="suc-01", nombre="Luna Centro", ciudad="Santa Cruz", direccion="Av. Monseñor Rivero 123", horario="10:00-20:00"),
            dict(codigo="suc-02", nombre="Luna Equipetrol", ciudad="Santa Cruz", direccion="Av. San Martin 500", horario="10:00-22:00"),
        ],
    ),
    dict(
        tenant=dict(
            razon_social="Moda Andina SA",
            nit="2098765432",
            correo="hola@modaandina.bo",
            telefono="+591 71111111",
            codigo="andina",
        ),
        plan="basico",
        admin=dict(nombre="Rodrigo Mamani", email="rodrigo@modaandina.bo", password="Andina12345"),
        extra_users=[],
        sucursales=[
            dict(codigo="suc-01", nombre="Andina La Paz", ciudad="La Paz", direccion="Calle Sagarnaga 456", horario="09:00-19:00"),
        ],
    ),
]


def _ensure_planes(db: Session) -> dict[str, Plan]:
    out: dict[str, Plan] = {}
    for p in PLANES:
        existing = db.query(Plan).filter(Plan.codigo == p["codigo"]).first()
        if existing:
            out[p["codigo"]] = existing
            continue
        plan = Plan(**p)
        db.add(plan)
        db.flush()
        out[p["codigo"]] = plan
    return out


def _ensure_super(db: Session) -> SuperAdmin:
    sa = db.query(SuperAdmin).filter(SuperAdmin.email == SUPERADMIN["email"]).first()
    if sa:
        return sa
    sa = SuperAdmin(
        email=SUPERADMIN["email"],
        password_hash=hash_password(SUPERADMIN["password"]),
        nombre=SUPERADMIN["nombre"],
        activo=True,
    )
    db.add(sa)
    db.flush()
    return sa


def _ensure_empresa(db: Session, data: dict, planes: dict[str, Plan]) -> Tenant:
    t_data = data["tenant"]
    tenant = db.query(Tenant).filter(Tenant.codigo == t_data["codigo"]).first()
    if not tenant:
        tenant = Tenant(**t_data, estado="activo", activo=True)
        db.add(tenant)
        db.flush()

    if not db.query(User).filter(User.tenant_id == tenant.id, User.email == data["admin"]["email"]).first():
        db.add(User(
            tenant_id=tenant.id,
            email=data["admin"]["email"],
            password_hash=hash_password(data["admin"]["password"]),
            nombre=data["admin"]["nombre"],
            rol="admin",
            estado="activo",
            activo=True,
        ))

    for extra in data.get("extra_users", []):
        if not db.query(User).filter(User.tenant_id == tenant.id, User.email == extra["email"]).first():
            db.add(User(
                tenant_id=tenant.id,
                email=extra["email"],
                password_hash=hash_password(extra["password"]),
                nombre=extra["nombre"],
                rol=extra.get("rol", "encargado"),
                estado="activo",
                activo=True,
            ))

    if not db.query(Suscripcion).filter(Suscripcion.tenant_id == tenant.id, Suscripcion.estado == "activa").first():
        plan = planes[data["plan"]]
        hoy = date.today()
        db.add(Suscripcion(
            tenant_id=tenant.id,
            plan_id=plan.id,
            fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=30),
            estado="activa",
        ))

    for s in data["sucursales"]:
        exists = (
            db.query(Sucursal)
            .filter(Sucursal.tenant_id == tenant.id, Sucursal.codigo == s["codigo"])
            .first()
        )
        if not exists:
            db.add(Sucursal(
                tenant_id=tenant.id,
                codigo=s["codigo"],
                nombre=s["nombre"],
                ciudad=s["ciudad"],
                direccion=s["direccion"],
                horario=s.get("horario"),
                estado="activa",
                activo=True,
            ))

    return tenant


def run() -> None:
    init_db()
    db = SessionLocal()
    try:
        planes = _ensure_planes(db)
        _ensure_super(db)
        for empresa in EMPRESAS:
            _ensure_empresa(db, empresa, planes)
        db.commit()
        print("Semillas aplicadas:")
        print(f"  - {db.query(Plan).count()} planes")
        print(f"  - {db.query(SuperAdmin).count()} superadmin")
        print(f"  - {db.query(Tenant).count()} empresas")
        print(f"  - {db.query(User).count()} usuarios de tenant")
        print(f"  - {db.query(Sucursal).count()} sucursales")
        print(f"  - {db.query(Suscripcion).count()} suscripciones")
    finally:
        db.close()


if __name__ == "__main__":
    run()
