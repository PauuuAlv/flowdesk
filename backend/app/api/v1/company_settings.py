import io
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.company_settings import CompanySettingsPayload, CompanySettingsResponse
from app.security.permissions import require_permission

router = APIRouter()
MAX_LOGO_BYTES = 5 * 1024 * 1024
LOGO_SIZE = (800, 800)


def _logo_directory() -> Path:
    directory = Path(settings.MEDIA_ROOT).resolve() / "logos"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _delete_local_logo(tenant_id) -> None:
    path = _logo_directory() / f"{tenant_id}.webp"
    if path.exists():
        path.unlink()


def _get(tenant_id, db: Session) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def _serialize(tenant: Tenant) -> CompanySettingsResponse:
    return CompanySettingsResponse(
        id=str(tenant.id), slug=tenant.slug, name=tenant.name,
        legal_name=tenant.legal_name, tax_id=tenant.tax_id,
        contact_email=tenant.contact_email, contact_phone=tenant.contact_phone,
        website=tenant.website, logo_url=tenant.logo_url,
        address_line=tenant.address_line, city=tenant.city, state=tenant.state,
        postal_code=tenant.postal_code, country=tenant.country or "México",
        currency=tenant.currency or "MXN", default_tax_rate=tenant.default_tax_rate,
        quote_validity_days=tenant.quote_validity_days, quote_prefix=tenant.quote_prefix,
        payment_instructions=tenant.payment_instructions,
    )


@router.get("", response_model=CompanySettingsResponse)
def get_company_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("settings.view")),
):
    return _serialize(_get(current_user.tenant_id, db))


@router.patch("", response_model=CompanySettingsResponse)
def update_company_settings(
    payload: CompanySettingsPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("settings.update")),
):
    tenant = _get(current_user.tenant_id, db)
    for key, value in payload.model_dump(exclude={"logo_url"}).items():
        setattr(tenant, key, value)
    db.commit()
    db.refresh(tenant)
    return _serialize(tenant)


@router.post("/logo", response_model=CompanySettingsResponse)
async def upload_company_logo(
    logo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("settings.update")),
):
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if logo.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Logo must be JPG, PNG or WebP")
    content = await logo.read(MAX_LOGO_BYTES + 1)
    if len(content) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=413, detail="Logo exceeds 5 MB")
    try:
        image = Image.open(io.BytesIO(content))
        if image.width * image.height > 25_000_000:
            raise ValueError("Image dimensions are too large")
        image.verify()
        image = Image.open(io.BytesIO(content))
        image.thumbnail(LOGO_SIZE)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid image file") from exc

    tenant = _get(current_user.tenant_id, db)
    destination = _logo_directory() / f"{tenant.id}.webp"
    temporary = destination.with_suffix(".tmp")
    image.save(temporary, format="WEBP", quality=88, method=6)
    temporary.replace(destination)
    tenant.logo_url = f"/api/company-settings/logo/public/{tenant.id}?v={int(time.time())}"
    db.commit(); db.refresh(tenant)
    return _serialize(tenant)


@router.delete("/logo", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_logo(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("settings.update")),
):
    tenant = _get(current_user.tenant_id, db)
    _delete_local_logo(tenant.id)
    tenant.logo_url = None
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/logo/public/{tenant_id}", include_in_schema=False)
def public_company_logo(tenant_id: uuid.UUID, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.logo_url.is_not(None)).first()
    path = _logo_directory() / f"{tenant_id}.webp"
    if not tenant or not path.exists():
        raise HTTPException(status_code=404, detail="Logo not found")
    return FileResponse(path, media_type="image/webp", headers={"Cache-Control": "public, max-age=86400"})
