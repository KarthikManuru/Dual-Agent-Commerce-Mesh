from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.routers import health, products, orders, webhooks, ws, sessions, ai_agent_mesh, policies


from app.models import Base
import uuid
from decimal import Decimal
from sqlalchemy import select
from app.models.merchant import Merchant
from app.models.policy import Policy
from app.models.product import Product
from app.models.inventory import Inventory

MERCHANT_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

INITIAL_PRODUCTS = [
    {
        "name": "SonicPro ANC 3000",
        "description": "Premium active noise cancelling wireless headphones with 40hr battery, Hi-Res Audio, and adaptive transparency mode.",
        "category": "headphones",
        "price_paise": 499900,
        "cost_paise": 249900,
        "tags": ["ANC", "wireless", "bluetooth", "hi-res", "over-ear"],
        "stock": 25,
    },
    {
        "name": "BassWave 200",
        "description": "True wireless earbuds with deep bass boost, 28hr playtime with case, IPX5 water resistance, and fast pairing.",
        "category": "earbuds",
        "price_paise": 199900,
        "cost_paise": 89900,
        "tags": ["TWS", "earbuds", "bass", "waterproof", "wireless"],
        "stock": 50,
    },
    {
        "name": "NovaKeys Pro RGB",
        "description": "Tenkeyless mechanical gaming keyboard with hot-swappable tactile switches, per-key RGB, and PBT double-shot keycaps.",
        "category": "keyboards",
        "price_paise": 599900,
        "cost_paise": 320000,
        "tags": ["mechanical", "RGB", "gaming", "TKL", "hot-swap"],
        "stock": 15,
    },
    {
        "name": "AeroGlide Wireless Mouse",
        "description": "Ultra-lightweight 58g wireless gaming mouse with 26K DPI optical sensor, optical switches, and 80hr battery.",
        "category": "mice",
        "price_paise": 349900,
        "cost_paise": 170000,
        "tags": ["wireless", "gaming", "lightweight", "high-DPI"],
        "stock": 30,
    },
    {
        "name": "HyperCharge 65W GaN",
        "description": "65W GaN USB-C charger with 3 ports (2x USB-C PD + 1x USB-A). Charges laptop + phone simultaneously.",
        "category": "chargers",
        "price_paise": 249900,
        "cost_paise": 99900,
        "tags": ["GaN", "USB-C", "PD", "fast-charge", "multi-port"],
        "stock": 45,
    },
    {
        "name": "PowerCore 20000 Power Bank",
        "description": "20,000mAh high-capacity power bank with 45W Power Delivery output, digital battery display, and airline-safe design.",
        "category": "chargers",
        "price_paise": 299900,
        "cost_paise": 140000,
        "tags": ["powerbank", "PD", "fast-charge", "high-capacity"],
        "stock": 35,
    },
    {
        "name": "DeskMat Pro XL",
        "description": "Extended 900x400mm waterproof desk mat with micro-woven cloth surface, anti-fray stitched edges, and non-slip rubber base.",
        "category": "accessories",
        "price_paise": 99900,
        "cost_paise": 35000,
        "tags": ["deskmat", "mousepad", "waterproof", "accessories"],
        "stock": 100,
    },
    {
        "name": "ArmourShield USB-C Cable (2m)",
        "description": "Braided nylon USB-C to USB-C 100W cable with E-marker chip, 480Mbps data transfer, and 20,000+ bend lifespan.",
        "category": "accessories",
        "price_paise": 49900,
        "cost_paise": 15000,
        "tags": ["cable", "USB-C", "100W", "braided", "durable"],
        "stock": 200,
    },
    {
        "name": "StreamVision 4K Webcam",
        "description": "4K Ultra-HD webcam with Sony STARVIS sensor, dual noise-cancelling mics, autofocus, and physical privacy shutter.",
        "category": "cameras",
        "price_paise": 799900,
        "cost_paise": 450000,
        "tags": ["webcam", "4K", "streaming", "noise-cancelling", "autofocus"],
        "stock": 12,
    },
    {
        "name": "ErgoRest Wrist Pad",
        "description": "Memory foam ergonomic keyboard wrist rest with cooling gel layer, breathable Lycra cover, and non-skid backing.",
        "category": "accessories",
        "price_paise": 79900,
        "cost_paise": 28000,
        "tags": ["ergonomic", "wrist-rest", "memory-foam", "accessories"],
        "stock": 60,
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify DB connection, ensure tables & schema updates, auto-seed catalog. Shutdown: dispose engine."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS prev_hash VARCHAR(64);"))
        await conn.execute(text("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS current_hash VARCHAR(64);"))

    # Idempotent auto-seed catalog
    try:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            existing = await session.execute(select(Merchant).where(Merchant.id == MERCHANT_ID))
            if not existing.scalar_one_or_none():
                merchant = Merchant(id=MERCHANT_ID, name="TechMesh Electronics", is_active=True)
                session.add(merchant)

                policy = Policy(
                    merchant_id=MERCHANT_ID,
                    max_discount_pct=Decimal("15.00"),
                    min_margin_pct=Decimal("10.00"),
                    max_negotiation_rounds=2,
                    max_order_value_paise=5_000_000,
                    offer_ttl_seconds=600,
                )
                session.add(policy)

                for p_data in INITIAL_PRODUCTS:
                    product = Product(
                        name=p_data["name"],
                        description=p_data["description"],
                        category=p_data["category"],
                        price_paise=p_data["price_paise"],
                        cost_paise=p_data["cost_paise"],
                        tags=p_data["tags"],
                        is_active=True,
                    )
                    session.add(product)
                    await session.flush()

                    inv = Inventory(
                        product_id=product.id,
                        total_stock=p_data["stock"],
                        reserved=0,
                    )
                    session.add(inv)

                await session.commit()
                print("[Lifespan] Initial catalog auto-seeded successfully!")
            else:
                print("[Lifespan] Database already seeded.")
    except Exception as e:
        print(f"[Lifespan] Auto-seed status: {e}")

    yield
    await engine.dispose()


app = FastAPI(
    title="Dual-Agent Commerce Mesh",
    description="AI buyer + merchant agents transacting over structured JSON contracts with Razorpay Test Mode",
    version="0.2.0",
    lifespan=lifespan,
)

import os

# CORS — allow Vercel production/preview domains, localhost, and custom ALLOWED_ORIGINS
settings = get_settings()
_allowed_origins_str = os.environ.get("ALLOWED_ORIGINS", "")
_allowed_origins = [o.strip() for o in _allowed_origins_str.split(",") if o.strip()]
_default_origins = [
    "https://dual-agent-commerce-mesh.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
for o in _default_origins:
    if o not in _allowed_origins:
        _allowed_origins.append(o)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(webhooks.router)
app.include_router(ws.router)
app.include_router(sessions.router)
app.include_router(ai_agent_mesh.router)
app.include_router(policies.router)

from fastapi import Request
from fastapi.responses import JSONResponse
from app.services.llm_client import LLMExecutionError

@app.exception_handler(LLMExecutionError)
async def llm_execution_error_handler(request: Request, exc: LLMExecutionError):
    return JSONResponse(
        status_code=400,
        content={"detail": f"AI Engine Configuration Notice: {str(exc)}"},
    )

