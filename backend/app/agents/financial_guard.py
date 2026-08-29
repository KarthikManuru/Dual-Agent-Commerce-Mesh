from decimal import Decimal
from typing import NamedTuple
from pydantic import BaseModel

from app.models.policy import Policy
from app.models.product import Product


class GuardVerdict(BaseModel):
    allowed: bool
    result: str  # "ALLOW" | "DENY"
    reason_codes: list[str]
    effective_discount_pct: float
    effective_margin_pct: float
    detail: dict


class FinancialActionGuard:
    """
    100% Deterministic Financial Rule Guard.
    Enforces merchant business policies and financial safety guardrails mathematically.
    Zero LLM hallucination risk — executes exact constraint checks.
    """

    @staticmethod
    def evaluate_offer(
        product: Product,
        policy: Policy,
        offered_price_paise: int,
        round_num: int = 1,
    ) -> GuardVerdict:
        """
        Validates proposed price against product cost and merchant policy.
        """
        reason_codes = []
        violations = []

        original_price = product.price_paise
        cost_price = product.cost_paise

        # 1. Calculate discount percentage
        if original_price > 0:
            discount_paise = max(0, original_price - offered_price_paise)
            discount_pct = round((discount_paise / original_price) * 100, 2)
        else:
            discount_pct = 0.0

        # 2. Calculate profit margin percentage
        if offered_price_paise > 0:
            profit_paise = offered_price_paise - cost_price
            margin_pct = round((profit_paise / offered_price_paise) * 100, 2)
        else:
            profit_paise = -cost_price
            margin_pct = -100.0

        # Policy thresholds
        max_discount = float(policy.max_discount_pct)
        min_margin = float(policy.min_margin_pct)
        max_order_val = policy.max_order_value_paise
        max_rounds = policy.max_negotiation_rounds

        # Check 1: Max Discount Violation
        if discount_pct > max_discount:
            violations.append(f"Discount {discount_pct}% exceeds max allowed {max_discount}%")
            reason_codes.append("EXCEEDS_MAX_DISCOUNT")
        else:
            reason_codes.append("DISCOUNT_COMPLIANT")

        # Check 2: Minimum Margin Violation
        if margin_pct < min_margin:
            violations.append(f"Margin {margin_pct}% is below minimum required {min_margin}%")
            reason_codes.append("MARGIN_BELOW_MINIMUM")
        else:
            reason_codes.append("MARGIN_COMPLIANT")

        # Check 3: Below Cost Price Violation
        if offered_price_paise < cost_price:
            violations.append(f"Price ₹{offered_price_paise/100:.2f} is below unit cost ₹{cost_price/100:.2f}")
            reason_codes.append("BELOW_COST_PRICE")

        # Check 4: Max Order Value
        if offered_price_paise > max_order_val:
            violations.append(f"Order total ₹{offered_price_paise/100:.2f} exceeds policy ceiling ₹{max_order_val/100:.2f}")
            reason_codes.append("EXCEEDS_MAX_ORDER_VALUE")

        # Check 5: Max Negotiation Rounds
        if round_num > max_rounds:
            violations.append(f"Round {round_num} exceeds max allowed negotiation rounds ({max_rounds})")
            reason_codes.append("MAX_ROUNDS_EXCEEDED")

        is_allowed = len(violations) == 0

        detail = {
            "offered_price_paise": offered_price_paise,
            "original_price_paise": original_price,
            "cost_paise": cost_price,
            "effective_discount_pct": discount_pct,
            "effective_margin_pct": margin_pct,
            "policy_max_discount_pct": max_discount,
            "policy_min_margin_pct": min_margin,
            "violations": violations,
            "guard_type": "DETERMINISTIC_MATHEMATICAL",
        }

        return GuardVerdict(
            allowed=is_allowed,
            result="ALLOW" if is_allowed else "DENY",
            reason_codes=reason_codes,
            effective_discount_pct=discount_pct,
            effective_margin_pct=margin_pct,
            detail=detail,
        )


financial_guard = FinancialActionGuard()
