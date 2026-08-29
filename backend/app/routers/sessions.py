import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.product import Product
from app.models.merchant import Merchant
from app.models.negotiation_session import NegotiationSessionModel
from app.schemas.negotiation import (
    ChatSessionRequest,
    DirectNegotiateRequest,
    NegotiationSessionOut,
    BuyerConfig,
)
from app.schemas.product import ProductOut
from app.agents.intent_parser import parse_user_intent, discover_products
from app.agents.negotiation import negotiation_orchestrator
from scripts.seed import MERCHANT_ID

router = APIRouter(prefix="/sessions", tags=["Autonomous Sessions"])


@router.post("/chat", response_model=NegotiationSessionOut)
async def chat_and_negotiate(
    body: ChatSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Conversational Natural-Language Entry Point:
    1. Parses free-text user prompt (e.g. 'Find me ANC headphones under ₹3,000') using LLM.
    2. Discovers and ranks matching products in the catalog.
    3. Initializes Buyer Agent with parsed budget & persona.
    4. Triggers autonomous Dual-Agent negotiation session with real-time WebSocket broadcast.
    5. On deal agreement, pipes directly into Phase 2 Razorpay order creation.
    """
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # 1. Parse intent via LLM
    parsed_intent, src, model_name, lat = await parse_user_intent(body.query)

    # 2. Discover best product match
    matched_products = await discover_products(db, parsed_intent, limit=1)
    if not matched_products:
        raise HTTPException(status_code=404, detail="No matching products found in catalog for this query.")

    selected_product = matched_products[0]

    # 3. Setup Buyer Config
    budget = body.budget_paise or parsed_intent.max_budget_paise or int(selected_product.price_paise * 1.10)
    strategy = body.buyer_strategy or parsed_intent.buyer_persona or "BARGAIN_HUNTER"

    buyer_config = BuyerConfig(
        name="BuyerAgent-NL",
        strategy=strategy,
        budget_paise=budget,
        persona_notes=f"User requested: '{body.query}' | Extracted intent: {parsed_intent.reasoning}",
    )

    # 4. Execute autonomous negotiation session
    session_res = await negotiation_orchestrator.run_session(
        db=db,
        product=selected_product,
        merchant_id=MERCHANT_ID,
        buyer_config=buyer_config,
    )

    return session_res


@router.post("/negotiate", response_model=NegotiationSessionOut)
async def direct_negotiate(
    body: DirectNegotiateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Direct Autonomous Negotiation on a Selected Product:
    Runs multi-turn LLM negotiation between Buyer and Merchant,
    checked by FinancialActionGuard and streamed over WebSocket.
    """
    try:
        prod_uuid = uuid.UUID(body.product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product UUID")

    stmt = select(Product).options(joinedload(Product.inventory)).where(Product.id == prod_uuid, Product.is_active == True)
    res = await db.execute(stmt)
    product = res.unique().scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found or inactive")

    merchant_id = uuid.UUID(body.merchant_id) if body.merchant_id else MERCHANT_ID

    # Default budget = catalog price if not specified
    budget = body.buyer_budget_paise or int(product.price_paise * 1.05)

    buyer_config = BuyerConfig(
        name="BuyerAgent-Direct",
        strategy=body.buyer_strategy,
        budget_paise=budget,
        persona_notes="Direct catalog negotiation.",
    )

    session_res = await negotiation_orchestrator.run_session(
        db=db,
        product=product,
        merchant_id=merchant_id,
        buyer_config=buyer_config,
    )

    return session_res


@router.get("", response_model=List[NegotiationSessionOut])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List historical negotiation sessions with full transcript and outcome."""
    stmt = (
        select(NegotiationSessionModel)
        .options(joinedload(NegotiationSessionModel.product))
        .order_by(NegotiationSessionModel.created_at.desc())
        .limit(20)
    )
    res = await db.execute(stmt)
    sessions = res.unique().scalars().all()

    output = []
    for s in sessions:
        output.append(
            NegotiationSessionOut(
                session_id=str(s.id),
                product=ProductOut.model_validate(s.product),
                buyer=BuyerConfig(
                    name=s.buyer_name,
                    strategy=s.buyer_strategy,  # type: ignore
                    budget_paise=s.buyer_budget_paise,
                ),
                messages=s.messages,  # type: ignore
                outcome=s.outcome,  # type: ignore
                agreed_price_paise=s.agreed_price_paise,
                discount_achieved_pct=float(s.discount_achieved_pct) if s.discount_achieved_pct else 0.0,
                bundle_included=s.bundle_data,  # type: ignore
                total_rounds=s.total_rounds,
                order_id=str(s.order_id) if s.order_id else None,
                duration_ms=s.duration_ms,
                created_at=s.created_at,
            )
        )
    return output
