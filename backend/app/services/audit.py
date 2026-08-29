import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_event import OrderEvent


GENESIS_HASH = "0" * 64


def compute_event_hash(
    prev_hash: Optional[str],
    order_id: uuid.UUID | str,
    actor: str,
    action: str,
    from_status: Optional[str],
    to_status: Optional[str],
    detail: Optional[dict],
    created_at: datetime | str,
    result: Optional[str] = "INFO",
) -> str:
    """
    Computes a cryptographic SHA-256 hash for an order audit event.
    Creates a tamper-evident hash chain linking each event to its predecessor.
    """
    p_hash = prev_hash or GENESIS_HASH
    dt_str = str(created_at) if created_at else ""
    sorted_detail = json.dumps(detail or {}, sort_keys=True)
    payload = f"{p_hash}|{str(order_id)}|{actor}|{action}|{from_status or ''}|{to_status or ''}|{result or 'INFO'}|{sorted_detail}|{dt_str}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def log_order_event(
    db: AsyncSession,
    order_id: uuid.UUID,
    actor: str,
    action: str,
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
    detail: Optional[dict] = None,
    result: str = "INFO",
) -> OrderEvent:
    """
    Appends a new hash-chained audit event to the order's immutable ledger.
    """
    # 1. Fetch latest event for this order to find its current_hash
    stmt = (
        select(OrderEvent)
        .where(OrderEvent.order_id == order_id)
        .order_by(OrderEvent.created_at.desc(), OrderEvent.id.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    last_event = res.scalar_one_or_none()
    prev_hash = last_event.current_hash if (last_event and last_event.current_hash) else GENESIS_HASH

    now = datetime.now(timezone.utc)
    event_id = uuid.uuid4()
    cur_hash = compute_event_hash(
        prev_hash=prev_hash,
        order_id=order_id,
        actor=actor,
        action=action,
        from_status=from_status,
        to_status=to_status,
        detail=detail,
        created_at=now,
        result=result,
    )

    event = OrderEvent(
        id=event_id,
        order_id=order_id,
        actor=actor,
        action=action,
        from_status=from_status,
        to_status=to_status,
        detail=detail or {},
        result=result,
        prev_hash=prev_hash,
        current_hash=cur_hash,
        created_at=now,
        updated_at=now,
    )
    db.add(event)
    return event


async def verify_order_chain(db: AsyncSession, order_id: uuid.UUID) -> dict[str, Any]:
    """
    Walks the cryptographic hash chain of an order and verifies:
    1. prev_hash matches the previous event's current_hash (Genesis = 64 zeros).
    2. current_hash matches SHA256(fields).
    Returns {"valid": True, "count": N} or {"valid": False, "broken_event_id": UUID, "reason": str}
    """
    stmt = (
        select(OrderEvent)
        .where(OrderEvent.order_id == order_id)
        .order_by(OrderEvent.created_at.asc(), OrderEvent.id.asc())
    )
    res = await db.execute(stmt)
    events = list(res.scalars().all())

    if not events:
        return {"valid": True, "count": 0, "message": "No events found for order"}

    expected_prev = GENESIS_HASH
    for idx, event in enumerate(events):
        # Check linkage
        if event.prev_hash != expected_prev:
            return {
                "valid": False,
                "broken_event_id": str(event.id),
                "event_index": idx,
                "reason": f"Linkage broken at event {idx}: expected prev_hash '{expected_prev}', got '{event.prev_hash}'",
            }

        # Check content integrity
        recomputed_hash = compute_event_hash(
            prev_hash=event.prev_hash,
            order_id=event.order_id,
            actor=event.actor,
            action=event.action,
            from_status=event.from_status,
            to_status=event.to_status,
            detail=event.detail,
            created_at=event.created_at,
            result=event.result,
        )
        if event.current_hash != recomputed_hash:
            return {
                "valid": False,
                "broken_event_id": str(event.id),
                "event_index": idx,
                "reason": f"Tampered content at event {idx} ({event.action}): stored hash '{event.current_hash}' != recomputed '{recomputed_hash}'",
            }

        expected_prev = event.current_hash

    return {
        "valid": True,
        "count": len(events),
        "last_hash": expected_prev,
        "message": f"Cryptographic integrity verified across all {len(events)} events in chain",
    }
