import uuid
from decimal import Decimal
from sqlalchemy import String, Integer, BigInteger, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class NegotiationSessionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Persisted record of an autonomous dual-agent negotiation session.
    Stores full message transcripts with reasoning source stamps.
    """

    __tablename__ = "negotiation_sessions"

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
    buyer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    buyer_strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    buyer_budget_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)

    outcome: Mapped[str] = mapped_column(String(30), nullable=False)  # ACCEPTED, REJECTED, GUARD_BLOCKED
    agreed_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=True)
    discount_achieved_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    bundle_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    total_rounds: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orders.id"),
        nullable=True,
    )

    messages: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    product = relationship("Product", lazy="joined")
    order = relationship("Order", lazy="joined")

    def __repr__(self) -> str:
        return f"<NegotiationSession {self.id} outcome={self.outcome} rounds={self.total_rounds}>"
