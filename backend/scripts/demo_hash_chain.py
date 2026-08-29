"""
Live Demonstration: SHA-256 Cryptographic Hash-Chained Audit Trail & Tamper Detection.

Steps:
1. Initialize test database connection and schema.
2. Create an order and append 3 cryptographic audit events.
3. Verify that the initial hash chain validates 100% cleanly.
4. Directly tamper with historical DB data via raw SQL (bypassing application logic).
5. Re-run cryptographic verification and prove that tamper detection catches the intrusion.
"""

import asyncio
import sys
import uuid
import os
import logging
from decimal import Decimal
from datetime import datetime, timezone

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, text
from app.database import AsyncSessionLocal, engine
from app.models.merchant import Merchant
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.enums import OrderStatus
from app.services.audit import log_order_event, verify_order_chain, GENESIS_HASH


async def run_hash_chain_demo():
    print("=" * 70)
    print("LIVE DEMO: SHA-256 CRYPTOGRAPHIC HASH CHAIN & TAMPER DETECTION")
    print("=" * 70)

    # 1. Setup DB columns if needed
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS prev_hash VARCHAR(64);"))
        await conn.execute(text("ALTER TABLE order_events ADD COLUMN IF NOT EXISTS current_hash VARCHAR(64);"))

    order_id = uuid.uuid4()
    merchant_id = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    product_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        # Create merchant & product for test
        m_stmt = select(Merchant).where(Merchant.id == merchant_id)
        m_res = await session.execute(m_stmt)
        if not m_res.scalar_one_or_none():
            merchant = Merchant(
                id=merchant_id,
                name="Acoustic Labs Pro",
                razorpay_key_id="rzp_test_mock",
                is_active=True,
            )
            session.add(merchant)

        prod = Product(
            id=product_id,
            name="Cryptographic Audit Demo Headphones",
            description="Testing tamper-evident blockchain-style audit trail",
            category="headphones",
            price_paise=299900,
            cost_paise=180000,
            currency="INR",
            is_active=True,
            tags=[],
        )
        session.add(prod)
        session.add(Inventory(product_id=product_id, total_stock=10, reserved=0))

        order = Order(
            id=order_id,
            merchant_id=merchant_id,
            product_id=product_id,
            quantity=1,
            unit_price_paise=299900,
            total_paise=299900,
            currency="INR",
            status=OrderStatus.PAYMENT_PENDING.value,
        )
        session.add(order)
        await session.flush()

        print(f"\n[STEP 1] Created Order ID: {order_id}")
        print("Appending 3 cryptographic hash-chained audit events ...\n")

        # Event 1: Discovery & Selection
        e1 = await log_order_event(
            db=session,
            order_id=order_id,
            actor="SYSTEM",
            action="ORDER_DISCOVERED_AND_SELECTED",
            from_status="DISCOVERED",
            to_status="SELECTED",
            detail={"product_id": str(product_id), "quantity": 1},
            result="ALLOW",
        )
        await session.flush()

        # Event 2: Negotiation & Guard Check
        e2 = await log_order_event(
            db=session,
            order_id=order_id,
            actor="GUARD",
            action="FINANCIAL_GUARD_CONCESSION_EVALUATED",
            from_status="SELECTED",
            to_status="OFFER_ACCEPTED",
            detail={"discount_pct": "10.00", "verdict": "ALLOW"},
            result="ALLOW",
        )
        await session.flush()

        # Event 3: Payment Initiated
        e3 = await log_order_event(
            db=session,
            order_id=order_id,
            actor="RAZORPAY",
            action="PAYMENT_PENDING_INITIATED",
            from_status="OFFER_ACCEPTED",
            to_status="PAYMENT_PENDING",
            detail={"razorpay_order_id": "order_mock_test_123"},
            result="ALLOW",
        )
        await session.commit()

        # Print the chain
        events = [e1, e2, e3]
        for idx, ev in enumerate(events, 1):
            print(f"  Event #{idx} [{ev.action}] by {ev.actor}:")
            print(f"    Event ID:     {ev.id}")
            print(f"    prev_hash:    {ev.prev_hash}")
            print(f"    current_hash: {ev.current_hash}\n")

    # [STEP 2] Verification of Untampered Chain
    print("[STEP 2] Cryptographically verifying chain integrity before tampering ...")
    async with AsyncSessionLocal() as session:
        result_valid = await verify_order_chain(session, order_id)
        print(f"  Verification Result: Valid = {result_valid['valid']}")
        print(f"  Message: {result_valid.get('message')}")
        print(f"  Final Chain Head Hash: {result_valid.get('last_hash')}")
        assert result_valid["valid"] is True, "Expected valid chain before tamper"
        print("  [PASS] Initial audit trail cryptographic integrity verified.\n")

    # [STEP 3] Tamper Attack Simulation via Direct SQL Mutation
    print("[STEP 3] Simulating Direct Database Tampering Attack via Raw SQL ...")
    tampered_event_id = e2.id
    async with AsyncSessionLocal() as session:
        # Attacker modifies the guard decision from ALLOW to FORGED_BYPASS without updating hash
        await session.execute(
            text("UPDATE order_events SET result = 'FORGED' WHERE id = :eid"),
            {"eid": tampered_event_id},
        )
        await session.commit()
        print(f"  Attacker mutated Event ID {tampered_event_id} directly in PostgreSQL (result -> 'FORGED').\n")

    # [STEP 4] Verification of Tampered Chain
    print("[STEP 4] Re-verifying chain integrity after tampering ...")
    async with AsyncSessionLocal() as session:
        result_tampered = await verify_order_chain(session, order_id)
        print(f"  Verification Result: Valid = {result_tampered['valid']}")
        print(f"  Broken Event ID:     {result_tampered.get('broken_event_id')}")
        print(f"  Broken Event Index:  {result_tampered.get('event_index')}")
        print(f"  Reason:              {result_tampered.get('reason')}")
        assert result_tampered["valid"] is False, "Expected chain to fail after tampering"
        assert str(tampered_event_id) == result_tampered["broken_event_id"]
        print("\n  [PASS] Cryptographic audit trail detected unauthorized row tampering immediately!")

    print("\n" + "=" * 70)
    print("ALL SHA-256 AUDIT CHAIN & TAMPER-DETECTION TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_hash_chain_demo())
