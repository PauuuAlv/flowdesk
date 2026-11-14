import unittest
from decimal import Decimal
from pydantic import ValidationError

from app.schemas.product import CreateProductRequest


class ProductContractTests(unittest.TestCase):
    def test_normalizes_sku_and_text(self):
        item = CreateProductRequest(name="  Licencia   Flowdesk ", sku=" fd-pro.01 ", item_type="service", unit="license", base_price="1200", tax_rate="16")
        self.assertEqual(item.name, "Licencia Flowdesk")
        self.assertEqual(item.sku, "FD-PRO.01")
        self.assertEqual(item.base_price, Decimal("1200"))

    def test_rejects_invalid_tax(self):
        with self.assertRaises(ValidationError):
            CreateProductRequest(name="Servicio", sku="SERV-01", item_type="service", unit="service", base_price=100, tax_rate=101)
