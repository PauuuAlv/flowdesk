import pytest
from pydantic import ValidationError

from app.core.plans import get_plan
from app.schemas.platform_admin import CreateTenantRequest, UpdateTenantSubscriptionRequest


def test_basic_plan_limits_are_defined():
    plan = get_plan("basic")
    assert plan["max_users"] == 5
    assert plan["max_clients"] == 100


def test_new_tenant_defaults_to_basic_plan():
    payload = CreateTenantRequest(name="Empresa", slug="empresa", admin_email="admin@empresa.com")
    assert payload.plan_key == "basic"


def test_rejects_unknown_plan():
    with pytest.raises(ValidationError):
        UpdateTenantSubscriptionRequest(plan_key="unlimited", subscription_status="active")
