import unittest
from decimal import Decimal

from app.api.v1.dashboard import _money
from app.schemas.dashboard import DashboardMetrics, DashboardResponse


class DashboardContractTests(unittest.TestCase):
    def test_money_is_normalized_to_two_decimals(self):
        self.assertEqual(_money("123.456"), Decimal("123.46"))

    def test_dashboard_accepts_empty_collections(self):
        response = DashboardResponse(
            metrics=DashboardMetrics(
                active_clients=0,
                open_opportunities=0,
                pipeline_value=0,
                weighted_pipeline_value=0,
                pending_activities=0,
                overdue_activities=0,
                pending_quotes=0,
                accepted_quotes_value=0,
            ),
            pipeline=[],
            upcoming_activities=[],
            recent_quotes=[],
        )
        self.assertEqual(response.metrics.active_clients, 0)
        self.assertEqual(response.upcoming_activities, [])
