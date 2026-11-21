import unittest
from decimal import Decimal
from pydantic import ValidationError

from app.schemas.product import CreateProductRequest


class ProductContractTests(unittest.TestCase):
    def test_normalizes_sku_and_text(self):
        item = CreateProductRequest(name="  Licencia   Flowdesk ", sku=" fd-pro.01 ", item_type="service", unit_id="00000000-0000-0000-0000-000000000001", brand_id=None, base_price="1200", tax_rate="16")
        self.assertEqual(item.name, "Licencia Flowdesk")
        self.assertEqual(item.sku, "FD-PRO.01")
        self.assertEqual(item.base_price, Decimal("1200"))

    def test_allows_automatic_sku(self):
        item = CreateProductRequest(name="Instalación inicial", item_type="service", unit_id="00000000-0000-0000-0000-000000000001", brand_id=None, base_price=800, tax_rate=0)
        self.assertIsNone(item.sku)

    def test_rejects_invalid_tax(self):
        with self.assertRaises(ValidationError):
            CreateProductRequest(name="Servicio", sku="SERV-01", item_type="service", unit_id="00000000-0000-0000-0000-000000000001", brand_id=None, base_price=100, tax_rate=101)
