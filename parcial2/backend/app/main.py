from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.database import init_db
from .modules.auth.router import router as auth_router
from .modules.planes.router import router as planes_router
from .modules.sucursales.router import router as sucursales_router
from .modules.suscripciones.router import router as suscripciones_router
from .modules.tenants.router import router as tenants_router


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "SaaS multitenant para tiendas de ropa. Parcial 2 SI2 UAGRM.\n\n"
            "Aislamiento central por `tenant_id` via listener de SQLAlchemy "
            "`do_orm_execute` + `with_loader_criteria` sobre `TenantMixin`."
        ),
        lifespan=lifespan,
    )

    origins = [o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins else []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_v1_prefix
    app.include_router(auth_router, prefix=prefix)
    app.include_router(tenants_router, prefix=prefix)
    app.include_router(sucursales_router, prefix=prefix)
    app.include_router(suscripciones_router, prefix=prefix)
    app.include_router(planes_router, prefix=prefix)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
