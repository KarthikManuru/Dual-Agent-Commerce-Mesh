import uuid
import time
import asyncio
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.product import Product
from app.models.policy import Policy
from app.models.merchant import Merchant
from app.models.order import Order
from app.models.order_event import OrderEvent
from app.models.enums import OrderStatus, validate_transition
from app.models.negotiation_session import NegotiationSessionModel
from app.schemas.negotiation import (
    NegotiationMessage,
    BuyerConfig,
    BundleItem,
    NegotiationSessionOut,
)
from app.schemas.product import ProductOut
from app.agents.buyer_agent import buyer_agent
from app.agents.merchant_agent import merchant_agent
from app.agents.financial_guard import financial_guard
from app.agents.bundler import bundler
from app.services.razorpay_client import razorpay_service
from app.services.event_bus import manager
from app.config import get_settings


class NegotiationOrchestrator:
    """
    Coordinates multi-turn autonomous negotiations between Buyer LLM and Merchant LLM,
    enforcing deterministic FinancialActionGuard boundaries and executing single-source
    order creation through Razorpay.
    """

    async def run_session(
        self,
        db: AsyncSession,
        product: Product,
        merchant_id: uuid.UUID,
        buyer_config: BuyerConfig,
        preferred_bundle: bool = True,
    ) -> NegotiationSessionOut:
        start_time = time.time()
        session_id = str(uuid.uuid4())
        settings = get_settings()

        # 1. Fetch Merchant Policy
        stmt_policy = select(Policy).where(Policy.merchant_id == merchant_id)
        res_policy = await db.execute(stmt_policy)
        policy = res_policy.scalar_one_or_none()

        if not policy:
            # Create default policy if none exists
            from decimal import Decimal
            policy = Policy(
                merchant_id=merchant_id,
                max_discount_pct=Decimal("15.00"),
                min_margin_pct=Decimal("10.00"),
                max_negotiation_rounds=2,
                max_order_value_paise=5_000_000,
                offer_ttl_seconds=600,
            )
            db.add(policy)
            await db.flush()

        messages: List[NegotiationMessage] = []
        agreed_price_paise: Optional[int] = None
        included_bundle: Optional[BundleItem] = None
        outcome = "REJECTED"
        max_rounds = min(policy.max_negotiation_rounds, 2)

        # Broadcast initial discovery
        await self._broadcast_event({
            "type": "NEGOTIATION_STREAM",
            "session_id": session_id,
            "stage": "DISCOVERY",
            "product_name": product.name,
            "price_paise": product.price_paise,
            "buyer_strategy": buyer_config.strategy,
            "buyer_budget_paise": buyer_config.budget_paise,
        })

        # -------------------------------------------------------------
        # ROUND 1: Merchant Opening Offer
        # -------------------------------------------------------------
        merchant_msg_1 = await merchant_agent.generate_initial_offer(product, policy)
        
        # Financial Guard check on Merchant opening offer
        guard_v1 = financial_guard.evaluate_offer(
            product=product,
            policy=policy,
            offered_price_paise=merchant_msg_1.offered_price_paise,
            round_num=1,
        )

        messages.append(merchant_msg_1)
        await self._broadcast_message(session_id, merchant_msg_1)

        # Guard message
        guard_msg_1 = NegotiationMessage(
            sender="FINANCIAL_GUARD",
            intent="GUARD_ALLOW" if guard_v1.allowed else "GUARD_DENY",
            offered_price_paise=merchant_msg_1.offered_price_paise,
            discount_pct=guard_v1.effective_discount_pct,
            reasoning_text=f"Margin: {guard_v1.effective_margin_pct}% | Discount: {guard_v1.effective_discount_pct}% | Status: {guard_v1.result}",
            reason_codes=guard_v1.reason_codes,
            round=1,
            reasoning_source="DETERMINISTIC_GUARD",
            model_name="rules_engine_v1",
            latency_ms=1,
            timestamp=datetime.now(timezone.utc),
        )
        messages.append(guard_msg_1)
        await self._broadcast_message(session_id, guard_msg_1)

        if not guard_v1.allowed:
            outcome = "GUARD_BLOCKED"
        else:
            # -------------------------------------------------------------
            # ROUND 1: Buyer Response
            # -------------------------------------------------------------
            buyer_msg_1 = await buyer_agent.evaluate_and_respond(
                product=product,
                buyer_config=buyer_config,
                current_offer_paise=merchant_msg_1.offered_price_paise,
                round_num=1,
                conversation_history=messages,
            )
            messages.append(buyer_msg_1)
            await self._broadcast_message(session_id, buyer_msg_1)

            if buyer_msg_1.intent == "ACCEPT":
                outcome = "ACCEPTED"
                agreed_price_paise = buyer_msg_1.offered_price_paise
            elif buyer_msg_1.intent == "REJECT":
                outcome = "REJECTED"
            else:
                # Buyer countered — Round 2
                # Check for possible cross-sell bundling with remaining budget
                remaining_budget = max(0, buyer_config.budget_paise - buyer_msg_1.offered_price_paise)
                suggested_bundle = None
                if preferred_bundle and remaining_budget > 50000:
                    suggested_bundle = await bundler.suggest_bundle(
                        db=db,
                        main_product=product,
                        policy=policy,
                        remaining_budget_paise=remaining_budget,
                    )

                # -------------------------------------------------------------
                # ROUND 2: Merchant Response
                # -------------------------------------------------------------
                merchant_msg_2 = await merchant_agent.evaluate_and_respond(
                    product=product,
                    policy=policy,
                    buyer_message=buyer_msg_1,
                    round_num=2,
                    conversation_history=messages,
                    bundle_suggestion=suggested_bundle,
                )

                # Guard check on Merchant Round 2 response
                guard_v2 = financial_guard.evaluate_offer(
                    product=product,
                    policy=policy,
                    offered_price_paise=merchant_msg_2.offered_price_paise,
                    round_num=2,
                )

                messages.append(merchant_msg_2)
                await self._broadcast_message(session_id, merchant_msg_2)

                guard_msg_2 = NegotiationMessage(
                    sender="FINANCIAL_GUARD",
                    intent="GUARD_ALLOW" if guard_v2.allowed else "GUARD_DENY",
                    offered_price_paise=merchant_msg_2.offered_price_paise,
                    discount_pct=guard_v2.effective_discount_pct,
                    reasoning_text=f"Margin: {guard_v2.effective_margin_pct}% | Discount: {guard_v2.effective_discount_pct}% | Status: {guard_v2.result}",
                    reason_codes=guard_v2.reason_codes,
                    round=2,
                    reasoning_source="DETERMINISTIC_GUARD",
                    model_name="rules_engine_v1",
                    latency_ms=1,
                    timestamp=datetime.now(timezone.utc),
                )
                messages.append(guard_msg_2)
                await self._broadcast_message(session_id, guard_msg_2)

                if not guard_v2.allowed:
                    outcome = "GUARD_BLOCKED"
                elif merchant_msg_2.intent == "ACCEPT":
                    outcome = "ACCEPTED"
                    agreed_price_paise = merchant_msg_2.offered_price_paise
                    if suggested_bundle:
                        included_bundle = suggested_bundle
                else:
                    # -------------------------------------------------------------
                    # ROUND 2: Buyer Final Decision
                    # -------------------------------------------------------------
                    buyer_msg_2 = await buyer_agent.evaluate_and_respond(
                        product=product,
                        buyer_config=buyer_config,
                        current_offer_paise=merchant_msg_2.offered_price_paise,
                        round_num=2,
                        conversation_history=messages,
                    )
                    messages.append(buyer_msg_2)
                    await self._broadcast_message(session_id, buyer_msg_2)

                    if buyer_msg_2.intent == "ACCEPT":
                        outcome = "ACCEPTED"
                        agreed_price_paise = buyer_msg_2.offered_price_paise
                        if suggested_bundle:
                            included_bundle = suggested_bundle
                    else:
                        outcome = "REJECTED"

        # -------------------------------------------------------------
        # Single-Source Order Creation on ACCEPTED deal
        # -------------------------------------------------------------
        created_order_id = None
        razorpay_order_id = None
        final_price_paise = agreed_price_paise or product.price_paise

        if outcome == "ACCEPTED":
            # 1. Create order entity in DB
            order_uuid = uuid.uuid4()
            order = Order(
                id=order_uuid,
                merchant_id=merchant_id,
                product_id=product.id,
                quantity=1,
                unit_price_paise=final_price_paise,
                total_paise=final_price_paise,
                currency="INR",
                status=OrderStatus.DISCOVERED.value,
            )
            db.add(order)
            await db.flush()

            # Sequence: DISCOVERED -> SELECTED -> ORDER_CREATED -> PAYMENT_PENDING
            validate_transition(OrderStatus.DISCOVERED, OrderStatus.SELECTED)
            order.status = OrderStatus.SELECTED.value
            db.add(OrderEvent(
                order_id=order.id,
                actor="BUYER_AGENT",
                action="PRODUCT_SELECTED_AFTER_NEGOTIATION",
                from_status=OrderStatus.DISCOVERED.value,
                to_status=OrderStatus.SELECTED.value,
                detail={"agreed_price_paise": final_price_paise, "session_id": session_id},
                result="ALLOW",
            ))

            order.status = OrderStatus.ORDER_CREATED.value
            db.add(OrderEvent(
                order_id=order.id,
                actor="MERCHANT_AGENT",
                action="ORDER_COMMERCIAL_TERMS_FORMALIZED",
                from_status=OrderStatus.SELECTED.value,
                to_status=OrderStatus.ORDER_CREATED.value,
                detail={"total_paise": final_price_paise, "bundle": included_bundle.model_dump(mode="json") if included_bundle else None},
                result="ALLOW",
            ))

            # Call Razorpay Orders API at the negotiated price
            try:
                short_receipt = f"mesh_{str(order.id).replace('-', '')[:15]}"
                rzp_order = razorpay_service.create_order(
                    amount_paise=final_price_paise,
                    currency="INR",
                    receipt=short_receipt,
                    notes={
                        "order_id": str(order.id),
                        "product_name": product.name,
                        "session_id": session_id,
                        "negotiated": "true",
                    },
                )
                razorpay_order_id = rzp_order["id"]
                order.razorpay_order_id = razorpay_order_id
            except Exception as e:
                print(f"[Negotiation] Razorpay creation error: {e}")
                order.razorpay_order_id = f"order_mock_test_{int(time.time())}"
                razorpay_order_id = order.razorpay_order_id

            validate_transition(OrderStatus.ORDER_CREATED, OrderStatus.PAYMENT_PENDING)
            order.status = OrderStatus.PAYMENT_PENDING.value
            db.add(OrderEvent(
                order_id=order.id,
                actor="SYSTEM",
                action="PAYMENT_PENDING_AT_NEGOTIATED_TERMS",
                from_status=OrderStatus.ORDER_CREATED.value,
                to_status=OrderStatus.PAYMENT_PENDING.value,
                detail={"razorpay_order_id": razorpay_order_id, "amount_paise": final_price_paise},
                result="ALLOW",
            ))

            await db.commit()
            created_order_id = str(order.id)

            # Broadcast new order to Kanban stream
            await manager.broadcast({
                "type": "ORDER_CREATED",
                "order_id": str(order.id),
                "status": order.status,
                "product_name": product.name,
                "total_paise": order.total_paise,
                "razorpay_order_id": order.razorpay_order_id,
            })

        # Calculate discount achieved
        discount_achieved = 0.0
        if product.price_paise > 0 and final_price_paise < product.price_paise:
            discount_achieved = round(((product.price_paise - final_price_paise) / product.price_paise) * 100, 2)

        duration = int((time.time() - start_time) * 1000)

        # -------------------------------------------------------------
        # Save Negotiation Session Record
        # -------------------------------------------------------------
        session_record = NegotiationSessionModel(
            id=uuid.UUID(session_id),
            product_id=product.id,
            merchant_id=merchant_id,
            buyer_name=buyer_config.name,
            buyer_strategy=buyer_config.strategy,
            buyer_budget_paise=buyer_config.budget_paise,
            outcome=outcome,
            agreed_price_paise=final_price_paise if outcome == "ACCEPTED" else None,
            discount_achieved_pct=discount_achieved if outcome == "ACCEPTED" else 0.0,
            bundle_data=included_bundle.model_dump(mode="json") if included_bundle else None,
            total_rounds=max(m.round for m in messages if m.round),
            order_id=uuid.UUID(created_order_id) if created_order_id else None,
            messages=[m.model_dump(mode="json") for m in messages],
            duration_ms=duration,
        )
        db.add(session_record)
        await db.commit()

        # Final broadcast of session result
        await self._broadcast_event({
            "type": "NEGOTIATION_COMPLETE",
            "session_id": session_id,
            "outcome": outcome,
            "agreed_price_paise": final_price_paise,
            "discount_achieved_pct": discount_achieved,
            "order_id": created_order_id,
            "razorpay_order_id": razorpay_order_id,
            "duration_ms": duration,
        })

        return NegotiationSessionOut(
            session_id=session_id,
            product=ProductOut.model_validate(product),
            buyer=buyer_config,
            messages=messages,
            outcome=outcome,
            agreed_price_paise=final_price_paise if outcome == "ACCEPTED" else None,
            discount_achieved_pct=discount_achieved if outcome == "ACCEPTED" else 0.0,
            bundle_included=included_bundle,
            total_rounds=max(m.round for m in messages if m.round),
            order_id=created_order_id,
            razorpay_order_id=razorpay_order_id,
            duration_ms=duration,
            created_at=datetime.now(timezone.utc),
        )

    async def _broadcast_message(self, session_id: str, msg: NegotiationMessage):
        """Broadcast live message turn to WebSocket clients."""
        await manager.broadcast({
            "type": "NEGOTIATION_MESSAGE",
            "session_id": session_id,
            "message": msg.model_dump(mode="json"),
        })


    async def _broadcast_event(self, payload: dict):
        """Broadcast arbitrary status event to WebSocket clients."""
        await manager.broadcast(payload)


negotiation_orchestrator = NegotiationOrchestrator()
