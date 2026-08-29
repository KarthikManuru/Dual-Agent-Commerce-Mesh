import asyncio
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models.order import Order
from app.models.order_event import OrderEvent
from app.models.webhook_event import WebhookEvent
from app.models.enums import OrderStatus, validate_transition, is_at_or_past
from app.services.event_bus import manager


async def process_webhook_event_async(event_id: str, event_type: str, payload: dict):
    """
    Asynchronously processes a verified Razorpay webhook event:
    1. Extracts razorpay_order_id, razorpay_payment_id, payment status.
    2. Idempotent-by-status: if order already at or past the target state, logs INFO and skips.
    3. Updates orders.status through the state machine.
    4. Writes immutable audit rows to order_events.
    5. Marks webhook_event as processed=True.
    6. Broadcasts real-time WebSocket update to connected dashboard clients.
    """
    event_payload = payload.get("payload", {})
    payment_entity = event_payload.get("payment", {}).get("entity", {})
    order_entity = event_payload.get("order", {}).get("entity", {})

    razorpay_order_id = payment_entity.get("order_id") or order_entity.get("id")
    razorpay_payment_id = payment_entity.get("id")

    if not razorpay_order_id:
        print(f"[WebhookWorker] Warning: No order_id found in event {event_id}")
        return

    async with AsyncSessionLocal() as session:
        # 1. Fetch Order by razorpay_order_id
        stmt = select(Order).where(Order.razorpay_order_id == razorpay_order_id)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            print(f"[WebhookWorker] Order with razorpay_order_id={razorpay_order_id} not found.")
            return

        current_status = OrderStatus(order.status)

        # Idempotent early exit: if order is already FULFILLED, no-op with INFO log
        if current_status == OrderStatus.FULFILLED:
            session.add(OrderEvent(
                order_id=order.id,
                actor="RAZORPAY_WEBHOOK",
                action=f"WEBHOOK_ALREADY_FULFILLED_{event_type.upper().replace('.', '_')}",
                from_status=current_status.value,
                to_status=current_status.value,
                detail={
                    "event_id": event_id,
                    "event_type": event_type,
                    "razorpay_payment_id": razorpay_payment_id,
                    "note": "Order already fulfilled, webhook is a no-op",
                },
                result="INFO",
            ))
            # Still mark webhook as processed
            await session.execute(
                update(WebhookEvent)
                .where(WebhookEvent.razorpay_event_id == event_id)
                .values(processed=True)
            )
            await session.commit()
            print(f"[WebhookWorker] Order {order.id} already FULFILLED, skipping {event_type} (idempotent)")
            return

        target_statuses: list[OrderStatus] = []

        # Map Razorpay Webhook Event Types to State Transitions
        if event_type == "payment.authorized":
            target_statuses = [OrderStatus.PAYMENT_AUTHORIZED]
        elif event_type == "payment.captured":
            # Direct or auto-captured payment
            if current_status == OrderStatus.PAYMENT_PENDING:
                target_statuses = [OrderStatus.PAYMENT_AUTHORIZED, OrderStatus.PAYMENT_CAPTURED, OrderStatus.ORDER_PAID, OrderStatus.FULFILLED]
            elif current_status == OrderStatus.PAYMENT_AUTHORIZED:
                target_statuses = [OrderStatus.PAYMENT_CAPTURED, OrderStatus.ORDER_PAID, OrderStatus.FULFILLED]
            elif current_status == OrderStatus.PAYMENT_CAPTURED:
                target_statuses = [OrderStatus.ORDER_PAID, OrderStatus.FULFILLED]
        elif event_type == "order.paid":
            if current_status in [OrderStatus.PAYMENT_CAPTURED, OrderStatus.ORDER_PAID]:
                target_statuses = [OrderStatus.FULFILLED]
            elif current_status == OrderStatus.PAYMENT_PENDING:
                target_statuses = [OrderStatus.PAYMENT_AUTHORIZED, OrderStatus.PAYMENT_CAPTURED, OrderStatus.ORDER_PAID, OrderStatus.FULFILLED]
        elif event_type == "payment.failed":
            target_statuses = [OrderStatus.PAYMENT_FAILED]

        # Apply state transitions sequentially through the state machine
        for next_status in target_statuses:
            # Idempotent-by-status: if already at or past this state, skip gracefully
            if is_at_or_past(current_status, next_status):
                session.add(OrderEvent(
                    order_id=order.id,
                    actor="RAZORPAY_WEBHOOK",
                    action=f"WEBHOOK_SKIP_{next_status.value}",
                    from_status=current_status.value,
                    to_status=next_status.value,
                    detail={
                        "event_id": event_id,
                        "event_type": event_type,
                        "razorpay_payment_id": razorpay_payment_id,
                        "note": f"Already at or past {next_status.value}",
                    },
                    result="INFO",
                ))
                continue

            try:
                validate_transition(current_status, next_status)

                # Log audit event
                audit_event = OrderEvent(
                    order_id=order.id,
                    actor="RAZORPAY_WEBHOOK",
                    action=f"WEBHOOK_{event_type.upper().replace('.', '_')}",
                    from_status=current_status.value,
                    to_status=next_status.value,
                    detail={
                        "event_id": event_id,
                        "event_type": event_type,
                        "razorpay_payment_id": razorpay_payment_id,
                        "amount_paise": payment_entity.get("amount"),
                        "method": payment_entity.get("method"),
                    },
                    result="ALLOW",
                )
                session.add(audit_event)
                order.status = next_status.value
                current_status = next_status

            except Exception as e:
                print(f"[WebhookWorker] Illegal transition or error {current_status} -> {next_status}: {e}")
                # Log denial/failure audit
                session.add(OrderEvent(
                    order_id=order.id,
                    actor="RAZORPAY_WEBHOOK",
                    action="TRANSITION_FAILED",
                    from_status=current_status.value,
                    to_status=next_status.value,
                    detail={"error": str(e), "event_id": event_id},
                    result="DENY",
                ))
                break

        if razorpay_payment_id:
            order.razorpay_payment_id = razorpay_payment_id

        # Mark WebhookEvent as processed
        await session.execute(
            update(WebhookEvent)
            .where(WebhookEvent.razorpay_event_id == event_id)
            .values(processed=True)
        )

        await session.commit()
        await session.refresh(order)

        # Broadcast live update via WebSocket
        payload_broadcast = {
            "type": "ORDER_UPDATED",
            "order_id": str(order.id),
            "status": order.status,
            "razorpay_order_id": order.razorpay_order_id,
            "razorpay_payment_id": order.razorpay_payment_id,
            "total_paise": order.total_paise,
            "currency": order.currency,
        }
        await manager.broadcast(payload_broadcast)
        print(f"[WebhookWorker] Successfully processed {event_type} for order {order.id} -> {order.status}")


def process_webhook_event_task(event_id: str, event_type: str, payload: dict):
    """Synchronous entrypoint called by RQ Worker."""
    asyncio.run(process_webhook_event_async(event_id, event_type, payload))
