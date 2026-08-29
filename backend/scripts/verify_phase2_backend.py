"""
Phase 2 Backend Verification Script:
1. Tests POST /orders (creates real Razorpay Test Order via Razorpay API).
2. Tests POST /webhooks/razorpay with valid HMAC-SHA256 signature -> verifies state machine advance & audit events.
3. Tests POST /webhooks/razorpay duplicate event -> verifies idempotency (200 with ignored_duplicate).
4. Tests POST /webhooks/razorpay invalid signature -> verifies 400 Bad Request rejection.
"""

import sys
import os
import json
import time
import hmac
import hashlib
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings

BASE_URL = "http://127.0.0.1:8000"
settings = get_settings()


def generate_webhook_signature(body_bytes: bytes, secret: str) -> str:
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=body_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()


def test_phase2_backend():
    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    print("==================================================")
    print("PHASE 2 BACKEND VERIFICATION -- REAL RAZORPAY TEST")
    print("==================================================")

    # 1. Fetch products to get merchant_id and product_id
    r = client.get("/products")
    assert r.status_code == 200, f"Fetch products failed: {r.text}"
    products = r.json()["products"]
    assert len(products) > 0, "No products found."
    test_product = products[0]
    product_id = test_product["id"]

    # Get merchant ID
    from scripts.seed import MERCHANT_ID
    merchant_id = str(MERCHANT_ID)

    print(f"\n1. Creating order for product: {test_product['name']} (Price: {test_product['price_display'].replace('₹', 'INR ')}) ...")
    order_payload = {
        "product_id": product_id,
        "merchant_id": merchant_id,
        "quantity": 1,
    }
    r = client.post("/orders", json=order_payload)
    if r.status_code != 200:
        print(f"[FAIL] Order creation failed ({r.status_code}): {r.text}")
        sys.exit(1)

    order_resp = r.json()
    order_id = order_resp["order"]["id"]
    rzp_order_id = order_resp["razorpay_order_id"]
    print(f"  [PASS] Order created successfully in DB: {order_id}")
    print(f"  [PASS] Real Razorpay Test Order ID: {rzp_order_id}")
    print(f"  [PASS] Status: {order_resp['order']['status']}")

    assert rzp_order_id.startswith("order_"), f"Invalid Razorpay Order ID: {rzp_order_id}"

    # 2. Test Webhook with Invalid Signature (Should reject with 400)
    print("\n2. Testing Webhook Security: Invalid Signature Rejection ...")
    fake_payload = {
        "entity": "event",
        "account_id": "acc_test",
        "event": "payment.captured",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_test_{int(time.time())}",
                    "order_id": rzp_order_id,
                    "amount": test_product["price_paise"],
                    "status": "captured",
                    "method": "card",
                }
            }
        },
        "created_at": int(time.time()),
    }
    fake_body = json.dumps(fake_payload).encode("utf-8")
    r = client.post(
        "/webhooks/razorpay",
        content=fake_body,
        headers={"X-Razorpay-Signature": "invalid_tampered_signature_12345"},
    )
    assert r.status_code == 400, f"Expected 400 for bad signature, got {r.status_code}: {r.text}"
    print(f"  [PASS] Webhook with forged signature was rejected (HTTP 400): {r.json()}")

    # 3. Test Webhook with Valid Signature (Real HMAC)
    print("\n3. Testing Webhook Processing: Valid Signature & State Progression ...")
    event_id = f"evt_test_{int(time.time())}"
    webhook_payload = {
        "entity": "event",
        "account_id": "acc_test",
        "event": "payment.captured",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_test_{int(time.time())}",
                    "order_id": rzp_order_id,
                    "amount": test_product["price_paise"],
                    "status": "captured",
                    "method": "upi",
                }
            }
        },
        "created_at": int(time.time()),
    }
    body_bytes = json.dumps(webhook_payload).encode("utf-8")
    valid_sig = generate_webhook_signature(body_bytes, settings.RAZORPAY_WEBHOOK_SECRET)

    r = client.post(
        "/webhooks/razorpay",
        content=body_bytes,
        headers={"X-Razorpay-Signature": valid_sig},
    )
    assert r.status_code == 200, f"Webhook failed: {r.text}"
    print(f"  [PASS] Webhook accepted (HTTP 200): {r.json()}")

    # 4. Test Idempotency (Sending same event again)
    print("\n4. Testing Webhook Idempotency: Duplicate Event Handling ...")
    r_dup = client.post(
        "/webhooks/razorpay",
        content=body_bytes,
        headers={"X-Razorpay-Signature": valid_sig},
    )
    assert r_dup.status_code == 200, f"Duplicate webhook failed: {r_dup.text}"
    dup_resp = r_dup.json()
    assert dup_resp.get("status") == "ignored_duplicate", f"Expected ignored_duplicate, got {dup_resp}"
    print(f"  [PASS] Duplicate webhook gracefully ignored (HTTP 200): {dup_resp}")

    # Give background worker a brief moment to process
    time.sleep(1.5)

    # 5. Verify Order status in Database and Audit Events
    print("\n5. Verifying Order State Machine & Audit Trail ...")
    r_order = client.get(f"/orders/{order_id}")
    assert r_order.status_code == 200, f"Get order failed: {r_order.text}"
    order_data = r_order.json()
    print(f"  [PASS] Current Order Status: {order_data['status']}")
    print(f"  [PASS] Razorpay Payment ID: {order_data.get('razorpay_payment_id')}")
    print(f"  [PASS] Audit Events Logged ({len(order_data['events'])} events):")
    for ev in order_data["events"]:
        print(f"    - [{ev['actor']}] {ev['action']}: {ev['from_status']} -> {ev['to_status']} ({ev['result']})")

    # 6. Test Race Condition: Second webhook arriving AFTER order is already FULFILLED
    # This simulates the real-world race where /verify finishes first and the webhook arrives later,
    # or two webhook events arrive for the same payment. The second should no-op gracefully.
    print("\n6. Testing Race Condition: Webhook on already-FULFILLED order ...")
    race_event_id = f"evt_race_{int(time.time())}"  # NEW event_id → bypasses event_id dedup
    race_payload = {
        "entity": "event",
        "account_id": "acc_test",
        "event": "payment.captured",
        "event_id": race_event_id,
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_race_{int(time.time())}",
                    "order_id": rzp_order_id,
                    "amount": test_product["price_paise"],
                    "status": "captured",
                    "method": "card",
                }
            }
        },
        "created_at": int(time.time()),
    }
    race_body = json.dumps(race_payload).encode("utf-8")
    race_sig = generate_webhook_signature(race_body, settings.RAZORPAY_WEBHOOK_SECRET)

    r_race = client.post(
        "/webhooks/razorpay",
        content=race_body,
        headers={"X-Razorpay-Signature": race_sig},
    )
    assert r_race.status_code == 200, f"Race webhook failed (should be 200): {r_race.text}"
    race_resp = r_race.json()
    print(f"  [PASS] Second webhook accepted without crash (HTTP 200): {race_resp}")

    # Wait for the worker to process
    time.sleep(1.5)

    # Verify the order is STILL FULFILLED (not corrupted)
    r_final = client.get(f"/orders/{order_id}")
    assert r_final.status_code == 200
    final_data = r_final.json()
    assert final_data["status"] == "FULFILLED", f"Expected FULFILLED after race, got {final_data['status']}"
    print(f"  [PASS] Order remains FULFILLED after race condition (idempotent-by-status)")

    # Verify INFO audit events were logged (not DENY/crash)
    info_events = [e for e in final_data["events"] if e["result"] == "INFO"]
    assert len(info_events) > 0, "Expected at least one INFO audit event from the race condition handling"
    print(f"  [PASS] INFO audit events logged: {len(info_events)} events (graceful no-op, no crash)")
    for ev in info_events:
        print(f"    - [{ev['actor']}] {ev['action']}: {ev.get('detail', {}).get('note', '')}")

    print("\n[ALL PHASE 2 BACKEND TESTS PASSED — INCLUDING RACE CONDITION FIX]")


if __name__ == "__main__":
    test_phase2_backend()

