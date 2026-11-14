from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.company_settings import CompanySettingsPayload, CompanySettingsResponse
from app.security.permissions import require_permission

router = APIRouter()


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
    for key, value in payload.model_dump().items():
        setattr(tenant, key, value)
    db.commit()
    db.refresh(tenant)
    return _serialize(tenant)
