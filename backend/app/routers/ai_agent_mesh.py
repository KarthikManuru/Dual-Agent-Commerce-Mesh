import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.product import Product
from app.models.policy import Policy
from app.models.merchant import Merchant
from scripts.seed import MERCHANT_ID

router = APIRouter(tags=["Agent-to-Agent Machine Interface"])


@router.get("/.well-known/ai-commerce")
async def get_ai_commerce_manifest(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Standard Machine-Readable Discovery Manifest:
    Allows third-party AI buyer agents to discover this merchant, supported protocols,
    currencies, commercial policies, and interaction endpoints.
    """
    stmt = select(Merchant).where(Merchant.id == MERCHANT_ID)
    res = await db.execute(stmt)
    merchant = res.scalar_one_or_none()

    return {
        "manifest_version": "1.0.0",
        "mesh_standard": "Dual-Agent Autonomous Commerce Protocol (DA-ACP)",
        "merchant": {
            "merchant_id": str(MERCHANT_ID),
            "name": merchant.name if merchant else "NovaSound Audio Tech",
            "settlement_currency": "INR",
            "supported_currencies": ["INR"],
            "capabilities": [
                "AUTONOMOUS_PRICE_NEGOTIATION",
                "COMPLEMENTARY_CROSS_SELL_BUNDLING",
                "DYNAMIC_VOLUME_DISCOUNTING",
                "DETERMINISTIC_FINANCIAL_GUARD",
                "REALTIME_WEBSOCKET_TELEMETRY",
                "CRYPTOGRAPHIC_AUDIT_LOGGING",
            ],
        },
        "endpoints": {
            "catalog": "/ai/catalog",
            "policies": "/ai/policies",
            "conversational_chat": "/sessions/chat",
            "direct_negotiation": "/sessions/negotiate",
            "order_creation": "/orders",
            "order_verification": "/orders/{order_id}/verify",
            "realtime_events_ws": "/ws/orders",
        },
        "settlement": {
            "payment_processor": "Razorpay Test Mode",
            "verification_algorithm": "HMAC-SHA256",
            "idempotency_supported": True,
        },
    }


@router.get("/ai/catalog")
async def get_agent_catalog(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Agent-Readable Product & Inventory Catalog Feed:
    Structured data designed for machine consumption, inventory querying,
    and commercial evaluation by third-party AI buyer agents.
    """
    stmt = (
        select(Product)
        .options(joinedload(Product.inventory))
        .where(Product.is_active == True)
        .order_by(Product.name)
    )
    res = await db.execute(stmt)
    products = res.unique().scalars().all()

    items = []
    for p in products:
        avail = p.inventory.available if p.inventory else 0
        items.append({
            "product_id": str(p.id),
            "name": p.name,
            "category": p.category,
            "description": p.description,
            "price_paise": p.price_paise,
            "price_display": f"₹{p.price_paise / 100:,.2f}",
            "currency": p.currency,
            "inventory": {
                "in_stock": avail > 0,
                "units_available": avail,
            },
            "negotiable": True,
            "bundle_eligible": True,
            "tags": p.tags or [],
            "image_url": p.image_url,
        })

    return {
        "merchant_id": str(MERCHANT_ID),
        "total_products": len(items),
        "catalog_timestamp": "2026-08-26T00:00:00Z",
        "products": items,
    }


@router.get("/ai/policies")
async def get_agent_policies(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Exposed Read-Only Commercial Negotiation Policy:
    Allows AI buyer agents to understand the merchant's commercial boundaries,
    maximum concession caps, maximum negotiation rounds, and offer TTLs.
    """
    stmt = select(Policy).where(Policy.merchant_id == MERCHANT_ID)
    res = await db.execute(stmt)
    policy = res.scalar_one_or_none()

    if not policy:
        raise HTTPException(status_code=404, detail="Merchant policy not found")

    return {
        "merchant_id": str(MERCHANT_ID),
        "rules_engine": "Deterministic FinancialActionGuard",
        "max_discount_pct": float(policy.max_discount_pct),
        "max_negotiation_rounds": policy.max_negotiation_rounds,
        "offer_ttl_seconds": policy.offer_ttl_seconds,
        "below_cost_selling_allowed": False,
        "concession_rules": {
            "strategy": "TIERED_CONCESSION_MATH",
            "audit_trail": "IMMUTABLE_POSTGRES_EVENTS",
        },
    }
