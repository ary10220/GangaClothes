"""Datos iniciales de demostracion.  Uso:  python seed.py"""
from app import models  # noqa: F401
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.seguridad import Permiso, RolPermiso
from app.models.usuarios import Rol, Usuario
from app.modules.auth.service import asignar_rol
from app.core import migraciones, permisos as cat
import seed_demo

Base.metadata.create_all(bind=engine)
migraciones.aplicar(engine)
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

db.flush()

# --- tienda de demostracion: sucursales, prendas con foto, stock repartido,
#     promociones, proveedores con su oferta e historial de ventas y reservas ---
resumen = seed_demo.cargar(db, get_or_create)

db.commit()
db.close()
print("Seed OK")
print("  admin@gangaclothes.com      / Admin123      (administrador)")
print("  encargado@gangaclothes.com  / Encargado123  (encargado)")
print("  cajero@gangaclothes.com     / Cajero123     (cajero)")
print("  sofia@gangaclothes.com      / Cliente#2026  (cliente)")
print("  proveedor@gangaclothes.com  / Proveedor123  (proveedor: Textiles Andinos SRL)")
print("  oriente@gangaclothes.com    / Proveedor123  (proveedor: Confecciones Oriente)")
print(f"  {len(cat.todos_los_codigos())} permisos en {len(cat.MODULOS)} modulos")
print(f"  {resumen['prendas']} prendas, {resumen['stock_nuevo']} registros de stock nuevos, "
      f"{resumen['ventas']} ventas y {resumen['reservas']} reservas de historial")
