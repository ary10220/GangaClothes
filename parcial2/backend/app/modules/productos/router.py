from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, require_roles, require_tenant
from . import schemas, service


router = APIRouter(prefix="/productos", tags=["CU-08 Productos y Variantes"])
router_alias = APIRouter(prefix="/prendas", tags=["CU-08 Productos y Variantes (Alias /prendas)"])


def _endpoint(method: str, path: str, **kwargs: Any):
    """Registra el endpoint tanto en `/productos` como en `/prendas`."""
    def decorator(func: Any) -> Any:
        getattr(router, method)(path, **kwargs)(func)
        getattr(router_alias, method)(path, **kwargs)(func)
        return func
    return decorator


class PublicarIn(BaseModel):
    confirmar_sin_stock: bool = False


# ==============================================================================
# Endpoints de Producto / Prenda
# ==============================================================================
@_endpoint("get", "", response_model=list[schemas.ProductoOut])
def listar_productos(
    categoria_id: int | None = Query(default=None),
    temporada_id: int | None = Query(default=None),
    proveedor_id: int | None = Query(default=None),
    publicado: bool | None = Query(default=None),
    activo: bool | None = Query(default=None),
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """CU-08: Lista productos del tenant con filtros opcionales."""
    return service.listar_productos(
        db,
        scope.tenant_id,
        categoria_id=categoria_id,
        temporada_id=temporada_id,
        proveedor_id=proveedor_id,
        publicado=publicado,
        activo=activo,
    )


@_endpoint("get", "/catalogo-interno", response_model=list[schemas.ProductoOut])
def catalogo_interno(
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """Compatibilidad: catalogo interno con prendas activas y sus variantes."""
    return service.listar_productos(db, scope.tenant_id, activo=True)


@_endpoint("post", "", response_model=schemas.ProductoOut, status_code=status.HTTP_201_CREATED)
def crear_producto(
    body: schemas.ProductoIn,
    scope: TenantScope = Depends(require_roles("admin", "encargado")),
    db: Session = Depends(get_db),
):
    """CU-08: Da de alta un nuevo producto y sus variantes opcionales.
    - Valida limite de productos del plan contratado (409).
    - Valida relaciones de categoria, temporada y proveedor del tenant (404).
    - Valida unicidad de nombre de producto en el tenant (409).
    """
    return service.crear_producto(db, scope.tenant_id, body)


@_endpoint("get", "/{producto_id}", response_model=schemas.ProductoOut)
def obtener_producto(
    producto_id: int,
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.obtener_producto(db, scope.tenant_id, producto_id)


@_endpoint("patch", "/{producto_id}", response_model=schemas.ProductoOut)
def actualizar_producto_patch(
    producto_id: int,
    body: schemas.ProductoUpdateIn,
    scope: TenantScope = Depends(require_roles("admin", "encargado")),
    db: Session = Depends(get_db),
):
    return service.actualizar_producto(db, scope.tenant_id, producto_id, body)


@_endpoint("put", "/{producto_id}", response_model=schemas.ProductoOut)
def actualizar_producto_put(
    producto_id: int,
    body: schemas.ProductoUpdateIn,
    scope: TenantScope = Depends(require_roles("admin", "encargado")),
    db: Session = Depends(get_db),
):
    return service.actualizar_producto(db, scope.tenant_id, producto_id, body)


@_endpoint("delete", "/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(
    producto_id: int,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    service.eliminar_producto(db, scope.tenant_id, producto_id)
    return None


@_endpoint("post", "/{producto_id}/publicar", response_model=schemas.ProductoOut)
def publicar_producto(
    producto_id: int,
    body: PublicarIn | None = None,
    scope: TenantScope = Depends(require_roles("admin", "encargado")),
    db: Session = Depends(get_db),
):
    return service.cambiar_publicacion(db, scope.tenant_id, producto_id, publicado=True)


@_endpoint("post", "/{producto_id}/despublicar", response_model=schemas.ProductoOut)
def despublicar_producto(
    producto_id: int,
    scope: TenantScope = Depends(require_roles("admin", "encargado")),
    db: Session = Depends(get_db),
):
    return service.cambiar_publicacion(db, scope.tenant_id, producto_id, publicado=False)


# ==============================================================================
# Endpoints de Variantes
# ==============================================================================
@_endpoint("get", "/{producto_id}/variantes", response_model=list[schemas.VarianteOut])
def listar_variantes(
    producto_id: int,
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.listar_variantes(db, scope.tenant_id, producto_id)


@_endpoint("post", "/{producto_id}/variantes", response_model=schemas.VarianteOut, status_code=status.HTTP_201_CREATED)
def crear_variante(
    producto_id: int,
    body: schemas.VarianteIn,
    scope: TenantScope = Depends(require_roles("admin", "encargado")),
    db: Session = Depends(get_db),
):
    return service.crear_variante(db, scope.tenant_id, producto_id, body)


@_endpoint("get", "/variantes/{variante_id}", response_model=schemas.VarianteOut)
def obtener_variante(
    variante_id: int,
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.obtener_variante(db, scope.tenant_id, variante_id)


@_endpoint("patch", "/variantes/{variante_id}", response_model=schemas.VarianteOut)
def actualizar_variante_patch(
    variante_id: int,
    body: schemas.VarianteUpdateIn,
    scope: TenantScope = Depends(require_roles("admin", "encargado")),
    db: Session = Depends(get_db),
):
    return service.actualizar_variante(db, scope.tenant_id, variante_id, body)


@_endpoint("put", "/variantes/{variante_id}", response_model=schemas.VarianteOut)
def actualizar_variante_put(
    variante_id: int,
    body: schemas.VarianteUpdateIn,
    scope: TenantScope = Depends(require_roles("admin", "encargado")),
    db: Session = Depends(get_db),
):
    return service.actualizar_variante(db, scope.tenant_id, variante_id, body)


@_endpoint("delete", "/variantes/{variante_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_variante(
    variante_id: int,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    service.eliminar_variante(db, scope.tenant_id, variante_id)
    return None
