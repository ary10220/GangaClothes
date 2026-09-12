"""Catalogo de permisos del sistema, derivado de los modulos reales del proyecto.

Cada modulo declara que acciones tienen sentido sobre el. De aqui sale el
contenido de la tabla `permiso` (lo siembra seed.py) y la pantalla de roles.
"""

# accion -> verbo que se muestra en la interfaz
ACCIONES = {
    "VER": "Ver",
    "CREAR": "Crear",
    "EDITAR": "Editar",
    "ELIMINAR": "Eliminar",
}

# modulo -> (etiqueta, descripcion, acciones permitidas)
MODULOS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "USUARIOS": (
        "Usuarios",
        "Cuentas de personas que entran al sistema",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "ROLES": (
        "Roles y permisos",
        "Definir que puede hacer cada rol",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "BITACORA": (
        "Bitacora",
        "Consultar el registro de acciones del sistema",
        ("VER",),
    ),
    "CATALOGOS": (
        "Catalogos base",
        "Categorias, tallas, colores, temporadas y colecciones",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "SUCURSALES": (
        "Red de tiendas",
        "Ciudades y sucursales",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "PRENDAS": (
        "Prendas y variantes",
        "Prendas, variantes talla-color y recursos del probador",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "INVENTARIO": (
        "Inventario",
        "Stock por sucursal, movimientos y compras a proveedores",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "RESERVAS": (
        "Reservas",
        "Reservas de prendas para probar en tienda",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "VENTAS": (
        "Ventas",
        "Ventas en caja y por la tienda en linea",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "PAGOS": (
        "Pagos",
        "Cobros en efectivo, tarjeta y pasarela",
        ("VER", "CREAR", "EDITAR"),
    ),
    "PROMOCIONES": (
        "Promociones",
        "Descuentos por prenda y por temporada",
        ("VER", "CREAR", "EDITAR", "ELIMINAR"),
    ),
    "REPORTES": (
        "Reportes",
        "Ventas, ganancia promedio y prendas mas vendidas",
        ("VER",),
    ),
}


def codigo(modulo: str, accion: str) -> str:
    """PRENDAS + CREAR -> 'prendas:crear'"""
    return f"{modulo.lower()}:{accion.lower()}"


def catalogo() -> list[dict]:
    """Todos los permisos del sistema, en el orden en que se muestran."""
    filas = []
    for modulo, (etiqueta, _desc, acciones) in MODULOS.items():
        for accion in acciones:
            filas.append({
                "codigo": codigo(modulo, accion),
                "modulo": modulo,
                "accion": accion,
                "nombre": f"{ACCIONES[accion]} {etiqueta.lower()}",
                "descripcion": f"{ACCIONES[accion]} en el modulo {etiqueta}",
            })
    return filas


def todos_los_codigos() -> list[str]:
    return [p["codigo"] for p in catalogo()]


def _codigos(modulo: str, *acciones: str) -> list[str]:
    return [codigo(modulo, a) for a in acciones]


# Permisos con los que arranca cada rol del seed. El administrador lleva todo;
# los demas solo lo que necesitan para su trabajo.
PERMISOS_POR_ROL: dict[str, list[str]] = {
    "administrador": todos_los_codigos(),
    "encargado": [
        *_codigos("CATALOGOS", "VER"),
        *_codigos("SUCURSALES", "VER"),
        *_codigos("PRENDAS", "VER", "EDITAR"),
        *_codigos("INVENTARIO", "VER", "CREAR", "EDITAR", "ELIMINAR"),
        *_codigos("RESERVAS", "VER", "CREAR", "EDITAR", "ELIMINAR"),
        *_codigos("REPORTES", "VER"),
    ],
    "cajero": [
        *_codigos("PRENDAS", "VER"),
        *_codigos("INVENTARIO", "VER"),
        *_codigos("RESERVAS", "VER", "EDITAR"),
        *_codigos("VENTAS", "VER", "CREAR", "EDITAR"),
        *_codigos("PAGOS", "VER", "CREAR"),
    ],
    # El cliente no entra al panel: usa el catalogo publico, que no pide permisos.
    "cliente": [],
}

DESCRIPCION_ROLES = {
    "administrador": "Acceso total al sistema",
    "encargado": "Inventario y reservas de su sucursal",
    "cajero": "Ventas y cobros en caja",
    "cliente": "Compra en la tienda en linea",
}
