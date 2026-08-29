import uuid
from decimal import Decimal
from sqlalchemy import Integer, BigInteger, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class Policy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Merchant-level business policy constraints for the FinancialActionGuard."""

    __tablename__ = "policies"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
    )
    max_discount_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("15.00"), nullable=False
    )
    min_margin_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("10.00"), nullable=False
    )
    max_negotiation_rounds: Mapped[int] = mapped_column(
        Integer, default=2, nullable=False
    )
    max_order_value_paise: Mapped[int] = mapped_column(
        BigInteger, default=50_000_00, nullable=False  # ₹50,000
    )
    offer_ttl_seconds: Mapped[int] = mapped_column(
        Integer, default=600, nullable=False  # 10 minutes
    )

    def __repr__(self) -> str:
        return f"<Policy merchant={self.merchant_id} max_discount={self.max_discount_pct}%>"
