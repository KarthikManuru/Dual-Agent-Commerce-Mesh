"""
Live Failure Handling & Concurrency Demo Script:
1. Concurrent Inventory Race Test: 2 simultaneous requests compete for 1 unit of stock -> exactly 1 succeeds, 1 gets clean 400.
2. Price Tampering Prevention: Client cannot alter unit_price or total_price at checkout -> server enforces DB pricing.
3. Webhook Replay / Duplicate Idempotency: Re-sending identical webhook payload -> 200 OK with 'ignored_duplicate', zero duplicate events.
4. Illegal State Machine Transition: Attempting illegal status jump -> strictly blocked by StateMachine with IllegalTransitionError.
5. Deterministic Guard Bounds Violation: Excessive 25% discount -> mathematically blocked with EXCEEDS_MAX_DISCOUNT audit log.
"""

import sys
import asyncio
import uuid
import os
import httpx
import logging
from decimal import Decimal
import hmac
import hashlib

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.policy import Policy
from app.models.enums import OrderStatus, validate_transition, IllegalTransitionError
from app.agents.financial_guard import financial_guard
from scripts.seed import MERCHANT_ID

BASE_URL = "http://127.0.0.1:8000"
settings = get_settings()


def generate_webhook_signature(body_bytes: bytes, secret: str) -> str:
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=body_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()


