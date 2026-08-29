import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class OrderEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Immutable audit log for every action on an order.
    Every FinancialActionGuard decision, status change, and agent action
    is recorded here with actor, action, and result.
    """

    __tablename__ = "order_events"

    order_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # BUYER_AGENT, MERCHANT_AGENT, SYSTEM, GUARD, RAZORPAY
    action: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # STATUS_CHANGE, DISCOUNT_APPLIED, PAYMENT_RECEIVED, etc.
    from_status: Mapped[str] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=True)
    detail: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)
    result: Mapped[str] = mapped_column(
        String(10), nullable=False, default="INFO"
    )  # ALLOW, DENY, INFO
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    current_hash: Mapped[str] = mapped_column(String(64), nullable=True)

    # Relationships
    order = relationship("Order", back_populates="events")

    def __repr__(self) -> str:
        return f"<OrderEvent {self.action} {self.result} order={self.order_id}>"
