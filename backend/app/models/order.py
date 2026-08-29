import uuid
from sqlalchemy import String, Integer, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import OrderStatus


class Order(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Order entity — tracks the full lifecycle from discovery to fulfillment.
    Status transitions are enforced by the enum transition table.
    """

    __tablename__ = "orders"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("merchants.id"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    offer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("offers.id"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default=OrderStatus.DISCOVERED.value,
        nullable=False,
    )
    unit_price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    # Razorpay fields — populated in Phase 2
    razorpay_order_id: Mapped[str] = mapped_column(String(255), nullable=True)
    razorpay_payment_id: Mapped[str] = mapped_column(String(255), nullable=True)

    # Relationships
    events = relationship("OrderEvent", back_populates="order", lazy="selectin", order_by="OrderEvent.created_at")
    product = relationship("Product", lazy="joined")

    def __repr__(self) -> str:
        return f"<Order {self.id} status={self.status} total=₹{self.total_paise / 100:.2f}>"
