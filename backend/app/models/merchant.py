from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class Merchant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Merchant account — linked to Razorpay credentials in Phase 2."""

    __tablename__ = "merchants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    razorpay_key_id: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Merchant {self.name}>"
