import json
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.webhook_event import WebhookEvent
from app.services.razorpay_client import razorpay_service
from app.services.queue import enqueue_webhook_event

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/razorpay")
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(None, alias="X-Razorpay-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Razorpay Webhook Handler:
    1. Validates HMAC-SHA256 signature against RAZORPAY_WEBHOOK_SECRET.
    2. Enforces idempotency using razorpay_event_id in webhook_events table.
    3. Persists event and delegates heavy processing to background worker.
    4. Responds with HTTP 200 immediately.
    """
    body_bytes = await request.body()

    # 1. Verify Signature
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")

    try:
        is_valid = razorpay_service.verify_webhook_signature(body_bytes, x_razorpay_signature)
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="Signature verification failed")

    # 2. Parse JSON payload
    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event", "unknown")
    event_id = payload.get("event_id") or payload.get("id") or f"evt_{payload.get('created_at', '')}_{event_type}"

    # 3. Idempotency Check
    stmt = select(WebhookEvent).where(WebhookEvent.razorpay_event_id == event_id)
    res = await db.execute(stmt)
    existing_event = res.scalar_one_or_none()

    if existing_event:
        # Event already received and recorded — return 200 immediately
        return {"status": "ignored_duplicate", "event_id": event_id}

    # 4. Save to webhook_events dedup table
    new_event = WebhookEvent(
        razorpay_event_id=event_id,
        event_type=event_type,
        payload=payload,
        processed=False,
    )
    db.add(new_event)
    await db.commit()

    # 5. Enqueue background task
    enqueue_webhook_event(event_id, event_type, payload)

    return {"status": "accepted", "event_id": event_id}
