from app.services.saas_limits import RESOURCE_CONFIG


def test_limit_resources_have_tenant_fields():
    assert RESOURCE_CONFIG["users"][1] == "max_users"
    assert RESOURCE_CONFIG["clients"][1] == "max_clients"
    assert RESOURCE_CONFIG["products"][1] == "max_products"