async def run_failure_handling_demo():
    client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)

    print("==================================================================")
    print("LIVE DEMO: CONCURRENCY RACE & GRACEFUL FAILURE RECOVERY SUITE")
    print("==================================================================")

    # -----------------------------------------------------------------
    # DEMO 1: Concurrent Inventory Race (2 buyers, 1 unit of stock)
    # -----------------------------------------------------------------
    print("\n[DEMO 1] Testing Concurrent Inventory Race (2 Buyers competing for 1 Unit of Stock) ...")
    
    # 1. Create a limited-edition flash item with total_stock=1
    async with AsyncSessionLocal() as db:
        prod_id = uuid.uuid4()
        test_item = Product(
            id=prod_id,
            name="Limited Edition Master Headphones (Only 1 in Stock)",
            description="Ultra rare collectors unit",
            category="headphones",
            price_paise=499900,
            cost_paise=300000,
            currency="INR",
            is_active=True,
        )
        test_inv = Inventory(
            id=uuid.uuid4(),
            product_id=prod_id,
            total_stock=1,
            reserved=0,
        )
        db.add(test_item)
        db.add(test_inv)
        await db.commit()

    print(f"  -> Created product with EXACTLY 1 unit of stock (ID: {prod_id})")

    # 2. Fire 2 simultaneous purchase requests at the exact same millisecond
    async def attempt_purchase(buyer_label: str):
        payload = {
            "merchant_id": str(MERCHANT_ID),
            "product_id": str(prod_id),
            "quantity": 1,
        }
        resp = await client.post("/orders", json=payload)
        return buyer_label, resp.status_code, resp.json()

    print("  -> Firing 2 simultaneous purchase requests concurrently via asyncio.gather ...")
    results = await asyncio.gather(
        attempt_purchase("Buyer A (Thread 1)"),
        attempt_purchase("Buyer B (Thread 2)"),
    )

    success_count = 0
    blocked_count = 0

    for buyer, status, body in results:
        if status == 200:
            success_count += 1
            print(f"  [SUCCESS] {buyer}: Won the race! Order ID: {body['order']['id']} (Status: {body['order']['status']})")
        else:
            blocked_count += 1
            print(f"  [GRACEFUL REJECTION] {buyer}: HTTP {status} -> {body.get('detail')}")

    assert success_count == 1, f"Expected exactly 1 winner, got {success_count}"
    assert blocked_count == 1, f"Expected exactly 1 rejection, got {blocked_count}"
    print("  [PASS] Zero double-allocation. Concurrency race safely handled by atomic inventory checks.")

    # -----------------------------------------------------------------
    # DEMO 2: Price / Concession Tamper Protection
    # -----------------------------------------------------------------
    print("\n[DEMO 2] Testing Price Tamper Protection (Client cannot forge checkout amount) ...")
    # Create another product with stock
    async with AsyncSessionLocal() as db:
        tamper_prod_id = uuid.uuid4()
        t_prod = Product(
            id=tamper_prod_id,
            name="Security Test Item",
            description="Testing price tamper resistance",
            category="accessories",
            price_paise=999900,  # ₹9,999.00
            cost_paise=500000,
            currency="INR",
            is_active=True,
        )
        t_inv = Inventory(id=uuid.uuid4(), product_id=tamper_prod_id, total_stock=5, reserved=0)
        db.add(t_prod)
        db.add(t_inv)
        await db.commit()

    tampered_payload = {
        "merchant_id": str(MERCHANT_ID),
        "product_id": str(tamper_prod_id),
        "quantity": 1,
        "unit_price_paise": 100,  # Attacker tries to set ₹1.00 instead of ₹9,999.00
        "total_paise": 100,
    }

    r_tamper = await client.post("/orders", json=tampered_payload)
    # The server strictly recalculates from database (price_paise=999900)
    tamper_order = r_tamper.json()["order"]
    print(f"  Attacker submitted: unit_price_paise=100 (₹1.00)")
    print(f"  Server locked price: total_paise={tamper_order['total_paise']} (₹{tamper_order['total_paise']/100:.2f})")
    assert tamper_order["total_paise"] == 999900, "Server allowed client price tampering!"
    print("  [PASS] Client price tampering strictly ignored. Server-enforced catalog truth.")

    # -----------------------------------------------------------------
    # DEMO 3: Duplicate Webhook Replay Idempotency
    # -----------------------------------------------------------------
    print("\n[DEMO 3] Testing Webhook Replay & Duplicate Event Idempotency ...")
    order_id = tamper_order["id"]
    fake_payment_id = f"pay_test_{uuid.uuid4().hex[:8]}"

    webhook_payload = {
        "entity": "event",
        "account_id": "acc_mesh_demo",
        "event": "payment.captured",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": fake_payment_id,
                    "order_id": tamper_order["razorpay_order_id"],
                    "status": "captured",
                    "amount": tamper_order["total_paise"],
                    "currency": "INR",
                }
            }
        },
        "created_at": 1700000000,
    }
    import json
    body_bytes = json.dumps(webhook_payload).encode("utf-8")
    sig = generate_webhook_signature(body_bytes, settings.RAZORPAY_WEBHOOK_SECRET)
    headers = {
        "X-Razorpay-Signature": sig,
        "Content-Type": "application/json",
    }

    # First Webhook Delivery
    r_wh1 = await client.post("/webhooks/razorpay", content=body_bytes, headers=headers)
    print(f"  Webhook Delivery 1: HTTP {r_wh1.status_code} -> {r_wh1.json()}")
    assert r_wh1.status_code == 200

    # Duplicate Webhook Replay (Simulating network retry from gateway)
    r_wh2 = await client.post("/webhooks/razorpay", content=body_bytes, headers=headers)
    print(f"  Webhook Delivery 2 (Duplicate Replay): HTTP {r_wh2.status_code} -> {r_wh2.json()}")
    assert r_wh2.status_code == 200
    assert r_wh2.json().get("status") == "ignored_duplicate"
    print("  [PASS] Duplicate webhook safely deduplicated with status='ignored_duplicate'. No double-transitions.")

    # -----------------------------------------------------------------
    # DEMO 4: Illegal State Machine Transition Jump Rejection
    # -----------------------------------------------------------------
    print("\n[DEMO 4] Testing Illegal State Machine Jump (DISCOVERED -> FULFILLED) ...")
    try:
        validate_transition(OrderStatus.DISCOVERED, OrderStatus.FULFILLED)
        print("  [FAIL] Illegal transition was allowed!")
        sys.exit(1)
    except IllegalTransitionError as e:
        print(f"  [PASS] Illegal transition strictly blocked: {e}")

    # -----------------------------------------------------------------
    # DEMO 5: Deterministic FinancialActionGuard Violation
    # -----------------------------------------------------------------
    print("\n[DEMO 5] Testing FinancialActionGuard Policy Violation (Excessive 25% Concession) ...")
    dummy_policy = Policy(
        merchant_id=MERCHANT_ID,
        max_discount_pct=Decimal("15.00"),
        min_margin_pct=Decimal("10.00"),
        max_negotiation_rounds=2,
        max_order_value_paise=5_000_000,
        offer_ttl_seconds=600,
    )
    v_fail = financial_guard.evaluate_offer(t_prod, dummy_policy, offered_price_paise=749925, round_num=1)
    assert v_fail.allowed is False
    print(f"  [PASS] FinancialGuard Verdict: {v_fail.result} | Violations: {v_fail.detail['violations']}")

    # -----------------------------------------------------------------
    # DEMO 6: Expired Offer TTL Rejection at Checkout
    # -----------------------------------------------------------------
    print("\n[DEMO 6] Testing Expired Offer TTL Rejection at Checkout ...")
    from datetime import datetime, timezone, timedelta
    from app.models.offer import Offer

    expired_offer_id = uuid.uuid4()
    exp_product_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        exp_prod = Product(
            id=exp_product_id,
            name="TTL Expiration Test Earbuds",
            description="Testing time-to-live expiration barrier",
            category="earbuds",
            price_paise=399900,
            cost_paise=200000,
            currency="INR",
            is_active=True,
            tags=[],
        )
        session.add(exp_prod)
        session.add(Inventory(product_id=exp_product_id, total_stock=10, reserved=0))
        await session.flush()

        # Create an offer with expires_at backdated in the past (e.g. 5 minutes ago)
        expired_offer = Offer(
            id=expired_offer_id,
            product_id=exp_product_id,
            merchant_id=MERCHANT_ID,
            original_price_paise=399900,
            offered_price_paise=349900,
            discount_pct=Decimal("12.50"),
            negotiation_round=1,
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=300),
            is_accepted=False,
            is_expired=False,
        )
        session.add(expired_offer)
        await session.commit()

    # Attempt to checkout with the expired offer
    exp_checkout_resp = await client.post(
        "http://127.0.0.1:8000/orders",
        json={
            "product_id": str(exp_product_id),
            "merchant_id": str(MERCHANT_ID),
            "quantity": 1,
            "offer_id": str(expired_offer_id),
        },
    )

    print(f"  Expired Offer Checkout Response: HTTP {exp_checkout_resp.status_code} -> {exp_checkout_resp.json()}")
    assert exp_checkout_resp.status_code == 400, f"Expected 400 for expired offer, got {exp_checkout_resp.status_code}"
    assert "expired" in exp_checkout_resp.json()["detail"].lower()
    print("  [PASS] Stale offer successfully blocked at checkout: Offer TTL elapsed.")

    print("\n==================================================================")
    print("ALL 6 LIVE FAILURE-HANDLING & CONCURRENCY SCENARIOS PASSED!")
    print("==================================================================")

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(run_failure_handling_demo())
