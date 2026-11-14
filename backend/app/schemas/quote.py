from datetime import date,datetime
from decimal import Decimal,ROUND_HALF_UP
from typing import Literal
from pydantic import BaseModel,Field,field_validator,model_validator

QuoteStatus=Literal["draft","sent","accepted","rejected","expired"]


class QuoteItemRequest(BaseModel):
    description:str=Field(min_length=2,max_length=240)
    quantity:Decimal=Field(gt=0,max_digits=12,decimal_places=2)
    unit_price:Decimal=Field(ge=0,max_digits=14,decimal_places=2)
    @field_validator("description")
    @classmethod
    def normalize(cls,value:str)->str:return " ".join(value.split())


class SaveQuoteRequest(BaseModel):
    client_id:str
    opportunity_id:str|None=None
    owner_user_id:str
    issue_date:date
    valid_until:date
    discount:Decimal=Field(default=0,ge=0,max_digits=14,decimal_places=2)
    tax_rate:Decimal=Field(default=16,ge=0,le=100,max_digits=5,decimal_places=2)
    notes:str|None=Field(default=None,max_length=1000)
    items:list[QuoteItemRequest]=Field(min_length=1,max_length=100)
    @field_validator("notes")
    @classmethod
    def normalize_notes(cls,value:str|None)->str|None:
        value=value.strip() if value else None;return value or None
    @model_validator(mode="after")
    def validate_dates_and_discount(self):
        if self.valid_until<self.issue_date:raise ValueError("valid_until must not be before issue_date")
        subtotal=sum((item.quantity*item.unit_price for item in self.items),Decimal("0"))
        if self.discount>subtotal:raise ValueError("discount cannot exceed subtotal")
        return self


class UpdateQuoteStatusRequest(BaseModel):status:Literal["sent","accepted","rejected"]


class QuoteItemResponse(BaseModel):
    id:str;position:int;description:str;quantity:Decimal;unit_price:Decimal;amount:Decimal


class QuoteResponse(BaseModel):
    id:str;folio:str;tenant_name:str;client_id:str;client_name:str;client_contact:str;client_email:str;opportunity_id:str|None;opportunity_name:str|None;owner_user_id:str;owner_name:str
    issue_date:date;valid_until:date;currency:str;discount:Decimal;tax_rate:Decimal;subtotal:Decimal;tax:Decimal;total:Decimal;status:QuoteStatus;notes:str|None;items:list[QuoteItemResponse];created_at:datetime;updated_at:datetime


def calculate_totals(payload:SaveQuoteRequest):
    money=Decimal("0.01");subtotal=sum((x.quantity*x.unit_price for x in payload.items),Decimal("0")).quantize(money,ROUND_HALF_UP)
    taxable=subtotal-payload.discount;tax=(taxable*payload.tax_rate/Decimal("100")).quantize(money,ROUND_HALF_UP)
    return subtotal,tax,(taxable+tax).quantize(money,ROUND_HALF_UP)
