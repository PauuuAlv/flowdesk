from datetime import date,datetime
from decimal import Decimal,ROUND_HALF_UP
from typing import Literal
from pydantic import BaseModel,Field,field_validator,model_validator

from app.core.currencies import CurrencyCode

QuoteStatus=Literal["draft","sent","accepted","rejected","expired"]


class QuoteItemRequest(BaseModel):
    product_id:str|None=None
    description:str=Field(min_length=2,max_length=240)
    quantity:Decimal=Field(gt=0,max_digits=12,decimal_places=2)
    unit_price:Decimal=Field(ge=0,max_digits=14,decimal_places=2)
    discount_percent:Decimal=Field(default=0,ge=0,le=100,max_digits=5,decimal_places=2)
    @field_validator("description")
    @classmethod
    def normalize(cls,value:str)->str:return " ".join(value.split())


class SaveQuoteRequest(BaseModel):
    client_id:str
    opportunity_id:str|None=None
    owner_user_id:str
    issue_date:date
    valid_until:date
    # Sin moneda: al crear se usa la de la empresa; al editar se conserva la actual.
    currency:CurrencyCode|None=None
    notes:str|None=Field(default=None,max_length=1000)
    items:list[QuoteItemRequest]=Field(min_length=1,max_length=100)
    @field_validator("notes")
    @classmethod
    def normalize_notes(cls,value:str|None)->str|None:
        value=value.strip() if value else None;return value or None
    @model_validator(mode="after")
    def validate_dates(self):
        if self.valid_until<self.issue_date:raise ValueError("valid_until must not be before issue_date")
        return self


class UpdateQuoteStatusRequest(BaseModel):status:Literal["sent","accepted","rejected"]


class QuoteItemResponse(BaseModel):
    id:str;product_id:str|None;position:int;description:str;quantity:Decimal;unit_price:Decimal;gross_amount:Decimal;discount_percent:Decimal;discount_amount:Decimal;amount:Decimal


class QuoteResponse(BaseModel):
    id:str;folio:str;tenant_name:str;client_id:str;client_name:str;client_contact:str;client_email:str;opportunity_id:str|None;opportunity_name:str|None;owner_user_id:str;owner_name:str
    issue_date:date;valid_until:date;currency:str;discount:Decimal;tax_rate:Decimal;subtotal:Decimal;tax:Decimal;total:Decimal;status:QuoteStatus;notes:str|None;items:list[QuoteItemResponse];created_at:datetime;updated_at:datetime


def calculate_totals(payload:SaveQuoteRequest):
    money=Decimal("0.01")
    subtotal=sum((x.quantity*x.unit_price for x in payload.items),Decimal("0")).quantize(money,ROUND_HALF_UP)
    discount=sum(((x.quantity*x.unit_price)*x.discount_percent/Decimal("100") for x in payload.items),Decimal("0")).quantize(money,ROUND_HALF_UP)
    return subtotal,discount,(subtotal-discount).quantize(money,ROUND_HALF_UP)
