from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class OrderEventOut(BaseModel):
    """Single audit event for an order."""

    id: UUID
    actor: str
    action: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    detail: Optional[dict] = None
    result: str
    prev_hash: Optional[str] = None
    current_hash: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    """Single order response with audit trail."""

    id: UUID
    merchant_id: UUID
    product_id: UUID
    quantity: int
    offer_id: Optional[UUID] = None
    status: str
    unit_price_paise: int
    total_paise: int
    currency: str = "INR"
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    events: list[OrderEventOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    """Paginated order list response."""

    orders: list[OrderOut]
    total: int


class OrderCreate(BaseModel):
    """Request body to create a new order (expanded in Phase 2)."""

    product_id: UUID
    merchant_id: UUID
    quantity: int = 1
    offer_id: Optional[UUID] = None
