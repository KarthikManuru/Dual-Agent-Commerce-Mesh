from sqlalchemy import String, BigInteger, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Product catalog — prices stored in paise (₹27.99 = 2799)."""

    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    price_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cost_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=True)
    tags: Mapped[dict] = mapped_column(JSONB, nullable=True, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    inventory = relationship("Inventory", back_populates="product", uselist=False, lazy="joined")

    def __repr__(self) -> str:
        return f"<Product {self.name} ₹{self.price_paise / 100:.2f}>"
