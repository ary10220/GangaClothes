from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (registra las 28 tablas)
from app.core.config import settings
from app.core.database import Base, engine
from app.modules.auth.router import router as auth_router
from app.modules.catalogos_base.router import router as catalogos_router
from app.modules.usuarios.router import router as usuarios_router
from app.modules.seguridad.router import router as seguridad_router
from app.modules.prendas.router import router as prendas_router, publico as catalogo_publico
from app.modules.inventario.router import router as inventario_router, compras as compras_router
from app.modules.reservas.router import router as reservas_router
from app.modules.ventas.router import router as ventas_router
from app.modules.pagos.router import router as pagos_router
from app.modules.promociones.router import router as promociones_router
from app.modules.reportes.router import router as reportes_router
from app.modules.ia.router import router as ia_router

# En el curso usamos create_all; en un proyecto real se usarian migraciones (Alembic).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GangaClothes API",
    version="0.1.0",
    description="Plataforma inteligente de comercio electronico para tienda de ropa "
                "con vestidores virtuales via realidad aumentada. Sistemas de Informacion II - UAGRM.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["1. Autenticacion (CU1-CU2, CU20-CU21)"])
app.include_router(usuarios_router, prefix="/api/usuarios", tags=["2. Usuarios y roles (CU3)"])
app.include_router(seguridad_router, prefix="/api/seguridad", tags=["2b. Roles, permisos y bitacora (CU3)"])
app.include_router(catalogos_router, prefix="/api/admin", tags=["3. Catalogos base (CU4-CU6, CU8)"])
app.include_router(prendas_router, prefix="/api/prendas", tags=["4. Prendas y variantes (CU7)"])
app.include_router(catalogo_publico, prefix="/api", tags=["5. Catalogo publico (CU16, CU22)"])
app.include_router(inventario_router, prefix="/api/inventario", tags=["6. Inventario (CU11-CU12)"])
app.include_router(compras_router, prefix="/api/compras", tags=["6b. Compras a proveedor (CU10)"])
app.include_router(reservas_router, prefix="/api/reservas", tags=["7. Reservas (CU13, CU23-CU24)"])
app.include_router(ventas_router, prefix="/api/ventas", tags=["8. Ventas (CU14, CU17)"])
app.include_router(pagos_router, prefix="/api/pagos", tags=["9. Pagos (CU15, pasarela CU17)"])
app.include_router(promociones_router, prefix="/api/promociones", tags=["10. Promociones (CU18) [pendiente]"])
app.include_router(reportes_router, prefix="/api/reportes", tags=["11. Reportes (CU19) [pendiente]"])
app.include_router(ia_router, prefix="/api/ia", tags=["12. IA (CU28) [pendiente]"])


@app.get("/", tags=["raiz"])
def raiz():
    return {"proyecto": "GangaClothes", "documentacion": "/docs", "estado": "ok"}
