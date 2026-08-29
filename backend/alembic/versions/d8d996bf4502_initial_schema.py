"""initial_schema

Revision ID: d8d996bf4502
Revises: 
Create Date: 2026-08-22 22:34:24.532296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd8d996bf4502'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Independent tables: merchants, products, webhook_events
    op.create_table(
        'merchants',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('razorpay_key_id', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'products',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('price_paise', sa.BigInteger(), nullable=False),
        sa.Column('cost_paise', sa.BigInteger(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'webhook_events',
        sa.Column('razorpay_event_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_events_razorpay_event_id'), 'webhook_events', ['razorpay_event_id'], unique=True)

    # 2. Tables dependent on merchants / products
    op.create_table(
        'inventory',
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('total_stock', sa.Integer(), nullable=False),
        sa.Column('reserved', sa.Integer(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id')
    )

    op.create_table(
        'policies',
        sa.Column('merchant_id', sa.UUID(), nullable=False),
        sa.Column('max_discount_pct', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('min_margin_pct', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('max_negotiation_rounds', sa.Integer(), nullable=False),
        sa.Column('max_order_value_paise', sa.BigInteger(), nullable=False),
        sa.Column('offer_ttl_seconds', sa.Integer(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Create offers (initially without FK to orders to avoid circular dependency)
    op.create_table(
        'offers',
        sa.Column('order_id', sa.UUID(), nullable=True),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('merchant_id', sa.UUID(), nullable=False),
        sa.Column('original_price_paise', sa.BigInteger(), nullable=False),
        sa.Column('offered_price_paise', sa.BigInteger(), nullable=False),
        sa.Column('discount_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('reason_codes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('negotiation_round', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_accepted', sa.Boolean(), nullable=False),
        sa.Column('is_expired', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Create orders (referencing offers)
    op.create_table(
        'orders',
        sa.Column('merchant_id', sa.UUID(), nullable=False),
        sa.Column('product_id', sa.UUID(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('offer_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('unit_price_paise', sa.BigInteger(), nullable=False),
        sa.Column('total_paise', sa.BigInteger(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('razorpay_order_id', sa.String(length=255), nullable=True),
        sa.Column('razorpay_payment_id', sa.String(length=255), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id']),
        sa.ForeignKeyConstraint(['offer_id'], ['offers.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. Add backlink FK from offers.order_id -> orders.id
    op.create_foreign_key('fk_offers_order_id', 'offers', 'orders', ['order_id'], ['id'])

    # 6. Create order_events (audit trail)
    op.create_table(
        'order_events',
        sa.Column('order_id', sa.UUID(), nullable=False),
        sa.Column('actor', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('from_status', sa.String(length=30), nullable=True),
        sa.Column('to_status', sa.String(length=30), nullable=True),
        sa.Column('detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result', sa.String(length=10), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_order_events_order_id'), 'order_events', ['order_id'], unique=False)


def downgrade() -> None:
    op.drop_constraint('fk_offers_order_id', 'offers', type_='foreignkey')
    op.drop_index(op.f('ix_order_events_order_id'), table_name='order_events')
    op.drop_table('order_events')
    op.drop_table('orders')
    op.drop_table('offers')
    op.drop_table('policies')
    op.drop_table('inventory')
    op.drop_index(op.f('ix_webhook_events_razorpay_event_id'), table_name='webhook_events')
    op.drop_table('webhook_events')
    op.drop_table('products')
    op.drop_table('merchants')
