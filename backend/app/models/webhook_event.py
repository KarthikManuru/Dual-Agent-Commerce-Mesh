from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class WebhookEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Razorpay webhook event deduplication table.
    Keyed by razorpay_event_id — if an event_id is already in this table,
    the webhook handler returns 200 immediately without reprocessing.
    """

    __tablename__ = "webhook_events"

    razorpay_event_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<WebhookEvent {self.razorpay_event_id} type={self.event_type}>"
