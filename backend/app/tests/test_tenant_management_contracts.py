import pytest
from pydantic import ValidationError

from app.schemas.platform_admin import UpdateTenantRequest, UpdateTenantStatusRequest


def test_normalizes_tenant_update():
    payload = UpdateTenantRequest(name="  Comercializadora   del Norte ", slug=" Comercializadora-Norte ")
    assert payload.name == "Comercializadora del Norte"
    assert payload.slug == "comercializadora-norte"


@pytest.mark.parametrize("slug", ["con espacios", "-inicio", "fin-", "doble--guion", "acentó"])
def test_rejects_invalid_slugs(slug):
    with pytest.raises(ValidationError):
        UpdateTenantRequest(name="Empresa", slug=slug)


def test_rejects_blank_name():
    with pytest.raises(ValidationError):
        UpdateTenantRequest(name="   ", slug="empresa")


def test_status_requires_boolean():
    assert UpdateTenantStatusRequest(is_active=False).is_active is False
    with pytest.raises(ValidationError):
        UpdateTenantStatusRequest()
