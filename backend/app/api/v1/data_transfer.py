"""Exportación e importación masiva en CSV (por módulo o de toda la empresa)."""

from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.security.permissions import require_permission
from app.security.user_auth import get_current_user
from app.services.access_control import get_user_permission_codes
from app.services.data_transfer import (
    ENTITIES, MAX_FILE_BYTES, MAX_ZIP_BYTES, Entity, FileError, can_import, can_view, export_all, export_entity,
    import_files, read_zip, template_entity,
)

router = APIRouter()


def _entity(key: str) -> Entity:
    entity = ENTITIES.get(key)
    if not entity:
        raise HTTPException(status_code=404, detail="Unknown entity")
    return entity


def _permissions(user: User) -> set[str]:
    return set(get_user_permission_codes(user))


def _download(content: bytes, filename: str, media_type: str) -> Response:
    return Response(content=content, media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


async def _read_upload(file: UploadFile, limit: int) -> bytes:
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(status_code=413, detail="File too large")
    return content


@router.get("/entities")
def list_entities(current_user: User = Depends(get_current_user)):
    """Módulos disponibles y lo que el usuario puede hacer con cada uno."""
    permissions = _permissions(current_user)
    return [
        {"key": e.key, "label": e.label, "filename": e.filename,
         "can_export": can_view(e, permissions), "can_import": can_view(e, permissions) and can_import(e, permissions)}
        for e in ENTITIES.values()
    ]


@router.get("/export")
def export_company(db: Session = Depends(get_db), current_user: User = Depends(require_permission("settings.update"))):
    """ZIP con un CSV por cada módulo que el usuario puede ver."""
    permissions = _permissions(current_user)
    entities = [e for e in ENTITIES.values() if can_view(e, permissions)]
    content = export_all(db, current_user.tenant_id, entities)
    return _download(content, f"flowdesk_{date.today().isoformat()}.zip", "application/zip")


@router.post("/import")
async def import_company(file: UploadFile = File(...), db: Session = Depends(get_db),
                         current_user: User = Depends(require_permission("settings.update"))):
    """Importa un ZIP exportado (o con los CSV que se quieran actualizar)."""
    content = await _read_upload(file, MAX_ZIP_BYTES)
    try:
        found = read_zip(content)
    except FileError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_FILE", "message": str(exc)})
    permissions = _permissions(current_user)
    denied = [ENTITIES[k].label for k in found if not (can_view(ENTITIES[k], permissions) and can_import(ENTITIES[k], permissions))]
    if denied:
        raise HTTPException(status_code=403, detail={"code": "IMPORT_FORBIDDEN", "message": f"Sin permiso para importar: {', '.join(denied)}."})
    # El orden de ENTITIES respeta las dependencias (catálogos → productos → clientes → … → cotizaciones).
    files = [(entity, found[key]) for key, entity in ENTITIES.items() if key in found]
    return import_files(db, current_user, files)


@router.get("/{entity_key}/export")
def export_one(entity_key: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entity = _entity(entity_key)
    if not can_view(entity, _permissions(current_user)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    name = entity.filename.replace(".csv", f"_{date.today().isoformat()}.csv")
    return _download(export_entity(db, current_user.tenant_id, entity), name, "text/csv; charset=utf-8")


@router.get("/{entity_key}/template")
def template_one(entity_key: str, current_user: User = Depends(get_current_user)):
    entity = _entity(entity_key)
    if not can_view(entity, _permissions(current_user)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return _download(template_entity(entity), entity.filename.replace(".csv", "_plantilla.csv"), "text/csv; charset=utf-8")


@router.post("/{entity_key}/import")
async def import_one(entity_key: str, file: UploadFile = File(...), db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    entity = _entity(entity_key)
    permissions = _permissions(current_user)
    if not (can_view(entity, permissions) and can_import(entity, permissions)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    content = await _read_upload(file, MAX_FILE_BYTES)
    return import_files(db, current_user, [(entity, content)])
