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


def aplicar(engine) -> None:
    with engine.begin() as conexion:
        if inspect(conexion).has_table("prenda"):
            _prenda_publicado(conexion)
