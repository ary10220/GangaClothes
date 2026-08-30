# Importar todos los modelos para que Base.metadata.create_all los registre.
from app.models.usuarios import Usuario, Rol, UsuarioRol, Cliente          # noqa
from app.models.sucursales import Ciudad, Sucursal                          # noqa
from app.models.catalogo import (Categoria, Temporada, Coleccion, Talla,    # noqa
                                 Color, Prenda, Variante, AssetAR)
from app.models.inventario import (Inventario, MovimientoInventario,        # noqa
                                   Proveedor, Compra, DetalleCompra)
from app.models.ventas import (Reserva, DetalleReserva, Venta, DetalleVenta,  # noqa
                               Pago, Promocion, PromocionPrenda)
from app.models.ia import EventoNavegacion, Recomendacion                   # noqa
