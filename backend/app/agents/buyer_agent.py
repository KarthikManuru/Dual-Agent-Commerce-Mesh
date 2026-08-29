from typing import List, Optional
from datetime import datetime

from app.models.product import Product
from app.schemas.negotiation import NegotiationMessage, BuyerConfig
from app.services.llm_client import llm_service


BUYER_SYSTEM_PROMPT = """
You are an autonomous AI Buyer Agent negotiating a commercial purchase on behalf of a human user.
You must act according to the assigned strategy:
- EAGER: Wants convenience, accepts if price is within budget or after a tiny counter.
- BARGAIN_HUNTER: Tenacious negotiator, seeks 8-15% discounts, cites competitor prices, quality alternatives, or volume.
- BUDGET_STRICT: Cannot exceed the budget ceiling by even 1 rupee; aggressively demands price reductions.

Respond strictly in valid JSON format with the following keys:
{
  "intent": "ACCEPT" | "COUNTER" | "REJECT",
  "counter_price_paise": integer (in paise, ₹1 = 100 paise),
  "reasoning_text": "1-2 sentences of professional, persuasive negotiation text spoken to the merchant",
  "reason_codes": ["BUDGET_COMPLIANT", "SEEKING_VOLUME_DISCOUNT", "MARKET_BENCHMARK", etc.]
}
"""


def _buyer_heuristic(
    product: Product,
    buyer_config: BuyerConfig,
    current_offer_paise: int,
    round_num: int,
) -> dict:
    """Heuristic fallback for buyer negotiation."""
    budget = buyer_config.budget_paise
    strategy = buyer_config.strategy

    if current_offer_paise <= budget:
        if strategy == "EAGER" or round_num >= 2:
            return {
                "intent": "ACCEPT",
                "counter_price_paise": current_offer_paise,
                "reasoning_text": f"Offer of ₹{current_offer_paise/100:.2f} fits our parameters. We accept terms.",
                "reason_codes": ["WITHIN_BUDGET", "TERMS_ACCEPTED"],
            }
        elif strategy == "BARGAIN_HUNTER":
            # Counter with 8% further discount if round 1
            target_counter = max(int(current_offer_paise * 0.92), int(product.cost_paise * 1.12))
            return {
                "intent": "COUNTER",
                "counter_price_paise": target_counter,
                "reasoning_text": f"We are ready to close today if you can meet us at ₹{target_counter/100:.2f}.",
                "reason_codes": ["BARGAIN_STRATEGY_ROUND_1"],
            }
    else:
        # Over budget
        if strategy == "BUDGET_STRICT":
            if budget < product.cost_paise:
                return {
                    "intent": "REJECT",
                    "counter_price_paise": 0,
                    "reasoning_text": f"Our budget ceiling of ₹{budget/100:.2f} cannot accommodate this pricing.",
                    "reason_codes": ["BUDGET_CEILING_EXCEEDED"],
                }
            return {
                "intent": "COUNTER",
                "counter_price_paise": budget,
                "reasoning_text": f"Our hard budget limit is ₹{budget/100:.2f}. If you can match this, we will execute immediately.",
                "reason_codes": ["STRICT_BUDGET_COUNTER"],
            }

    # Default counter
    target_counter = max(int(current_offer_paise * 0.90), product.cost_paise)
    return {
        "intent": "COUNTER",
        "counter_price_paise": target_counter,
        "reasoning_text": f"We counter at ₹{target_counter/100:.2f} based on current market benchmarks.",
        "reason_codes": ["STANDARD_COUNTER"],
    }


class BuyerAgent:
    """
    Autonomous Buyer Agent powered by real LLM with structured negotiation protocol.
    """

    async def evaluate_and_respond(
        self,
        product: Product,
        buyer_config: BuyerConfig,
        current_offer_paise: int,
        round_num: int,
        conversation_history: List[NegotiationMessage],
    ) -> NegotiationMessage:
        """
        Evaluates merchant offer via LLM and generates response message.
        """
        prompt = f"""
Negotiation Context:
- Product: {product.name} (Category: {product.category})
- Original Catalog Price: ₹{product.price_paise / 100:.2f} ({product.price_paise} paise)
- Current Merchant Offer: ₹{current_offer_paise / 100:.2f} ({current_offer_paise} paise)
- Buyer Persona & Strategy: {buyer_config.strategy}
- Buyer Budget: ₹{buyer_config.budget_paise / 100:.2f} ({buyer_config.budget_paise} paise)
- Current Round: {round_num} of 2
- Negotiation History:
{[f"Round {m.round} - {m.sender}: {m.intent} ₹{m.offered_price_paise/100:.2f} - '{m.reasoning_text}'" for m in conversation_history]}

Instructions:
Evaluate the offer. If within strategy and budget, ACCEPT. If you want a better deal, COUNTER with a specific price. If completely unviable, REJECT.
Respond in JSON.
"""
        llm_res = await llm_service.generate_structured(
            prompt=prompt,
            system_prompt=BUYER_SYSTEM_PROMPT,
            fallback_fn=lambda: _buyer_heuristic(product, buyer_config, current_offer_paise, round_num),
        )

        data = llm_res.data
        intent = data.get("intent", "COUNTER")
        counter_price = int(data.get("counter_price_paise", current_offer_paise))
        reasoning_text = data.get("reasoning_text", "Counter offer submitted.")
        reason_codes = data.get("reason_codes") or ["LLM_DECISION"]

        # Calculate discount from original price
        discount_pct = 0.0
        if product.price_paise > 0 and counter_price < product.price_paise:
            discount_pct = round(((product.price_paise - counter_price) / product.price_paise) * 100, 2)

        return NegotiationMessage(
            sender="BUYER_AGENT",
            intent=intent,
            offered_price_paise=counter_price,
            discount_pct=discount_pct,
            reasoning_text=reasoning_text,
            reason_codes=reason_codes,
            round=round_num,
            reasoning_source=llm_res.reasoning_source,
            model_name=llm_res.model_name,
            latency_ms=llm_res.latency_ms,
            timestamp=datetime.utcnow(),
        )


buyer_agent = BuyerAgent()
