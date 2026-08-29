import re
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.product import Product
from app.schemas.negotiation import ParsedIntent
from app.services.llm_client import llm_service


SYSTEM_INTENT_PROMPT = """
You are an AI Commerce Discovery Agent in an autonomous commerce mesh.
Your task is to parse a buyer's free-text natural language query into a structured search contract.

Categories available in our catalog:
- headphones
- speakers
- keyboards
- mice
- chargers

Extract and return JSON with keys:
{
  "category": "headphones" | "speakers" | "keyboards" | "mice" | "chargers" | null,
  "max_budget_paise": integer (e.g. ₹3,000 = 300000 paise) or null,
  "required_tags": ["ANC", "wireless", "RGB", etc.],
  "buyer_persona": "EAGER" | "BARGAIN_HUNTER" | "BUDGET_STRICT",
  "target_product_name": string or null,
  "reasoning": "brief 1 sentence reasoning"
}
"""


def _heuristic_parse(query: str) -> dict:
    """Heuristic fallback for intent parsing."""
    q_lower = query.lower()
    
    # Category detection
    cat = None
    if any(w in q_lower for w in ["headphone", "earbud", "earphone", "audio", "anc"]):
        cat = "headphones"
    elif any(w in q_lower for w in ["speaker", "sound", "boom", "audio"]):
        cat = "speakers"
    elif any(w in q_lower for w in ["keyboard", "switch", "tkl", "type"]):
        cat = "keyboards"
    elif any(w in q_lower for w in ["mouse", "mice", "glide"]):
        cat = "mice"
    elif any(w in q_lower for w in ["charger", "gan", "adapter", "power", "pd"]):
        cat = "chargers"

    # Budget detection: "under 3000", "₹3,000", "< 5000", "budget 2500"
    budget_paise = None
    match = re.search(r"(?:under|below|less than|budget|within|₹|rs\.?)\s*(\d+[\d,]*)", q_lower)
    if match:
        num_str = match.group(1).replace(",", "")
        try:
            val_rupees = int(num_str)
            budget_paise = val_rupees * 100
        except ValueError:
            pass

    # Persona
    persona = "BARGAIN_HUNTER"
    if "urgent" in q_lower or "fast" in q_lower or "immediate" in q_lower:
        persona = "EAGER"
    elif "strict" in q_lower or "exact" in q_lower or "max" in q_lower:
        persona = "BUDGET_STRICT"

    tags = []
    for t in ["anc", "wireless", "bluetooth", "rgb", "fast-charge", "office", "gaming", "portable", "waterproof"]:
        if t in q_lower:
            tags.append(t)

    return {
        "category": cat,
        "max_budget_paise": budget_paise,
        "required_tags": tags,
        "buyer_persona": persona,
        "target_product_name": None,
        "reasoning": "Heuristically extracted category and constraints from user prompt.",
    }


async def parse_user_intent(query: str) -> tuple[ParsedIntent, str, str, int]:
    """
    Parses a user query into structured ParsedIntent.
    Returns (ParsedIntent, reasoning_source, model_name, latency_ms).
    """
    llm_res = await llm_service.generate_structured(
        prompt=f"User search query: \"{query}\"\nExtract search parameters in JSON format.",
        system_prompt=SYSTEM_INTENT_PROMPT,
        fallback_fn=lambda: _heuristic_parse(query),
    )

    data = llm_res.data
    parsed = ParsedIntent(
        raw_query=query,
        category=data.get("category"),
        max_budget_paise=data.get("max_budget_paise"),
        required_tags=data.get("required_tags") or [],
        buyer_persona=data.get("buyer_persona", "BARGAIN_HUNTER"),
        target_product_name=data.get("target_product_name"),
        reasoning=data.get("reasoning", ""),
        reasoning_source=llm_res.reasoning_source,
    )
    return parsed, llm_res.reasoning_source, llm_res.model_name, llm_res.latency_ms


async def discover_products(
    db: AsyncSession,
    intent: ParsedIntent,
    limit: int = 5,
) -> List[Product]:
    """
    Queries catalog matching parsed intent.
    Ranks by: category match -> budget match -> tag overlap.
    """
    stmt = select(Product).options(joinedload(Product.inventory)).where(Product.is_active == True)

    if intent.category:
        stmt = stmt.where(Product.category == intent.category)

    res = await db.execute(stmt)
    products = res.unique().scalars().all()

    if not products:
        # Fallback: all active products
        fallback_stmt = select(Product).options(joinedload(Product.inventory)).where(Product.is_active == True)
        res_fb = await db.execute(fallback_stmt)
        products = res_fb.unique().scalars().all()

    # Score and rank
    def score_product(p: Product) -> float:
        score = 0.0
        # Budget score
        if intent.max_budget_paise:
            if p.price_paise <= intent.max_budget_paise:
                score += 50.0
            else:
                score -= 100.0  # Over budget penalty

        # Tag overlap
        p_tags = set(p.tags or [])
        req_tags = set(t.lower() for t in intent.required_tags)
        for req in req_tags:
            if any(req in pt.lower() for pt in p_tags):
                score += 20.0

        # Stock availability bonus
        if p.inventory and p.inventory.available > 0:
            score += 10.0

        return score

    ranked = sorted(products, key=score_product, reverse=True)
    return list(ranked[:limit])
