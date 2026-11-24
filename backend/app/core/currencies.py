"""Monedas con las que trabaja Flowdesk.

Cada oportunidad, cotización y producto/servicio guarda su propia moneda. Al
crearlos sin indicarla se usa la moneda configurada de la empresa
(tenants.currency). Para admitir otra moneda basta con agregarla aquí y en
frontend/app/src/app/core/models/currency.models.ts.
"""

from typing import Literal

from sqlalchemy.orm import Session

CurrencyCode = Literal["MXN", "USD"]
SUPPORTED_CURRENCIES: tuple[str, ...] = ("MXN", "USD")
DEFAULT_CURRENCY = "MXN"


def tenant_currency(db: Session, tenant_id) -> str:
    """Moneda predeterminada de la empresa (la de Configuración)."""
    from app.models.tenant import Tenant  # import local: evita ciclos con los modelos

    currency = db.query(Tenant.currency).filter(Tenant.id == tenant_id).scalar()
    return currency if currency in SUPPORTED_CURRENCIES else DEFAULT_CURRENCY
