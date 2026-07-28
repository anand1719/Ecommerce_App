from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.sale import SaleStatus


class SaleItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(gt=0, le=999)


class SaleCreate(BaseModel):
    items: list[SaleItemCreate] = Field(min_length=1)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2, max_digits=12)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2, max_digits=12)


class SaleStatusUpdate(BaseModel):
    status: SaleStatus


class SaleItemResponse(BaseModel):
    id: str
    product_id: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class SaleResponse(BaseModel):
    id: str
    customer_id: str
    status: SaleStatus
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    items: list[SaleItemResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

