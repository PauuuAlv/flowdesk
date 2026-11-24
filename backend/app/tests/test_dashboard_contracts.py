import unittest
from decimal import Decimal

from app.api.v1.dashboard import _money, _totals
from app.schemas.dashboard import DashboardMetrics, DashboardResponse


class DashboardContractTests(unittest.TestCase):
    def test_money_is_normalized_to_two_decimals(self):
        self.assertEqual(_money("123.456"), Decimal("123.46"))

    def test_dashboard_accepts_empty_collections(self):
        response = DashboardResponse(
            metrics=DashboardMetrics(
                active_clients=0,
                open_opportunities=0,
                pipeline_value=[],
                weighted_pipeline_value=[],
                pending_activities=0,
                overdue_activities=0,
                pending_quotes=0,
                accepted_quotes_value=[],
            ),
            pipeline=[],
            upcoming_activities=[],
            recent_quotes=[],
        )
        self.assertEqual(response.metrics.active_clients, 0)
        self.assertEqual(response.upcoming_activities, [])

    def test_totals_never_mix_currencies(self):
        totals = _totals([("USD", "10"), ("MXN", "100.5"), ("USD", "5.255")], "MXN")
        self.assertEqual(
            [(t.currency, t.amount) for t in totals],
            [("MXN", Decimal("100.50")), ("USD", Decimal("15.26"))],
        )

    def test_company_currency_always_first_even_when_empty(self):
        totals = _totals([("USD", "3")], "MXN")
        self.assertEqual([(t.currency, t.amount) for t in totals], [("MXN", Decimal("0.00")), ("USD", Decimal("3.00"))])
