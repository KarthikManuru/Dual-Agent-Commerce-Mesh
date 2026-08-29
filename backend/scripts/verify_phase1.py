"""
Verification test for Phase 1 endpoints.
Tests:
- GET /health
- GET /products
- GET /products/{product_id}
- GET /orders
- State machine transition checks
"""

import httpx
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8000"


def test_endpoints():
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # 1. Health check
    print("Testing GET /health ...")
    r = client.get("/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    data = r.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"
    print(f"  [PASS] /health -> {data}")

    # 2. Products list
    print("\nTesting GET /products ...")
    r = client.get("/products")
    assert r.status_code == 200, f"List products failed: {r.text}"
    data = r.json()
    assert data["total"] == 10, f"Expected 10 products, got {data['total']}"
    assert len(data["products"]) == 10
    first_product = data["products"][0]
    print(f"  [PASS] /products -> {data['total']} products retrieved")
    print(f"  Sample product: {first_product['name']} | Price: {first_product['price_display'].replace('₹', 'INR ')} | Available stock: {first_product['inventory']['available']}")

    # 3. Product detail by ID
    product_id = first_product["id"]
    print(f"\nTesting GET /products/{product_id} ...")
    r = client.get(f"/products/{product_id}")
    assert r.status_code == 200, f"Get product failed: {r.text}"
    p_data = r.json()
    assert p_data["id"] == product_id
    assert p_data["name"] == first_product["name"]
    print(f"  [PASS] /products/{product_id} -> {p_data['name']} (Category: {p_data['category']})")

    # 4. Orders list
    print("\nTesting GET /orders ...")
    r = client.get("/orders")
    assert r.status_code == 200, f"List orders failed: {r.text}"
    orders_data = r.json()
    assert orders_data["total"] == 0
    print(f"  [PASS] /orders -> Total orders: {orders_data['total']} (empty initially)")

    # 5. Test state machine validation
    print("\nTesting Order State Machine logic ...")
    from app.models.enums import OrderStatus, validate_transition, IllegalTransitionError

    # Valid transition
    validate_transition(OrderStatus.DISCOVERED, OrderStatus.SELECTED)
    print("  [PASS] DISCOVERED -> SELECTED allowed")

    # Invalid transition
    try:
        validate_transition(OrderStatus.DISCOVERED, OrderStatus.ORDER_PAID)
        raise AssertionError("Should have raised IllegalTransitionError")
    except IllegalTransitionError as e:
        print(f"  [PASS] DISCOVERED -> ORDER_PAID correctly rejected: {e}")

    print("\n[ALL PHASE 1 TESTS PASSED]")


if __name__ == "__main__":
    test_endpoints()
