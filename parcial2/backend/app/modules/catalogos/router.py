from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, require_roles, require_tenant
from . import schemas, service


# ==============================================================================
# Router: Categorias
# ==============================================================================
categorias_router = APIRouter(prefix="/categorias", tags=["CU-09 Categorias"])


@categorias_router.get("", response_model=list[schemas.CategoriaOut])
def listar_categorias(
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.listar_categorias(db, scope.tenant_id)


@categorias_router.post("", response_model=schemas.CategoriaOut, status_code=status.HTTP_201_CREATED)
def crear_categoria(
    body: schemas.CategoriaIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return service.crear_categoria(db, scope.tenant_id, body)


@categorias_router.get("/{categoria_id}", response_model=schemas.CategoriaOut)
def obtener_categoria(
    categoria_id: int,
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.obtener_categoria(db, scope.tenant_id, categoria_id)


@categorias_router.patch("/{categoria_id}", response_model=schemas.CategoriaOut)
def actualizar_categoria(
    categoria_id: int,
    body: schemas.CategoriaUpdateIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return service.actualizar_categoria(db, scope.tenant_id, categoria_id, body)


@categorias_router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_categoria(
    categoria_id: int,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    service.eliminar_categoria(db, scope.tenant_id, categoria_id)
    return None


# ==============================================================================
# Router: Tallas
# ==============================================================================
tallas_router = APIRouter(prefix="/tallas", tags=["CU-09 Tallas"])


@tallas_router.get("", response_model=list[schemas.TallaOut])
def listar_tallas(
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.listar_tallas(db, scope.tenant_id)


@tallas_router.post("", response_model=schemas.TallaOut, status_code=status.HTTP_201_CREATED)
def crear_talla(
    body: schemas.TallaIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return service.crear_talla(db, scope.tenant_id, body)


@tallas_router.get("/{talla_id}", response_model=schemas.TallaOut)
def obtener_talla(
    talla_id: int,
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.obtener_talla(db, scope.tenant_id, talla_id)


@tallas_router.patch("/{talla_id}", response_model=schemas.TallaOut)
def actualizar_talla(
    talla_id: int,
    body: schemas.TallaUpdateIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return service.actualizar_talla(db, scope.tenant_id, talla_id, body)


@tallas_router.delete("/{talla_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_talla(
    talla_id: int,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    service.eliminar_talla(db, scope.tenant_id, talla_id)
    return None


# ==============================================================================
# Router: Colores
# ==============================================================================
colores_router = APIRouter(prefix="/colores", tags=["CU-09 Colores"])


@colores_router.get("", response_model=list[schemas.ColorOut])
def listar_colores(
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.listar_colores(db, scope.tenant_id)


@colores_router.post("", response_model=schemas.ColorOut, status_code=status.HTTP_201_CREATED)
def crear_color(
    body: schemas.ColorIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return service.crear_color(db, scope.tenant_id, body)


@colores_router.get("/{color_id}", response_model=schemas.ColorOut)
def obtener_color(
    color_id: int,
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.obtener_color(db, scope.tenant_id, color_id)


@colores_router.patch("/{color_id}", response_model=schemas.ColorOut)
def actualizar_color(
    color_id: int,
    body: schemas.ColorUpdateIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return service.actualizar_color(db, scope.tenant_id, color_id, body)


@colores_router.delete("/{color_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_color(
    color_id: int,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    service.eliminar_color(db, scope.tenant_id, color_id)
    return None


# ==============================================================================
# Router: Temporadas
# ==============================================================================
temporadas_router = APIRouter(prefix="/temporadas", tags=["CU-09 Temporadas"])


@temporadas_router.get("", response_model=list[schemas.TemporadaOut])
def listar_temporadas(
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.listar_temporadas(db, scope.tenant_id)


@temporadas_router.post("", response_model=schemas.TemporadaOut, status_code=status.HTTP_201_CREATED)
def crear_temporada(
    body: schemas.TemporadaIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return service.crear_temporada(db, scope.tenant_id, body)


@temporadas_router.get("/{temporada_id}", response_model=schemas.TemporadaOut)
def obtener_temporada(
    temporada_id: int,
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.obtener_temporada(db, scope.tenant_id, temporada_id)


@temporadas_router.patch("/{temporada_id}", response_model=schemas.TemporadaOut)
def actualizar_temporada(
    temporada_id: int,
    body: schemas.TemporadaUpdateIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return service.actualizar_temporada(db, scope.tenant_id, temporada_id, body)


@temporadas_router.delete("/{temporada_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_temporada(
    temporada_id: int,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    service.eliminar_temporada(db, scope.tenant_id, temporada_id)
    return None
