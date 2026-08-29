from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from pydantic import BaseModel, Field

from app.schemas.product import ProductOut


class BundleItem(BaseModel):
    product_id: str
    name: str
    category: str
    original_price_paise: int
    bundled_price_paise: int
    discount_pct: float


class NegotiationMessage(BaseModel):
    sender: Literal["BUYER_AGENT", "MERCHANT_AGENT", "FINANCIAL_GUARD", "USER"]
    intent: Literal[
        "OFFER",
        "COUNTER",
        "ACCEPT",
        "REJECT",
        "GUARD_ALLOW",
        "GUARD_DENY",
        "BUNDLE_OFFER",
        "DISCOVERY"
    ]
    offered_price_paise: int
    discount_pct: float = 0.0
    reasoning_text: str
    reason_codes: list[str] = Field(default_factory=list)
    bundle_suggestion: BundleItem | None = None
    round: int = 1
    
    # Transparency & Verifiability metadata
    reasoning_source: Literal["LLM", "HEURISTIC_FALLBACK", "DETERMINISTIC_GUARD", "USER_ACTION"] = "LLM"
    model_name: str = "gemini-2.5-flash"
    latency_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BuyerConfig(BaseModel):
    name: str = "BuyerAgent-Alpha"
    strategy: Literal["EAGER", "BARGAIN_HUNTER", "BUDGET_STRICT"] = "BARGAIN_HUNTER"
    budget_paise: int
    persona_notes: str | None = "Looking for best value, demands high quality."


class ParsedIntent(BaseModel):
    raw_query: str
    category: str | None = None
    max_budget_paise: int | None = None
    required_tags: list[str] = Field(default_factory=list)
    buyer_persona: Literal["EAGER", "BARGAIN_HUNTER", "BUDGET_STRICT"] = "BARGAIN_HUNTER"
    target_product_name: str | None = None
    reasoning: str = ""
    reasoning_source: str = "LLM"


class ChatSessionRequest(BaseModel):
    query: str
    buyer_strategy: Literal["EAGER", "BARGAIN_HUNTER", "BUDGET_STRICT"] | None = None
    budget_paise: int | None = None


class DirectNegotiateRequest(BaseModel):
    product_id: str
    buyer_strategy: Literal["EAGER", "BARGAIN_HUNTER", "BUDGET_STRICT"] = "BARGAIN_HUNTER"
    buyer_budget_paise: int | None = None  # defaults to product price + 10%
    merchant_id: str | None = None


class NegotiationSessionOut(BaseModel):
    session_id: str
    product: ProductOut
    buyer: BuyerConfig
    messages: list[NegotiationMessage]
    outcome: Literal["ACCEPTED", "REJECTED", "GUARD_BLOCKED"]
    agreed_price_paise: int | None = None
    discount_achieved_pct: float | None = None
    bundle_included: BundleItem | None = None
    total_rounds: int
    order_id: str | None = None
    razorpay_order_id: str | None = None
    duration_ms: int
    created_at: datetime
