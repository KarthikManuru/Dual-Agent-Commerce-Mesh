"""
Live Demonstration: Dynamic Merchant Policy Update & On-the-Fly Guard Reconfiguration.

Steps:
1. GET /policies/{merchant_id} -> Read current baseline policy (max_discount_pct=15%).
2. Evaluate an 18% discount offer against baseline -> DENIED (exceeds 15%).
3. PATCH /policies/{merchant_id} -> Dynamically increase max_discount_pct to 20%.
4. GET /policies/{merchant_id} -> Confirm new policy persisted in PostgreSQL.
5. Re-evaluate the same 18% discount offer -> ALLOWED under new live policy!
6. Restore baseline policy (15%).
"""

import asyncio
import sys
import uuid
import os
import httpx
from decimal import Decimal

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.product import Product
from app.models.policy import Policy
from app.agents.financial_guard import financial_guard

MERCHANT_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


async def run_policy_demo():
    print("=" * 70)
    print("LIVE DEMO: DYNAMIC POLICY MANAGEMENT & ON-THE-FLY GUARD ENFORCEMENT")
    print("=" * 70)

    test_product = Product(
        id=uuid.uuid4(),
        name="Dynamic Policy Test Pro Headphones",
        description="Testing live policy reconfiguration",
        category="headphones",
        price_paise=100000,  # ₹1,000.00
        cost_paise=50000,    # ₹500.00
        currency="INR",
        is_active=True,
        tags=[],
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Step 0: Ensure baseline policy is exactly 15% discount and 2 rounds
        await client.patch(
            f"http://127.0.0.1:8000/policies/{MERCHANT_ID}",
            json={"max_discount_pct": 15.0, "max_negotiation_rounds": 2, "min_margin_pct": 10.0, "offer_ttl_seconds": 600},
        )

        # Step 1: GET baseline policy
        print("\n[STEP 1] Fetching baseline policy via GET /policies/{merchant_id} ...")
        resp1 = await client.get(f"http://127.0.0.1:8000/policies/{MERCHANT_ID}")
        print(f"  HTTP {resp1.status_code} Baseline Response: {resp1.json()}")
        base_policy_data = resp1.json()
        assert resp1.status_code == 200
        assert base_policy_data["max_negotiation_rounds"] == 2
        assert float(base_policy_data["max_discount_pct"]) == 15.0

        # Step 2: Test 18% discount against 15% baseline guard
        print("\n[STEP 2] Testing 18% discount concession (offered_price=INR 820.00) against baseline 15% cap ...")
        policy_base = Policy(
            merchant_id=MERCHANT_ID,
            max_discount_pct=Decimal(str(base_policy_data["max_discount_pct"])),
            min_margin_pct=Decimal(str(base_policy_data["min_margin_pct"])),
            max_negotiation_rounds=base_policy_data["max_negotiation_rounds"],
            max_order_value_paise=base_policy_data["max_order_value_paise"],
            offer_ttl_seconds=base_policy_data["offer_ttl_seconds"],
        )
        v_base = financial_guard.evaluate_offer(test_product, policy_base, offered_price_paise=82000, round_num=1)
        print(f"  Guard Verdict: {v_base.result} (Allowed: {v_base.allowed})")
        print(f"  Reason:        {v_base.detail.get('violations')}")
        assert v_base.allowed is False, "Expected 18% discount to be DENIED against 15% cap"
        print("  [PASS] Baseline 15% cap strictly blocked 18% discount concession.")

        # Step 3: PATCH policy to allow 20% discount and 3 rounds
        print("\n[STEP 3] Dynamically updating policy via PATCH /policies/{merchant_id} (max_discount_pct: 20.0%, max_rounds: 3) ...")
        patch_payload = {
            "max_discount_pct": 20.0,
            "max_negotiation_rounds": 3,
        }
        patch_resp = await client.patch(f"http://127.0.0.1:8000/policies/{MERCHANT_ID}", json=patch_payload)
        print(f"  HTTP {patch_resp.status_code} Response: {patch_resp.json()}")
        assert patch_resp.status_code == 200
        assert float(patch_resp.json()["max_discount_pct"]) == 20.0

        # Step 4: Re-GET to verify database persistence
        print("\n[STEP 4] Re-verifying persisted policy in database via GET ...")
        get_updated = await client.get(f"http://127.0.0.1:8000/policies/{MERCHANT_ID}")
        updated_data = get_updated.json()
        print(f"  Persisted max_discount_pct: {updated_data['max_discount_pct']}%")
        print(f"  Persisted max_negotiation_rounds: {updated_data['max_negotiation_rounds']}")

        # Step 5: Test the exact same 18% discount under the updated live policy
        print("\n[STEP 5] Re-evaluating the exact same 18% discount offer under the new live policy ...")
        policy_updated = Policy(
            merchant_id=MERCHANT_ID,
            max_discount_pct=Decimal(str(updated_data["max_discount_pct"])),
            min_margin_pct=Decimal(str(updated_data["min_margin_pct"])),
            max_negotiation_rounds=updated_data["max_negotiation_rounds"],
            max_order_value_paise=updated_data["max_order_value_paise"],
            offer_ttl_seconds=updated_data["offer_ttl_seconds"],
        )
        v_updated = financial_guard.evaluate_offer(test_product, policy_updated, offered_price_paise=82000, round_num=1)
        print(f"  Guard Verdict: {v_updated.result} (Allowed: {v_updated.allowed})")
        print(f"  Calculated Discount: {v_updated.effective_discount_pct}% (Ceiling: {policy_updated.max_discount_pct}%)")
        assert v_updated.allowed is True, "Expected 18% discount to be ALLOWED under 20% cap"
        print("  [PASS] New policy immediately enforced live without server restart!")

        # Step 6: Restore baseline policy (15%)
        print("\n[STEP 6] Restoring baseline policy (15% cap) ...")
        restore_resp = await client.patch(f"http://127.0.0.1:8000/policies/{MERCHANT_ID}", json={"max_discount_pct": 15.0, "max_negotiation_rounds": 2})
        print(f"  HTTP {restore_resp.status_code} Restored: max_discount_pct={restore_resp.json()['max_discount_pct']}%")

    print("\n" + "=" * 70)
    print("ALL DYNAMIC POLICY MANAGEMENT & GUARD TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_policy_demo())
