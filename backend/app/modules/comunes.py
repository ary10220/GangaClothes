"""Fabrica de routers CRUD para tablas simples (catalogos base).

Para tablas con logica de negocio (inventario, reservas, ventas) NO usar esta
fabrica: crear su propio modulo con router + service, como indica el informe.

Cada router generado valida por permiso (no por nombre de rol) y deja constancia
de la escritura en la bitacora. El GET queda publico porque el catalogo del
cliente lo consume sin sesion.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import create_model
from sqlalchemy.exc import DataError, IntegrityError

from app.core.auditoria import registrar
from app.core.database import to_dict
from app.core.deps import get_db, require_permiso


def _nombre_legible(fila, nombre: str) -> str:
    return str(getattr(fila, "nombre", None) or f"{nombre} #{getattr(fila, 'id', '?')}")


def crud_router(model, nombre: str, campos: dict, modulo: str = "CATALOGOS") -> APIRouter:
    """campos: {"nombre_campo": (tipo, default)} — usar ... como default para requerido.

    modulo: a que modulo de permisos pertenece el recurso (CATALOGOS,
    SUCURSALES, INVENTARIO...). De ahi salen los codigos que se exigen.
    """
    In = create_model(f"{nombre.title()}In", **campos)
    campos_upd = {k: (t | None, None) for k, (t, _d) in campos.items()}
    # Las tablas con bandera `activo` se archivan en vez de borrarse: el PUT
    # tiene que poder volver a activarlas (y desactivarlas a mano).
    if hasattr(model, "activo"):
        campos_upd["activo"] = (bool | None, None)
    Upd = create_model(f"{nombre.title()}Upd", **campos_upd)

    router = APIRouter()
    clave = modulo.lower()
    puede_crear = require_permiso(f"{clave}:crear")
    puede_editar = require_permiso(f"{clave}:editar")
    puede_eliminar = require_permiso(f"{clave}:eliminar")

    @router.get("", summary=f"Listar {nombre}s")
    def listar(db=Depends(get_db)):
        return [to_dict(f) for f in db.query(model).all()]

    @router.post("", status_code=201, summary=f"Crear {nombre}")
    def crear(datos: In, peticion: Request, db=Depends(get_db), usuario=Depends(puede_crear)):
        fila = model(**datos.model_dump())
        db.add(fila)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(400, "Registro duplicado o referencia inexistente")
        except DataError:
            # PostgreSQL rechaza textos mas largos que la columna (SQLite no lo valida).
            db.rollback()
            raise HTTPException(400, "Algun campo excede el largo permitido")
        db.refresh(fila)
        registrar(db, modulo=modulo, accion="CREAR", usuario=usuario, peticion=peticion,
                  entidad=nombre, entidad_id=fila.id,
                  detalle=f"Alta de {nombre} '{_nombre_legible(fila, nombre)}'")
        return to_dict(fila)

    @router.put("/{id}", summary=f"Actualizar {nombre}")
    def actualizar(id: int, datos: Upd, peticion: Request, db=Depends(get_db), usuario=Depends(puede_editar)):
        fila = db.get(model, id)
        if fila is None:
            raise HTTPException(404, f"{nombre} no encontrado")
        cambios = datos.model_dump(exclude_unset=True)
        for k, v in cambios.items():
            setattr(fila, k, v)
        try:
            db.commit()
        except (IntegrityError, DataError):
            db.rollback()
            raise HTTPException(400, "Datos invalidos")
        db.refresh(fila)
        # Reactivar o archivar se registra aparte: es lo que mas se audita.
        if list(cambios) == ["activo"]:
            accion, detalle = "EDITAR", (
                f"{'Reactivacion' if cambios['activo'] else 'Archivado'} de "
                f"{nombre} '{_nombre_legible(fila, nombre)}'"
            )
        else:
            accion = "EDITAR"
            detalle = f"Cambios en {nombre} '{_nombre_legible(fila, nombre)}': {', '.join(cambios) or 'sin cambios'}"
        registrar(db, modulo=modulo, accion=accion, usuario=usuario, peticion=peticion,
                  entidad=nombre, entidad_id=fila.id, detalle=detalle)
        return to_dict(fila)

    @router.delete("/{id}", summary=f"Eliminar {nombre}")
    def eliminar(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(puede_eliminar)):
        fila = db.get(model, id)
        if fila is None:
            raise HTTPException(404, f"{nombre} no encontrado")
        etiqueta = _nombre_legible(fila, nombre)
        try:
            db.delete(fila)
            db.commit()
        except IntegrityError:
            db.rollback()
            if hasattr(fila, "activo"):
                db.refresh(fila)
                fila.activo = False
                db.commit()
                registrar(db, modulo=modulo, accion="EDITAR", usuario=usuario, peticion=peticion,
                          entidad=nombre, entidad_id=id, nivel="ALERTA",
                          detalle=f"{nombre} '{etiqueta}' tiene registros asociados: se desactivo")
                return {"detail": f"{nombre} tiene registros asociados: se desactivo en su lugar"}
            registrar(db, modulo=modulo, accion="ELIMINAR", usuario=usuario, peticion=peticion,
                      entidad=nombre, entidad_id=id, nivel="ERROR",
                      detalle=f"Intento fallido de eliminar {nombre} '{etiqueta}': tiene registros asociados")
            raise HTTPException(400, f"No se puede eliminar: {nombre} tiene registros asociados")
        registrar(db, modulo=modulo, accion="ELIMINAR", usuario=usuario, peticion=peticion,
                  entidad=nombre, entidad_id=id, nivel="ALERTA",
                  detalle=f"Baja de {nombre} '{etiqueta}'")
        return {"detail": f"{nombre} eliminado"}

    return router
