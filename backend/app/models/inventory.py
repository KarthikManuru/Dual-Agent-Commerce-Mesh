import uuid
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class Inventory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Inventory tracking per product. Reserved units are held during payment windows."""

    __tablename__ = "inventory"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    total_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="inventory")

    @property
    def available(self) -> int:
        """Available stock = total - reserved."""
        return self.total_stock - self.reserved

    def __repr__(self) -> str:
        return f"<Inventory product={self.product_id} available={self.available}/{self.total_stock}>"
