"""Fabrica de routers CRUD para tablas simples (catalogos base).

Para tablas con logica de negocio (inventario, reservas, ventas) NO usar esta
fabrica: crear su propio modulo con router + service, como indica el informe.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import create_model
from sqlalchemy.exc import IntegrityError

from app.core.database import to_dict
from app.core.deps import get_db, require_roles


def crud_router(model, nombre: str, campos: dict, roles=("administrador",)) -> APIRouter:
    """campos: {"nombre_campo": (tipo, default)} — usar ... como default para requerido."""
    In = create_model(f"{nombre.title()}In", **campos)
    campos_upd = {k: (t | None, None) for k, (t, _d) in campos.items()}
    # Las tablas con bandera `activo` se archivan en vez de borrarse: el PUT
    # tiene que poder volver a activarlas (y desactivarlas a mano).
    if hasattr(model, "activo"):
        campos_upd["activo"] = (bool | None, None)
    Upd = create_model(f"{nombre.title()}Upd", **campos_upd)
    router = APIRouter()
    admin = require_roles(*roles)

    @router.get("", summary=f"Listar {nombre}s")
    def listar(db=Depends(get_db)):
        return [to_dict(f) for f in db.query(model).all()]

    @router.post("", status_code=201, summary=f"Crear {nombre}")
    def crear(datos: In, db=Depends(get_db), _=Depends(admin)):
        fila = model(**datos.model_dump())
        db.add(fila)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(400, "Registro duplicado o referencia inexistente")
        db.refresh(fila)
        return to_dict(fila)

    @router.put("/{id}", summary=f"Actualizar {nombre}")
    def actualizar(id: int, datos: Upd, db=Depends(get_db), _=Depends(admin)):
        fila = db.get(model, id)
        if fila is None:
            raise HTTPException(404, f"{nombre} no encontrado")
        for k, v in datos.model_dump(exclude_unset=True).items():
            setattr(fila, k, v)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(400, "Datos invalidos")
        db.refresh(fila)
        return to_dict(fila)

    @router.delete("/{id}", summary=f"Eliminar {nombre}")
    def eliminar(id: int, db=Depends(get_db), _=Depends(admin)):
        fila = db.get(model, id)
        if fila is None:
            raise HTTPException(404, f"{nombre} no encontrado")
        try:
            db.delete(fila)
            db.commit()
        except IntegrityError:
            db.rollback()
            if hasattr(fila, "activo"):
                db.refresh(fila)
                fila.activo = False
                db.commit()
                return {"detail": f"{nombre} tiene registros asociados: se desactivo en su lugar"}
            raise HTTPException(400, f"No se puede eliminar: {nombre} tiene registros asociados")
        return {"detail": f"{nombre} eliminado"}

    return router
