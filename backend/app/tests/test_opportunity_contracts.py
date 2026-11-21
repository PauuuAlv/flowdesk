import unittest
from decimal import Decimal
from pydantic import ValidationError
from app.schemas.opportunity import CloseOpportunityRequest, SaveOpportunityRequest


class OpportunityContractTests(unittest.TestCase):
    def test_valid_contract(self):
        value=SaveOpportunityRequest(client_id="00000000-0000-0000-0000-000000000001",owner_user_id="00000000-0000-0000-0000-000000000002",name="  Renovación   anual ",amount=Decimal("12500.50"),stage="proposal",probability=60)
        self.assertEqual(value.name,"Renovación anual")
    def test_probability_is_bounded(self):
        with self.assertRaises(ValidationError):
            SaveOpportunityRequest(client_id="a",owner_user_id="b",name="Venta",amount=10,stage="contact",probability=101)
    def test_stage_key_is_required(self):
        with self.assertRaises(ValidationError):
            SaveOpportunityRequest(client_id="a",owner_user_id="b",name="Venta",amount=10,stage="",probability=10)
    def test_stage_can_use_a_tenant_catalog_key(self):
        value=SaveOpportunityRequest(client_id="a",owner_user_id="b",name="Venta",amount=10,stage="demo-tecnica",probability=45)
        self.assertEqual(value.stage,"demo-tecnica")
    def test_close_detail_is_normalized(self):
        value=CloseOpportunityRequest(stage="cierre-perdido",loss_reason="price",loss_detail="  Fuera de presupuesto  ")
        self.assertEqual(value.loss_detail,"Fuera de presupuesto")


if __name__=="__main__": unittest.main()
