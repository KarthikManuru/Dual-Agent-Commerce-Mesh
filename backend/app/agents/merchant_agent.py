from typing import List, Optional
from datetime import datetime

from app.models.product import Product
from app.models.policy import Policy
from app.schemas.negotiation import NegotiationMessage, BundleItem
from app.services.llm_client import llm_service


MERCHANT_SYSTEM_PROMPT = """
You are an autonomous AI Merchant Agent negotiating sales on behalf of an online electronics retailer.
Your objective is to maximize revenue and closed deals while strictly protecting profit margins and merchant policy limits.

Policy Constraints:
- Max discount allowed: defined by policy
- Min margin required: defined by policy
- You must never sell at a loss or violate policy margins.

Respond strictly in valid JSON format with keys:
{
  "intent": "OFFER" | "COUNTER" | "ACCEPT" | "REJECT",
  "offered_price_paise": integer (in paise, ₹1 = 100 paise),
  "reasoning_text": "1-2 sentences of commercial justification spoken to the buyer explaining the value, quality, or pricing rationale",
  "reason_codes": ["MARGIN_PROTECTED", "VOLUME_CONCESSION", "MEET_IN_MIDDLE", "HOLD_FIRM", etc.]
}
"""


def _merchant_heuristic(
    product: Product,
    policy: Policy,
    buyer_counter_paise: int | None,
    round_num: int,
) -> dict:
    """Heuristic fallback for merchant negotiation."""
    orig_price = product.price_paise
    cost_price = product.cost_paise
    max_discount_pct = float(policy.max_discount_pct)
    max_discount_paise = int(orig_price * (max_discount_pct / 100.0))
    floor_price = max(orig_price - max_discount_paise, int(cost_price * 1.10))

    if buyer_counter_paise is None or round_num == 1:
        # Initial offer: 3% promotional discount to encourage deal
        init_price = max(int(orig_price * 0.97), floor_price)
        return {
            "intent": "OFFER",
            "offered_price_paise": init_price,
            "reasoning_text": f"Welcome! We are pleased to offer our premium {product.name} with an introductory discount at ₹{init_price/100:.2f}.",
            "reason_codes": ["INTRODUCTORY_OFFER"],
        }

    # Evaluate buyer counter
    if buyer_counter_paise >= floor_price:
        if buyer_counter_paise >= int(orig_price * 0.95) or round_num >= 2:
            return {
                "intent": "ACCEPT",
                "offered_price_paise": buyer_counter_paise,
                "reasoning_text": f"We appreciate your business and accept your counter of ₹{buyer_counter_paise/100:.2f}.",
                "reason_codes": ["COUNTER_ACCEPTED_WITHIN_POLICY"],
            }
        else:
            # Meet halfway between floor and buyer
            mid_price = int((buyer_counter_paise + orig_price) / 2)
            mid_price = max(mid_price, floor_price)
            return {
                "intent": "COUNTER",
                "offered_price_paise": mid_price,
                "reasoning_text": f"We can meet you halfway at ₹{mid_price/100:.2f} with full warranty and priority shipping included.",
                "reason_codes": ["MEET_IN_MIDDLE"],
            }
    else:
        # Buyer counter is below our floor
        if round_num >= 2:
            return {
                "intent": "COUNTER",
                "offered_price_paise": floor_price,
                "reasoning_text": f"Our best and final price is ₹{floor_price/100:.2f}. We cannot discount below our production costs.",
                "reason_codes": ["BEST_AND_FINAL_FLOOR"],
            }
        return {
            "intent": "COUNTER",
            "offered_price_paise": floor_price,
            "reasoning_text": f"Your counter is below our policy margin. The lowest we can offer is ₹{floor_price/100:.2f}.",
            "reason_codes": ["POLICY_FLOOR_COUNTER"],
        }


