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
from ..models import (
    Categoria,
    Cliente,
    Color,
    Plan,
    Producto,
    Proveedor,
    Sucursal,
    SuperAdmin,
    Suscripcion,
    Talla,
    Temporada,
    Tenant,
    User,
    Variante,
)


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
        categorias=[
            dict(nombre="Poleras", descripcion="Poleras y camisetas"),
            dict(nombre="Pantalones", descripcion="Pantalones y jeans"),
            dict(nombre="Vestidos", descripcion="Vestidos de gala y casuales"),
        ],
        tallas=[
            dict(nombre="S", orden=1),
            dict(nombre="M", orden=2),
            dict(nombre="L", orden=3),
            dict(nombre="XL", orden=4),
        ],
        colores=[
            dict(nombre="Negro", codigo_hex="#000000"),
            dict(nombre="Blanco", codigo_hex="#FFFFFF"),
            dict(nombre="Rojo", codigo_hex="#FF0000"),
            dict(nombre="Azul Marino", codigo_hex="#000080"),
        ],
        temporadas=[
            dict(nombre="Verano 2026", fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 3, 31)),
            dict(nombre="Invierno 2026", fecha_inicio=date(2026, 6, 1), fecha_fin=date(2026, 8, 31)),
        ],
        proveedores=[
            dict(nombre="Textiles Andinos SRL", nit="1020304025", contacto="Rosa Mamani", telefono="70012345", email="ventas@textilesandinos.bo", direccion="Av. Bolivia 456"),
            dict(nombre="Confecciones Oriente", nit="3040506071", contacto="Mario Suarez", telefono="71122334", email="contacto@confeccionesoriente.bo", direccion="Parque Industrial Mz 10"),
        ],
        productos=[
            dict(
                nombre="Polera Básica Algodón",
                categoria="Poleras",
                temporada="Verano 2026",
                proveedor="Textiles Andinos SRL",
                descripcion="Polera 100% algodón suave",
                marca="Luna Basic",
                genero="unisex",
                precio_venta=85.0,
                costo=35.0,
                publicado=True,
                variantes=[
                    dict(talla="S", color="Blanco", sku="LUNA-POL-S-BLA"),
                    dict(talla="M", color="Blanco", sku="LUNA-POL-M-BLA"),
                    dict(talla="M", color="Negro", sku="LUNA-POL-M-NEG"),
                ],
            ),
            dict(
                nombre="Vestido Floral Casual",
                categoria="Vestidos",
                temporada="Verano 2026",
                proveedor="Confecciones Oriente",
                descripcion="Vestido fresco con estampado floral",
                marca="Luna Chic",
                genero="mujer",
                precio_venta=220.0,
                costo=95.0,
                publicado=True,
                variantes=[
                    dict(talla="S", color="Rojo", sku="LUNA-VES-S-ROJ"),
                    dict(talla="M", color="Rojo", sku="LUNA-VES-M-ROJ"),
                ],
            ),
        ],
        clientes=[
            dict(
                nombre="Mariana",
                apellido="Ruiz",
                ci_nit="6543210",
                telefono="71012345",
                email="mariana.ruiz@gmail.com",
                direccion="Barrio Sirari Calle 4",
                ciudad="Santa Cruz",
                tipo="regular",
            ),
            dict(
                nombre="Carlos",
                apellido="Justiniano",
                ci_nit="7890123",
                telefono="72098765",
                email="carlos.j@hotmail.com",
                direccion="Av. Busch 3er Anillo",
                ciudad="Santa Cruz",
                tipo="vip",
            ),
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
        categorias=[
            dict(nombre="Abrigos", descripcion="Abrigos y ponchos tradicionales"),
            dict(nombre="Bufandas", descripcion="Bufandas de alpaca"),
        ],
        tallas=[
            dict(nombre="M", orden=1),
            dict(nombre="L", orden=2),
        ],
        colores=[
            dict(nombre="Gris", codigo_hex="#808080"),
            dict(nombre="Cafe", codigo_hex="#8B4513"),
        ],
        temporadas=[
            dict(nombre="Temporada Andina 2026", fecha_inicio=date(2026, 4, 1), fecha_fin=date(2026, 10, 31)),
        ],
        proveedores=[
            dict(nombre="Lanas del Altiplano", nit="5060708092", contacto="Juana Quispe", telefono="72233445", email="ventas@lanasaltiplano.bo", direccion="Calle Sagarnaga 100"),
        ],
        productos=[
            dict(
                nombre="Poncho Clásico de Alpaca",
                categoria="Abrigos",
                temporada="Temporada Andina 2026",
                proveedor="Lanas del Altiplano",
                descripcion="Poncho tejido artesanal con lana de alpaca",
                marca="Andina",
                genero="unisex",
                precio_venta=350.0,
                costo=150.0,
                publicado=True,
                variantes=[
                    dict(talla="M", color="Gris", sku="AND-PON-M-GRI"),
                    dict(talla="L", color="Cafe", sku="AND-PON-L-CAF"),
                ],
            ),
        ],
        clientes=[
            dict(
                nombre="Willy",
                apellido="Choque",
                ci_nit="4567890",
                telefono="73055443",
                email="willy.choque@gmail.com",
                direccion="Calle Illampu 789",
                ciudad="La Paz",
                tipo="mayorista",
            ),
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

    for c in data.get("categorias", []):
        if not db.query(Categoria).filter(Categoria.tenant_id == tenant.id, Categoria.nombre == c["nombre"]).first():
            db.add(Categoria(tenant_id=tenant.id, nombre=c["nombre"], descripcion=c.get("descripcion"), activo=True))

    for t in data.get("tallas", []):
        if not db.query(Talla).filter(Talla.tenant_id == tenant.id, Talla.nombre == t["nombre"]).first():
            db.add(Talla(tenant_id=tenant.id, nombre=t["nombre"], orden=t.get("orden", 0), activo=True))

    for cl in data.get("colores", []):
        if not db.query(Color).filter(Color.tenant_id == tenant.id, Color.nombre == cl["nombre"]).first():
            db.add(Color(tenant_id=tenant.id, nombre=cl["nombre"], codigo_hex=cl.get("codigo_hex"), activo=True))

    for tp in data.get("temporadas", []):
        if not db.query(Temporada).filter(Temporada.tenant_id == tenant.id, Temporada.nombre == tp["nombre"]).first():
            db.add(Temporada(
                tenant_id=tenant.id,
                nombre=tp["nombre"],
                fecha_inicio=tp.get("fecha_inicio"),
                fecha_fin=tp.get("fecha_fin"),
                activo=True,
            ))

    for pr in data.get("proveedores", []):
        if not db.query(Proveedor).filter(Proveedor.tenant_id == tenant.id, Proveedor.nombre == pr["nombre"]).first():
            db.add(Proveedor(
                tenant_id=tenant.id,
                nombre=pr["nombre"],
                nit=pr.get("nit"),
                contacto=pr.get("contacto"),
                telefono=pr.get("telefono"),
                email=pr.get("email"),
                direccion=pr.get("direccion"),
                estado="activo",
                activo=True,
            ))

    db.flush()

    for p in data.get("productos", []):
        cat = db.query(Categoria).filter(Categoria.tenant_id == tenant.id, Categoria.nombre == p["categoria"]).first()
        temp = db.query(Temporada).filter(Temporada.tenant_id == tenant.id, Temporada.nombre == p.get("temporada")).first() if p.get("temporada") else None
        prov = db.query(Proveedor).filter(Proveedor.tenant_id == tenant.id, Proveedor.nombre == p.get("proveedor")).first() if p.get("proveedor") else None
        if not cat:
            continue

        prod = db.query(Producto).filter(Producto.tenant_id == tenant.id, Producto.nombre == p["nombre"]).first()
        if not prod:
            prod = Producto(
                tenant_id=tenant.id,
                categoria_id=cat.id,
                temporada_id=temp.id if temp else None,
                proveedor_id=prov.id if prov else None,
                nombre=p["nombre"],
                descripcion=p.get("descripcion"),
                marca=p.get("marca"),
                genero=p.get("genero"),
                precio_venta=p["precio_venta"],
                costo=p.get("costo", 0.0),
                activo=True,
                publicado=p.get("publicado", True),
            )
            db.add(prod)
            db.flush()

        for var_data in p.get("variantes", []):
            tal = db.query(Talla).filter(Talla.tenant_id == tenant.id, Talla.nombre == var_data["talla"]).first()
            col = db.query(Color).filter(Color.tenant_id == tenant.id, Color.nombre == var_data["color"]).first()
            if not tal or not col:
                continue
            v_exist = db.query(Variante).filter(
                Variante.producto_id == prod.id,
                Variante.talla_id == tal.id,
                Variante.color_id == col.id,
            ).first()
            if not v_exist:
                db.add(Variante(
                    tenant_id=tenant.id,
                    producto_id=prod.id,
                    talla_id=tal.id,
                    color_id=col.id,
                    sku=var_data["sku"],
                    precio_adicional=var_data.get("precio_adicional", 0.0),
                    activo=True,
                ))

    for cl in data.get("clientes", []):
        existe_cli = db.query(Cliente).filter(
            Cliente.tenant_id == tenant.id,
            Cliente.nombre == cl["nombre"],
            Cliente.apellido == cl.get("apellido"),
        ).first()
        if not existe_cli:
            db.add(Cliente(
                tenant_id=tenant.id,
                nombre=cl["nombre"],
                apellido=cl.get("apellido"),
                ci_nit=cl.get("ci_nit"),
                telefono=cl.get("telefono"),
                email=cl.get("email"),
                direccion=cl.get("direccion"),
                ciudad=cl.get("ciudad"),
                tipo=cl.get("tipo", "regular"),
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
        print(f"  - {db.query(Categoria).count()} categorias")
        print(f"  - {db.query(Talla).count()} tallas")
        print(f"  - {db.query(Color).count()} colores")
        print(f"  - {db.query(Temporada).count()} temporadas")
        print(f"  - {db.query(Proveedor).count()} proveedores")
        print(f"  - {db.query(Producto).count()} productos")
        print(f"  - {db.query(Variante).count()} variantes")
        print(f"  - {db.query(Cliente).count()} clientes")
    finally:
        db.close()




if __name__ == "__main__":
    run()
