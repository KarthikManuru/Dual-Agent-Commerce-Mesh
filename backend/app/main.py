from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.routers import health, products, orders, webhooks, ws, sessions, ai_agent_mesh, policies


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify DB connection & ensure schema updates. Shutdown: dispose engine."""
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
        await conn.execute(text("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS prev_hash VARCHAR(64);"))
        await conn.execute(text("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS current_hash VARCHAR(64);"))
    yield
    await engine.dispose()


app = FastAPI(
    title="Dual-Agent Commerce Mesh",
    description="AI buyer + merchant agents transacting over structured JSON contracts with Razorpay Test Mode",
    version="0.2.0",
    lifespan=lifespan,
)

import os

# CORS — read allowed origins from env var; fallback to localhost for local dev
settings = get_settings()
_allowed_origins_str = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
)
_allowed_origins = [o.strip() for o in _allowed_origins_str.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
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

