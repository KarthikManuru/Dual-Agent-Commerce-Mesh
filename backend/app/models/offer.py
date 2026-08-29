import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, BigInteger, Boolean, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class Offer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A time-bounded price offer from the merchant agent.
    Must pass FinancialActionGuard validation before becoming an order.
    expires_at is enforced at checkout — stale offers are rejected.
    """

    __tablename__ = "offers"

    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orders.id"),
        nullable=True,  # offer may be created before order
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=False,
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("merchants.id"),
        nullable=False,
    )
    original_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    offered_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    reason_codes: Mapped[dict] = mapped_column(JSONB, nullable=True, default=list)
    negotiation_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<Offer {self.id} ₹{self.offered_price_paise / 100:.2f} accepted={self.is_accepted}>"
