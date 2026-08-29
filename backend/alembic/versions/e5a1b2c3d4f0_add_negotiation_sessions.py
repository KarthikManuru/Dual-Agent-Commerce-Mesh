"""add_negotiation_sessions

Revision ID: e5a1b2c3d4f0
Revises: d8d996bf4502
Create Date: 2026-08-25 19:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5a1b2c3d4f0'
down_revision: Union[str, None] = 'd8d996bf4502'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'negotiation_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('merchant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('merchants.id'), nullable=False),
        sa.Column('buyer_name', sa.String(length=100), nullable=False),
        sa.Column('buyer_strategy', sa.String(length=50), nullable=False),
        sa.Column('buyer_budget_paise', sa.BigInteger(), nullable=False),
        sa.Column('outcome', sa.String(length=30), nullable=False),
        sa.Column('agreed_price_paise', sa.BigInteger(), nullable=True),
        sa.Column('discount_achieved_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('bundle_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('total_rounds', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=True),
        sa.Column('messages', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('negotiation_sessions')
