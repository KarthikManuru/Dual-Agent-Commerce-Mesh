import uuid
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.policy import Policy

router = APIRouter(prefix="/policies", tags=["Policies"])


class PolicyUpdate(BaseModel):
    max_discount_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    min_margin_pct: Optional[Decimal] = Field(None, ge=0, le=100)
    max_negotiation_rounds: Optional[int] = Field(None, ge=1, le=10)
    max_order_value_paise: Optional[int] = Field(None, ge=100)
    offer_ttl_seconds: Optional[int] = Field(None, ge=10, le=86400)


class PolicyOut(BaseModel):
    id: uuid.UUID
    merchant_id: uuid.UUID
    max_discount_pct: Decimal
    min_margin_pct: Decimal
    max_negotiation_rounds: int
    max_order_value_paise: int
    offer_ttl_seconds: int

    model_config = {"from_attributes": True}


@router.get("/{merchant_id}", response_model=PolicyOut)
async def get_policy(
    merchant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Policy).where(Policy.merchant_id == merchant_id)
    res = await db.execute(stmt)
    policy = res.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Merchant policy not found")
    return policy


@router.patch("/{merchant_id}", response_model=PolicyOut)
async def update_policy(
    merchant_id: uuid.UUID,
    body: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    On-the-fly merchant policy update.
    Instantly reconfigures FinancialActionGuard bounds for subsequent AI agent negotiations.
    """
    stmt = select(Policy).where(Policy.merchant_id == merchant_id)
    res = await db.execute(stmt)
    policy = res.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Merchant policy not found")

    if body.max_discount_pct is not None:
        policy.max_discount_pct = body.max_discount_pct
    if body.min_margin_pct is not None:
        policy.min_margin_pct = body.min_margin_pct
    if body.max_negotiation_rounds is not None:
        policy.max_negotiation_rounds = body.max_negotiation_rounds
    if body.max_order_value_paise is not None:
        policy.max_order_value_paise = body.max_order_value_paise
    if body.offer_ttl_seconds is not None:
        policy.offer_ttl_seconds = body.offer_ttl_seconds

    await db.commit()
    await db.refresh(policy)
    return policy
