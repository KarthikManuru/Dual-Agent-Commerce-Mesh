from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check — pings the database and returns connection status."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        db=db_status,
        timestamp=datetime.now(timezone.utc),
    )
