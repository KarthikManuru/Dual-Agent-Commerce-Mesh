import uuid
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from pydantic import BaseModel

from datetime import datetime, timezone
from app.database import get_db
from app.config import get_settings
from app.models.order import Order
from app.models.order_event import OrderEvent
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.offer import Offer
from app.models.enums import OrderStatus, validate_transition, is_at_or_past
from app.schemas.order import OrderOut, OrderListResponse, OrderCreate
from app.services.razorpay_client import razorpay_service
from app.services.event_bus import manager
from app.services.audit import log_order_event, verify_order_chain

router = APIRouter(prefix="/orders", tags=["Orders"])
settings = get_settings()


class OrderCreateResponse(BaseModel):
    order: OrderOut
    razorpay_order_id: str
    razorpay_key_id: str
    amount_paise: int
    currency: str


class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("", response_model=OrderCreateResponse)
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new order and generate a real Razorpay Test Mode order:
    1. Validates product, stock availability, and optional time-bounded offer TTL.
    2. Progresses state: DISCOVERED -> SELECTED -> ORDER_CREATED -> PAYMENT_PENDING.
    3. Calls Razorpay Orders API.
    4. Writes hash-chained cryptographic audit events for each step.
    5. Returns order and Razorpay credentials for Checkout.js.
    """
    # 1. Look up product & lock inventory row
    stmt = (
        select(Product)
        .options(joinedload(Product.inventory))
        .where(Product.id == body.product_id, Product.is_active == True)
    )
    res = await db.execute(stmt)
    product = res.unique().scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found or inactive")

    # Validate offer if provided
    unit_price = product.price_paise
    matched_offer: Offer | None = None
    if body.offer_id:
        offer_stmt = select(Offer).where(Offer.id == body.offer_id)
        offer_res = await db.execute(offer_stmt)
        matched_offer = offer_res.scalar_one_or_none()
        if not matched_offer:
            raise HTTPException(status_code=404, detail=f"Offer {body.offer_id} not found")
        
        # Check offer expiration
        now = datetime.now(timezone.utc)
        if matched_offer.is_expired or matched_offer.expires_at < now:
            matched_offer.is_expired = True
            await db.flush()
            raise HTTPException(status_code=400, detail=f"Offer {body.offer_id} has expired (TTL elapsed)")
        
        if matched_offer.product_id != body.product_id or matched_offer.merchant_id != body.merchant_id:
            raise HTTPException(status_code=400, detail="Offer does not match specified product or merchant")
        
        unit_price = matched_offer.offered_price_paise
        matched_offer.is_accepted = True

    # Atomic conditional update: only increments reserved if sufficient available stock remains
    from sqlalchemy import update
    update_stmt = (
        update(Inventory)
        .where(
            Inventory.product_id == body.product_id,
            (Inventory.total_stock - Inventory.reserved) >= body.quantity,
        )
        .values(reserved=Inventory.reserved + body.quantity)
        .returning(Inventory.id)
    )
    update_res = await db.execute(update_stmt)
    if not update_res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Insufficient inventory available")

    await db.flush()

    total_price = unit_price * body.quantity

    # 2. Create Order in database (Starts at DISCOVERED)
    order_id = uuid.uuid4()
    order = Order(
        id=order_id,
        merchant_id=body.merchant_id,
        product_id=body.product_id,
        quantity=body.quantity,
        offer_id=matched_offer.id if matched_offer else None,
        unit_price_paise=unit_price,
        total_paise=total_price,
        currency="INR",
        status=OrderStatus.DISCOVERED.value,
    )
    db.add(order)
    await db.flush()

    if matched_offer:
        matched_offer.order_id = order.id

    # Record DISCOVERED -> SELECTED
    validate_transition(OrderStatus.DISCOVERED, OrderStatus.SELECTED)
    order.status = OrderStatus.SELECTED.value
    await log_order_event(
        db=db,
        order_id=order.id,
        actor="SYSTEM",
        action="ORDER_DISCOVERED_AND_SELECTED",
        from_status=OrderStatus.DISCOVERED.value,
        to_status=OrderStatus.SELECTED.value,
        detail={"product_id": str(product.id), "quantity": body.quantity, "offer_id": str(matched_offer.id) if matched_offer else None},
        result="ALLOW",
    )
    await db.flush()

    # Record SELECTED -> ORDER_CREATED
    order.status = OrderStatus.ORDER_CREATED.value
    await log_order_event(
        db=db,
        order_id=order.id,
        actor="SYSTEM",
        action="ORDER_INITIALIZED",
        from_status=OrderStatus.SELECTED.value,
        to_status=OrderStatus.ORDER_CREATED.value,
        detail={"total_paise": total_price, "currency": "INR", "unit_price_paise": unit_price},
        result="ALLOW",
    )
    await db.flush()

    # 3. Call Razorpay Orders API
    try:
        short_receipt = f"rcpt_{str(order.id).replace('-', '')[:15]}"
        rzp_order = razorpay_service.create_order(
            amount_paise=total_price,
            currency="INR",
            receipt=short_receipt,
            notes={
                "order_id": str(order.id),
                "product_id": str(product.id),
                "product_name": product.name,
            },
        )
        razorpay_order_id = rzp_order["id"]
        order.razorpay_order_id = razorpay_order_id
    except Exception as e:
        await log_order_event(
            db=db,
            order_id=order.id,
            actor="SYSTEM",
            action="RAZORPAY_ORDER_CREATION_FAILED",
            from_status=order.status,
            to_status=OrderStatus.CANCELLED.value,
            detail={"error": str(e)},
            result="DENY",
        )
        order.status = OrderStatus.CANCELLED.value
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Razorpay order creation failed: {str(e)}")

    # 4. Advance state: ORDER_CREATED -> PAYMENT_PENDING
    validate_transition(OrderStatus.ORDER_CREATED, OrderStatus.PAYMENT_PENDING)
    order.status = OrderStatus.PAYMENT_PENDING.value
    await log_order_event(
        db=db,
        order_id=order.id,
        actor="SYSTEM",
        action="PAYMENT_INITIATED",
        from_status=OrderStatus.ORDER_CREATED.value,
        to_status=OrderStatus.PAYMENT_PENDING.value,
        detail={"razorpay_order_id": razorpay_order_id},
        result="ALLOW",
    )

    await db.commit()
    await db.refresh(order)

    # Broadcast event
    await manager.broadcast({
        "type": "ORDER_CREATED",
        "order_id": str(order.id),
        "status": order.status,
        "product_name": product.name,
        "total_paise": order.total_paise,
        "razorpay_order_id": order.razorpay_order_id,
    })

    return OrderCreateResponse(
        order=OrderOut.model_validate(order),
        razorpay_order_id=razorpay_order_id,
        razorpay_key_id=settings.RAZORPAY_KEY_ID,
        amount_paise=total_price,
        currency="INR",
    )


@router.post("/{order_id}/verify", response_model=OrderOut)
async def verify_payment(
    order_id: UUID,
    body: PaymentVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify payment signature after frontend Checkout.js success callback:
    1. Verifies HMAC-SHA256 signature using RAZORPAY_KEY_SECRET.
    2. Advances status: PAYMENT_PENDING -> PAYMENT_AUTHORIZED -> PAYMENT_CAPTURED -> ORDER_PAID -> FULFILLED.
    3. Idempotent-by-status: if order already at or past a target state, logs INFO and skips.
    4. Records immutable audit logs.
    5. Broadcasts real-time WebSocket update.
    """
    stmt = (
        select(Order)
        .options(selectinload(Order.events))
        .where(Order.id == order_id)
    )
    res = await db.execute(stmt)
    order = res.unique().scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    current = OrderStatus(order.status)

    # Idempotent early exit: if order is already FULFILLED, no-op with success
    if current == OrderStatus.FULFILLED:
        await log_order_event(
            db=db,
            order_id=order.id,
            actor="RAZORPAY_CHECKOUT",
            action="VERIFY_ALREADY_FULFILLED",
            from_status=current.value,
            to_status=current.value,
            detail={"razorpay_payment_id": body.razorpay_payment_id, "note": "Order already fulfilled, verify is a no-op"},
            result="INFO",
        )
        await db.commit()
        await db.refresh(order)
        return OrderOut.model_validate(order)

    # Verify signature
    is_valid = razorpay_service.verify_payment_signature(
        razorpay_order_id=body.razorpay_order_id,
        razorpay_payment_id=body.razorpay_payment_id,
        razorpay_signature=body.razorpay_signature,
    )

    if not is_valid:
        await log_order_event(
            db=db,
            order_id=order.id,
            actor="SYSTEM",
            action="SIGNATURE_VERIFICATION_FAILED",
            from_status=order.status,
            to_status=OrderStatus.PAYMENT_FAILED.value,
            detail={"razorpay_payment_id": body.razorpay_payment_id},
            result="DENY",
        )
        order.status = OrderStatus.PAYMENT_FAILED.value
        await db.commit()
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Update order with payment ID
    order.razorpay_payment_id = body.razorpay_payment_id

    # Sequence of state transitions
    transitions = [
        OrderStatus.PAYMENT_AUTHORIZED,
        OrderStatus.PAYMENT_CAPTURED,
        OrderStatus.ORDER_PAID,
        OrderStatus.FULFILLED,
    ]

    for next_st in transitions:
        # Idempotent-by-status: if already at or past this state, skip gracefully
        if is_at_or_past(current, next_st):
            await log_order_event(
                db=db,
                order_id=order.id,
                actor="RAZORPAY_CHECKOUT",
                action=f"VERIFY_SKIP_{next_st.value}",
                from_status=current.value,
                to_status=next_st.value,
                detail={"razorpay_payment_id": body.razorpay_payment_id, "note": f"Already at or past {next_st.value}"},
                result="INFO",
            )
            await db.flush()
            continue

        try:
            validate_transition(current, next_st)
            await log_order_event(
                db=db,
                order_id=order.id,
                actor="RAZORPAY_CHECKOUT",
                action=f"PAYMENT_TRANSITION_{next_st.value}",
                from_status=current.value,
                to_status=next_st.value,
                detail={"razorpay_payment_id": body.razorpay_payment_id},
                result="ALLOW",
            )
            await db.flush()
            order.status = next_st.value
            current = next_st
        except Exception as e:
            print(f"[Verify] Transition skip/error: {e}")
            break

    # Permanently deduct inventory when reaching FULFILLED
    if current == OrderStatus.FULFILLED:
        inv_stmt = (
            select(Inventory)
            .where(Inventory.product_id == order.product_id)
            .with_for_update()
        )
        inv_res = await db.execute(inv_stmt)
        inv = inv_res.scalar_one_or_none()
        if inv:
            inv.total_stock = max(0, inv.total_stock - order.quantity)
            inv.reserved = max(0, inv.reserved - order.quantity)

    await db.commit()
    await db.refresh(order)

    # Broadcast update
    await manager.broadcast({
        "type": "ORDER_UPDATED",
        "order_id": str(order.id),
        "status": order.status,
        "razorpay_order_id": order.razorpay_order_id,
        "razorpay_payment_id": order.razorpay_payment_id,
    })

    return OrderOut.model_validate(order)


@router.get("/{order_id}/verify-audit-chain")
async def verify_order_audit_chain(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Cryptographically walks and verifies the SHA-256 hash chain of the order events.
    """
    return await verify_order_chain(db, order_id)


@router.get("", response_model=OrderListResponse)
async def list_orders(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all orders with their events."""
    query = select(Order).options(selectinload(Order.events))

    if status:
        query = query.where(Order.status == status)

    query = query.order_by(Order.created_at.desc())
    result = await db.execute(query)
    orders = result.unique().scalars().all()

    return OrderListResponse(
        orders=[OrderOut.model_validate(o) for o in orders],
        total=len(orders),
    )


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get single order with full audit event history."""
    query = (
        select(Order)
        .options(selectinload(Order.events))
        .where(Order.id == order_id)
    )
    result = await db.execute(query)
    order = result.unique().scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderOut.model_validate(order)
