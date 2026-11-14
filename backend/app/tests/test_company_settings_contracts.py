from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.company_settings import CompanySettingsPayload


def valid_payload(**changes):
    data = dict(name="  Comercializadora   del Norte ", country="México", currency="mxn",
        default_tax_rate="16", quote_validity_days=15, quote_prefix=" cot ")
    data.update(changes)
    return CompanySettingsPayload(**data)


def test_normalizes_company_settings():
    payload = valid_payload(tax_id="abc010101aa1")
    assert payload.name == "Comercializadora del Norte"
    assert payload.currency == "MXN"
    assert payload.quote_prefix == "COT"
    assert payload.tax_id == "ABC010101AA1"


@pytest.mark.parametrize("field,value", [("default_tax_rate", 101), ("quote_validity_days", 0), ("currency", "peso")])
def test_rejects_invalid_commercial_defaults(field, value):
    with pytest.raises(ValidationError):
        valid_payload(**{field: value})


def test_accepts_zero_tax():
    assert valid_payload(default_tax_rate=0).default_tax_rate == Decimal("0")
