"""Cambios de esquema sobre bases que ya existen (Neon y la SQLite local).

`create_all` crea las tablas nuevas pero no agrega columnas a las que ya estan
creadas. Cada cambio revisa primero si ya se aplico, asi que es seguro correrlo
en cada arranque de la API y en el seed.
"""
from sqlalchemy import inspect, text


def _prenda_publicado(conexion) -> None:
    columnas = {c["name"] for c in inspect(conexion).get_columns("prenda")}
    if "publicado" in columnas:
        return

    falso = "0" if conexion.dialect.name == "sqlite" else "FALSE"
    conexion.execute(text(
        f"ALTER TABLE prenda ADD COLUMN publicado BOOLEAN NOT NULL DEFAULT {falso}"
    ))
    # Antes toda prenda activa salia en la tienda. Siguen publicadas solo las que
    # se pueden vender (tienen unidades en alguna sucursal); el resto queda sin
    # publicar hasta que el administrador cargue su stock y la publique.
    conexion.execute(text("""
        UPDATE prenda SET publicado = :si
        WHERE activo = :si AND EXISTS (
            SELECT 1 FROM variante v
            JOIN inventario i ON i.variante_id = v.id
            WHERE v.prenda_id = prenda.id AND i.cantidad > 0
        )
    """), {"si": True})


def _columna_nueva(conexion, tabla: str, columna: str, definicion: str) -> None:
    """Agrega una columna que admite nulos si todavia no existe."""
    if not inspect(conexion).has_table(tabla):
        return
    if columna in {c["name"] for c in inspect(conexion).get_columns(tabla)}:
        return
    conexion.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}"))


def aplicar(engine) -> None:
    with engine.begin() as conexion:
        if inspect(conexion).has_table("prenda"):
            _prenda_publicado(conexion)
        # Ciclo 3: promocion aplicada a cada linea de venta (CU18) y cuenta del
        # proveedor para su portal (CU9).
        _columna_nueva(conexion, "detalle_venta", "promocion_id", "INTEGER REFERENCES promocion(id)")
        _columna_nueva(conexion, "proveedor", "usuario_id", "INTEGER REFERENCES usuario(id)")
        # La compra parte de la oferta: a que prenda corresponde un producto
        # ofrecido y de que producto salio cada linea de compra.
        _columna_nueva(conexion, "producto_proveedor", "prenda_id", "INTEGER REFERENCES prenda(id)")
        _columna_nueva(conexion, "detalle_compra", "producto_proveedor_id",
                       "INTEGER REFERENCES producto_proveedor(id)")
        # Ciclo 5: delivery de las compras en linea (CU29). La tabla `envio` la
        # crea create_all; aqui van las columnas que le faltan a lo que ya existe.
        _columna_nueva(conexion, "sucursal", "latitud", "FLOAT")
        _columna_nueva(conexion, "sucursal", "longitud", "FLOAT")
        _columna_nueva(conexion, "venta", "tipo_entrega", "VARCHAR(15)")
        _columna_nueva(conexion, "venta", "costo_envio", "NUMERIC(12, 2)")
        # Las ventas anteriores al delivery se retiraban todas en sucursal.
        if inspect(conexion).has_table("venta"):
            conexion.execute(text(
                "UPDATE venta SET tipo_entrega = 'sucursal' WHERE tipo_entrega IS NULL"))
            conexion.execute(text("UPDATE venta SET costo_envio = 0 WHERE costo_envio IS NULL"))
