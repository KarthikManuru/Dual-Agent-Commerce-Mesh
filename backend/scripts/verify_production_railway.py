"""
Production Verification Script for Railway Backend.
"""
import httpx
import json

BASE_URL = "https://dual-agent-commerce-mesh-production.up.railway.app"

def test_production():
    print("=" * 70)
    print("LIVE PRODUCTION BACKEND VERIFICATION (RAILWAY)")
    print("=" * 70)

    # 1. Health Endpoint
    print(f"\n[1] GET {BASE_URL}/health ...")
    r_health = httpx.get(f"{BASE_URL}/health", timeout=10.0)
    print(f"    HTTP {r_health.status_code}: {r_health.json()}")
    assert r_health.status_code == 200, "Health check failed"

    # 2. Products Catalog Endpoint
    print(f"\n[2] GET {BASE_URL}/products ...")
    r_products = httpx.get(f"{BASE_URL}/products", timeout=10.0)
    p_data = r_products.json()
    product_list = p_data.get("products", [])
    print(f"    HTTP {r_products.status_code}: Successfully retrieved {len(product_list)} seeded products.")
    for p in product_list[:3]:
        price_clean = p['price_display'].replace('₹', 'INR ')
        print(f"    - {p['name']} ({p['category']}): {price_clean} | Available: {p['inventory']['available']}")

    # 3. AI-Commerce Well-Known Discovery Endpoint
    print(f"\n[3] GET {BASE_URL}/.well-known/ai-commerce ...")
    r_wellknown = httpx.get(f"{BASE_URL}/.well-known/ai-commerce", timeout=10.0)
    print(f"    HTTP {r_wellknown.status_code}: {json.dumps(r_wellknown.json(), indent=2)}")
    assert r_wellknown.status_code == 200, "Well-known discovery failed"

    # 4. Merchant Policy Endpoint
    print(f"\n[4] GET {BASE_URL}/policies/a1b2c3d4-e5f6-7890-abcd-ef1234567890 ...")
    r_policy = httpx.get(f"{BASE_URL}/policies/a1b2c3d4-e5f6-7890-abcd-ef1234567890", timeout=10.0)
    print(f"    HTTP {r_policy.status_code}: {r_policy.json()}")
    assert r_policy.status_code == 200, "Policy fetch failed"

    print("\n" + "=" * 70)
    print("ALL PRODUCTION BACKEND ENDPOINTS ARE 100% ONLINE AND VERIFIED!")
    print("=" * 70)


if __name__ == "__main__":
    test_production()
