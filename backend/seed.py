"""Datos iniciales de demostracion.  Uso:  python seed.py"""
from app import models  # noqa: F401
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.catalogo import (Categoria, Coleccion, Color, Prenda, Talla,
                                 Temporada, Variante)
from app.models.inventario import Inventario
from app.models.sucursales import Ciudad, Sucursal
from app.models.seguridad import Permiso, RolPermiso
from app.models.usuarios import Rol, Usuario
from app.modules.auth.service import asignar_rol
from app.core import permisos as cat

Base.metadata.create_all(bind=engine)
db = SessionLocal()


def get_or_create(model, defaults=None, **filtros):
    fila = db.query(model).filter_by(**filtros).first()
    if fila:
        return fila
    fila = model(**filtros, **(defaults or {}))
    db.add(fila)
    db.flush()
    return fila


# --- permisos del sistema (un registro por modulo + accion) ---
for fila in cat.catalogo():
    permiso = get_or_create(Permiso, codigo=fila["codigo"], defaults={
        "modulo": fila["modulo"], "accion": fila["accion"],
        "nombre": fila["nombre"], "descripcion": fila["descripcion"]})
    # Si el catalogo cambia de texto, se actualiza la fila existente.
    permiso.modulo, permiso.accion = fila["modulo"], fila["accion"]
    permiso.nombre, permiso.descripcion = fila["nombre"], fila["descripcion"]

por_codigo = {p.codigo: p for p in db.query(Permiso).all()}

# --- roles con sus permisos ---
for nombre_rol, codigos in cat.PERMISOS_POR_ROL.items():
    rol = get_or_create(Rol, nombre=nombre_rol,
                        defaults={"descripcion": cat.DESCRIPCION_ROLES.get(nombre_rol)})
    if not rol.descripcion:
        rol.descripcion = cat.DESCRIPCION_ROLES.get(nombre_rol)
    # El administrador siempre queda con todo, incluso si se agregan modulos.
    if nombre_rol == "administrador":
        codigos = cat.todos_los_codigos()
    actuales = {rp.permiso_id for rp in db.query(RolPermiso).filter(RolPermiso.rol_id == rol.id).all()}
    for codigo in codigos:
        permiso = por_codigo.get(codigo)
        if permiso and permiso.id not in actuales:
            db.add(RolPermiso(rol_id=rol.id, permiso_id=permiso.id))

db.flush()

# --- usuarios con cada rol ---
usuarios = [
    ("Admin", "GangaClothes", "admin@gangaclothes.com", "Admin123", "administrador"),
    ("Elena", "Encargada", "encargado@gangaclothes.com", "Encargado123", "encargado"),
    ("Carlos", "Cajero", "cajero@gangaclothes.com", "Cajero123", "cajero"),
]
for nombre, apellido, email, pwd, rol in usuarios:
    u = get_or_create(Usuario, email=email,
                      defaults={"nombre": nombre, "apellido": apellido,
                                "password_hash": hash_password(pwd)})
    asignar_rol(db, u.id, rol)

# --- ciudad y sucursal ---
scz = get_or_create(Ciudad, nombre="Santa Cruz de la Sierra", defaults={"departamento": "Santa Cruz"})
central = get_or_create(Sucursal, nombre="Sucursal Central", defaults={
    "ciudad_id": scz.id, "direccion": "Av. Principal #123", "horario": "Lun-Sab 9:00-20:00"})

# --- catalogos base ---
tallas = {n: get_or_create(Talla, nombre=n, defaults={"orden": i}) for i, n in enumerate(["S", "M", "L", "XL"], 1)}
colores = {n: get_or_create(Color, nombre=n, defaults={"codigo_hex": h})
           for n, h in [("Negro", "#000000"), ("Blanco", "#FFFFFF"), ("Rojo", "#D62828"), ("Azul", "#1D3557")]}
cat_poleras = get_or_create(Categoria, nombre="Poleras")
cat_pant = get_or_create(Categoria, nombre="Pantalones")
temporada = get_or_create(Temporada, nombre="Primavera-Verano 2026")
colec = get_or_create(Coleccion, nombre="Coleccion Verano", defaults={"temporada_id": temporada.id, "anio": 2026})

# --- prendas de ejemplo con variantes y stock ---
prendas = [
    ("Polera basica algodon", cat_poleras.id, 79.90, 45.00),
    ("Pantalon jean clasico", cat_pant.id, 189.90, 110.00),
]
for nombre, cat_id, precio, costo in prendas:
    p = get_or_create(Prenda, nombre=nombre, defaults={
        "categoria_id": cat_id, "coleccion_id": colec.id,
        "precio_venta": precio, "costo": costo, "genero": "unisex"})
    for t in list(tallas.values())[:3]:
        for c in list(colores.values())[:2]:
            v = get_or_create(Variante, prenda_id=p.id, talla_id=t.id, color_id=c.id,
                              defaults={"sku": f"P{p.id}-T{t.id}-C{c.id}"})
            get_or_create(Inventario, variante_id=v.id, sucursal_id=central.id,
                          defaults={"cantidad": 10, "stock_minimo": 3, "stock_maximo": 20})

db.commit()
db.close()
print("Seed OK")
print("  admin@gangaclothes.com      / Admin123      (administrador)")
print("  encargado@gangaclothes.com  / Encargado123  (encargado)")
print("  cajero@gangaclothes.com     / Cajero123     (cajero)")
print(f"  {len(cat.todos_los_codigos())} permisos en {len(cat.MODULOS)} modulos")
