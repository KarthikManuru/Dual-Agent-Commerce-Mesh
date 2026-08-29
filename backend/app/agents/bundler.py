from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.product import Product
from app.models.policy import Policy
from app.schemas.negotiation import BundleItem
from app.agents.financial_guard import financial_guard


# Category complementarity mapping for intelligent upselling
COMPLEMENTARY_CATEGORIES = {
    "headphones": ["chargers", "speakers"],
    "speakers": ["chargers", "headphones"],
    "keyboards": ["mice", "chargers"],
    "mice": ["keyboards", "chargers"],
    "chargers": ["headphones", "mice"],
}


class BundlerEngine:
    """
    Autonomous cross-sell and bundle discovery engine.
    Finds compatible add-on accessories within the buyer's leftover budget,
    calculating a compliant bundle discount.
    """

    async def suggest_bundle(
        self,
        db: AsyncSession,
        main_product: Product,
        policy: Policy,
        remaining_budget_paise: int,
        preferred_discount_pct: float = 12.0,
    ) -> Optional[BundleItem]:
        """
        Suggests a bundle add-on product that fits the remaining budget and passes guard.
        """
        if remaining_budget_paise <= 0:
            return None

        # Look for complementary products
        target_categories = COMPLEMENTARY_CATEGORIES.get(main_product.category or "", ["chargers", "mice"])

        stmt = (
            select(Product)
            .options(joinedload(Product.inventory))
            .where(
                Product.id != main_product.id,
                Product.category.in_(target_categories),
                Product.is_active == True,
            )
        )
        res = await db.execute(stmt)
        candidates = res.unique().scalars().all()

        if not candidates:
            # Fallback: any other active product
            stmt_fb = (
                select(Product)
                .options(joinedload(Product.inventory))
                .where(Product.id != main_product.id, Product.is_active == True)
            )
            res_fb = await db.execute(stmt_fb)
            candidates = res_fb.unique().scalars().all()

        for candidate in candidates:
            if not candidate.inventory or candidate.inventory.available <= 0:
                continue

            # Calculate proposed bundle price with discount
            discount = min(preferred_discount_pct, float(policy.max_discount_pct))
            discount_paise = int(candidate.price_paise * (discount / 100.0))
            proposed_bundle_price = candidate.price_paise - discount_paise

            # Check if fits within remaining budget
            if proposed_bundle_price <= remaining_budget_paise:
                # Verify with FinancialActionGuard
                verdict = financial_guard.evaluate_offer(
                    product=candidate,
                    policy=policy,
                    offered_price_paise=proposed_bundle_price,
                    round_num=1,
                )

                if verdict.allowed:
                    return BundleItem(
                        product_id=str(candidate.id),
                        name=candidate.name,
                        category=candidate.category or "accessory",
                        original_price_paise=candidate.price_paise,
                        bundled_price_paise=proposed_bundle_price,
                        discount_pct=verdict.effective_discount_pct,
                    )

        return None


bundler = BundlerEngine()