class MerchantAgent:
    """
    Autonomous Merchant Agent powered by real LLM with commercial strategy deliberation.
    """

    async def generate_initial_offer(
        self,
        product: Product,
        policy: Policy,
    ) -> NegotiationMessage:
        """Generates opening offer for an order session."""
        prompt = f"""
Opening Offer Request:
- Product: {product.name} (Category: {product.category})
- Description: {product.description}
- List Price: ₹{product.price_paise / 100:.2f} ({product.price_paise} paise)
- Cost Price: ₹{product.cost_paise / 100:.2f} ({product.cost_paise} paise)
- Merchant Policy Max Discount: {policy.max_discount_pct}%
- Merchant Policy Min Margin: {policy.min_margin_pct}%

Instructions:
Create an attractive initial offer for the buyer (typically list price or a small 2-5% welcome discount).
Respond in JSON.
"""
        llm_res = await llm_service.generate_structured(
            prompt=prompt,
            system_prompt=MERCHANT_SYSTEM_PROMPT,
            fallback_fn=lambda: _merchant_heuristic(product, policy, None, 1),
        )

        data = llm_res.data
        offered_price = int(data.get("offered_price_paise", product.price_paise))
        reasoning_text = data.get("reasoning_text", f"Special introductory price for {product.name}.")
        reason_codes = data.get("reason_codes") or ["OPENING_OFFER"]

        discount_pct = 0.0
        if product.price_paise > 0 and offered_price < product.price_paise:
            discount_pct = round(((product.price_paise - offered_price) / product.price_paise) * 100, 2)

        return NegotiationMessage(
            sender="MERCHANT_AGENT",
            intent="OFFER",
            offered_price_paise=offered_price,
            discount_pct=discount_pct,
            reasoning_text=reasoning_text,
            reason_codes=reason_codes,
            round=1,
            reasoning_source=llm_res.reasoning_source,
            model_name=llm_res.model_name,
            latency_ms=llm_res.latency_ms,
            timestamp=datetime.utcnow(),
        )

    async def evaluate_and_respond(
        self,
        product: Product,
        policy: Policy,
        buyer_message: NegotiationMessage,
        round_num: int,
        conversation_history: List[NegotiationMessage],
        bundle_suggestion: Optional[BundleItem] = None,
    ) -> NegotiationMessage:
        """
        Evaluates buyer counter-offer via LLM and generates response.
        """
        buyer_counter_paise = buyer_message.offered_price_paise
        floor_price = int(product.price_paise * (1 - float(policy.max_discount_pct) / 100.0))

        bundle_context = ""
        if bundle_suggestion:
            bundle_context = f"\n- Optional Bundle Add-on Available: {bundle_suggestion.name} at ₹{bundle_suggestion.bundled_price_paise/100:.2f} ({bundle_suggestion.discount_pct}% off)"

        prompt = f"""
Negotiation Context:
- Product: {product.name}
- List Price: ₹{product.price_paise / 100:.2f}
- Unit Cost: ₹{product.cost_paise / 100:.2f}
- Hard Policy Discount Limit: {policy.max_discount_pct}% (Absolute floor price: ₹{floor_price / 100:.2f})
- Min Profit Margin Required: {policy.min_margin_pct}%
- Buyer Counter Offer: ₹{buyer_counter_paise / 100:.2f}
- Buyer Reasoning: "{buyer_message.reasoning_text}"
- Current Round: {round_num} of {policy.max_negotiation_rounds}
{bundle_context}

Negotiation History:
{[f"Round {m.round} - {m.sender}: {m.intent} ₹{m.offered_price_paise/100:.2f} - '{m.reasoning_text}'" for m in conversation_history]}

Instructions:
1. If buyer counter is >= floor price and fair, you may ACCEPT.
2. If buyer counter is below floor price, you MUST COUNTER at or above ₹{floor_price/100:.2f}.
3. If buyer counter is within policy, you may propose a compromise counter price.
4. Respond in JSON.
"""
        llm_res = await llm_service.generate_structured(
            prompt=prompt,
            system_prompt=MERCHANT_SYSTEM_PROMPT,
            fallback_fn=lambda: _merchant_heuristic(product, policy, buyer_counter_paise, round_num),
        )

        data = llm_res.data
        intent = data.get("intent", "COUNTER")
        offered_price = int(data.get("offered_price_paise", floor_price))
        reasoning_text = data.get("reasoning_text", "Counter offer submitted.")
        reason_codes = data.get("reason_codes") or ["LLM_DECISION"]

        discount_pct = 0.0
        if product.price_paise > 0 and offered_price < product.price_paise:
            discount_pct = round(((product.price_paise - offered_price) / product.price_paise) * 100, 2)

        return NegotiationMessage(
            sender="MERCHANT_AGENT",
            intent=intent,
            offered_price_paise=offered_price,
            discount_pct=discount_pct,
            reasoning_text=reasoning_text,
            reason_codes=reason_codes,
            bundle_suggestion=bundle_suggestion,
            round=round_num,
            reasoning_source=llm_res.reasoning_source,
            model_name=llm_res.model_name,
            latency_ms=llm_res.latency_ms,
            timestamp=datetime.utcnow(),
        )


merchant_agent = MerchantAgent()
