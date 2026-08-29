"""
Seed script — populates the database with demo data:
- 1 merchant ("TechMesh Electronics")
- 1 policy (15% max discount, 10% min margin, 2 negotiation rounds)
- 10 products across categories with realistic prices, costs, tags, stock
"""

import asyncio
import uuid
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.merchant import Merchant
from app.models.policy import Policy
from app.models.product import Product
from app.models.inventory import Inventory
from decimal import Decimal


# Fixed UUIDs so seed is idempotent
MERCHANT_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

PRODUCTS = [
    {
        "name": "SonicPro ANC 3000",
        "description": "Premium active noise cancelling wireless headphones with 40hr battery, Hi-Res Audio, and adaptive transparency mode.",
        "category": "headphones",
        "price_paise": 499900,  # ₹4,999
        "cost_paise": 249900,   # ₹2,499
        "tags": ["ANC", "wireless", "bluetooth", "hi-res", "over-ear"],
        "image_url": None,
        "stock": 25,
    },
    {
        "name": "BassWave 200",
        "description": "Deep bass wireless earbuds with IPX5 water resistance and 8hr playback.",
        "category": "headphones",
        "price_paise": 179900,  # ₹1,799
        "cost_paise": 79900,    # ₹799
        "tags": ["wireless", "bluetooth", "earbuds", "bass", "waterproof"],
        "image_url": None,
        "stock": 50,
    },
    {
        "name": "ClearTalk Pro",
        "description": "ANC headphones optimized for video calls with dual-mic beamforming and USB-C dongle.",
        "category": "headphones",
        "price_paise": 299900,  # ₹2,999
        "cost_paise": 149900,   # ₹1,499
        "tags": ["ANC", "wireless", "bluetooth", "office", "microphone"],
        "image_url": None,
        "stock": 30,
    },
    {
        "name": "ThunderBoom 360",
        "description": "360° spatial audio portable speaker, 20W, waterproof (IP67), 16hr battery.",
        "category": "speakers",
        "price_paise": 349900,  # ₹3,499
        "cost_paise": 174900,   # ₹1,749
        "tags": ["bluetooth", "portable", "waterproof", "spatial-audio"],
        "image_url": None,
        "stock": 20,
    },
    {
        "name": "DeskBlast Mini",
        "description": "Compact desktop speaker with USB-C, 10W, fabric finish. Perfect desk companion.",
        "category": "speakers",
        "price_paise": 149900,  # ₹1,499
        "cost_paise": 69900,    # ₹699
        "tags": ["desktop", "usb-c", "compact", "wired"],
        "image_url": None,
        "stock": 40,
    },
    {
        "name": "MechStrike TKL",
        "description": "Tenkeyless mechanical keyboard, hot-swappable Gateron switches, per-key RGB, aluminum frame.",
        "category": "keyboards",
        "price_paise": 599900,  # ₹5,999
        "cost_paise": 299900,   # ₹2,999
        "tags": ["mechanical", "TKL", "RGB", "hot-swap", "gaming"],
        "image_url": None,
        "stock": 15,
    },
    {
        "name": "SilentType 75",
        "description": "75% low-profile keyboard with silent switches and Mac/Windows layout toggle.",
        "category": "keyboards",
        "price_paise": 449900,  # ₹4,499
        "cost_paise": 224900,   # ₹2,249
        "tags": ["low-profile", "silent", "wireless", "bluetooth", "office"],
        "image_url": None,
        "stock": 22,
    },
    {
        "name": "PrecisionGlide X1",
        "description": "Ergonomic wireless mouse, 26K DPI sensor, 90hr battery, USB-C fast charge.",
        "category": "mice",
        "price_paise": 399900,  # ₹3,999
        "cost_paise": 199900,   # ₹1,999
        "tags": ["wireless", "ergonomic", "gaming", "high-dpi"],
        "image_url": None,
        "stock": 35,
    },
    {
        "name": "TravelMouse Lite",
        "description": "Ultra-portable travel mouse, 65g, Bluetooth + USB-A dongle, silent clicks.",
        "category": "mice",
        "price_paise": 129900,  # ₹1,299
        "cost_paise": 54900,    # ₹549
        "tags": ["portable", "bluetooth", "silent", "travel", "lightweight"],
        "image_url": None,
        "stock": 60,
    },
    {
        "name": "HyperCharge 65W GaN",
        "description": "65W GaN USB-C charger with 3 ports (2x USB-C PD + 1x USB-A). Charges laptop + phone simultaneously.",
        "category": "chargers",
        "price_paise": 249900,  # ₹2,499
        "cost_paise": 99900,    # ₹999
        "tags": ["GaN", "USB-C", "PD", "fast-charge", "multi-port"],
        "image_url": None,
        "stock": 45,
    },
]


async def seed():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing = await session.execute(
            select(Merchant).where(Merchant.id == MERCHANT_ID)
        )
        if existing.scalar_one_or_none():
            print("[INFO] Database already seeded. Skipping.")
            return

        # Create merchant
        merchant = Merchant(
            id=MERCHANT_ID,
            name="TechMesh Electronics",
            is_active=True,
        )
        session.add(merchant)

        # Create policy for merchant
        policy = Policy(
            merchant_id=MERCHANT_ID,
            max_discount_pct=Decimal("15.00"),
            min_margin_pct=Decimal("10.00"),
            max_negotiation_rounds=2,
            max_order_value_paise=5_000_000,  # ₹50,000
            offer_ttl_seconds=600,
        )
        session.add(policy)

        # Create products and inventory
        for p_data in PRODUCTS:
            product = Product(
                name=p_data["name"],
                description=p_data["description"],
                category=p_data["category"],
                price_paise=p_data["price_paise"],
                cost_paise=p_data["cost_paise"],
                tags=p_data["tags"],
                image_url=p_data["image_url"],
                is_active=True,
            )
            session.add(product)
            await session.flush()  # Get the product ID

            inventory = Inventory(
                product_id=product.id,
                total_stock=p_data["stock"],
                reserved=0,
            )
            session.add(inventory)

        await session.commit()
        print("[SUCCESS] Seed complete:")
        print("   - 1 merchant: TechMesh Electronics")
        print("   - 1 policy: 15% max discount, 10% min margin, 2 rounds")
        print(f"   - {len(PRODUCTS)} products with inventory")


if __name__ == "__main__":
    asyncio.run(seed())
