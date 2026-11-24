import unittest
from datetime import date
from decimal import Decimal
from pydantic import ValidationError
from app.api.v1.quotes import _included_tax
from app.schemas.quote import SaveQuoteRequest,calculate_totals
class QuoteContractTests(unittest.TestCase):
    def payload(self,**changes):
        data=dict(client_id="c",owner_user_id="u",issue_date=date(2026,11,13),valid_until=date(2026,11,30),items=[{"description":"Servicio mensual","quantity":2,"unit_price":500,"discount_percent":10}]);data.update(changes);return SaveQuoteRequest(**data)
    def test_totals_apply_item_discount_without_adding_tax(self):
        self.assertEqual(calculate_totals(self.payload()),(Decimal("1000.00"),Decimal("100.00"),Decimal("900.00")))
    def test_extracts_included_tax_from_historical_total(self):
        self.assertEqual(_included_tax(Decimal("12500"),Decimal("16")),Decimal("1724.14"))
    def test_rejects_discount_above_one_hundred_percent(self):
        with self.assertRaises(ValidationError):self.payload(items=[{"description":"Servicio","quantity":1,"unit_price":500,"discount_percent":101}])
    def test_requires_at_least_one_item(self):
        with self.assertRaises(ValidationError):self.payload(items=[])
    def test_rejects_invalid_validity(self):
        with self.assertRaises(ValidationError):self.payload(valid_until=date(2026,11,1))
