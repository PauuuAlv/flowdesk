import unittest
from datetime import date
from decimal import Decimal
from pydantic import ValidationError
from app.schemas.quote import SaveQuoteRequest,calculate_totals
class QuoteContractTests(unittest.TestCase):
    def payload(self,**changes):
        data=dict(client_id="c",owner_user_id="u",issue_date=date(2026,11,13),valid_until=date(2026,11,30),discount=Decimal("100"),tax_rate=Decimal("16"),items=[{"description":"Servicio mensual","quantity":2,"unit_price":500}]);data.update(changes);return SaveQuoteRequest(**data)
    def test_totals_include_discount_and_tax(self):
        self.assertEqual(calculate_totals(self.payload()),(Decimal("1000.00"),Decimal("144.00"),Decimal("1044.00")))
    def test_requires_at_least_one_item(self):
        with self.assertRaises(ValidationError):self.payload(items=[])
    def test_rejects_invalid_validity(self):
        with self.assertRaises(ValidationError):self.payload(valid_until=date(2026,11,1))
