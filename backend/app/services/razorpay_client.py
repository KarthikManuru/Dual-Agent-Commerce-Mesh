import hmac
import hashlib
import razorpay
from typing import Any
from app.config import get_settings


class RazorpayService:
    """Service wrapper for interacting with Razorpay Test Mode APIs and verifying signatures."""

    @property
    def client(self):
        settings = get_settings()
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            return None
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        client.set_app_details({"title": "Dual-Agent-Commerce-Mesh", "version": "1.0.0"})
        return client

    def create_order(
        self,
        amount_paise: int,
        currency: str = "INR",
        receipt: str = "",
        notes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a real Razorpay Order.
        Amount must be in paise (e.g. 100 paise = ₹1).
        """
        if not self.client:
            raise ValueError("Razorpay client is not initialized. Please verify RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.")

        payload = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "notes": notes or {},
            "payment_capture": 1,  # auto-capture on authorization
        }
        return self.client.order.create(data=payload)

    def verify_webhook_signature(self, body_bytes: bytes, signature: str) -> bool:
        """
        Verify the X-Razorpay-Signature header against the raw body bytes and webhook secret.
        Uses HMAC-SHA256.
        """
        settings = get_settings()
        secret = settings.RAZORPAY_WEBHOOK_SECRET
        if not secret:
            raise ValueError("RAZORPAY_WEBHOOK_SECRET is not configured.")

        expected_signature = hmac.new(
            key=secret.encode("utf-8"),
            msg=body_bytes,
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """
        Verify payment signature received from frontend Checkout.js callback.
        """
        settings = get_settings()
        secret = settings.RAZORPAY_KEY_SECRET
        if not secret:
            raise ValueError("RAZORPAY_KEY_SECRET is not configured.")

        msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
        expected_signature = hmac.new(
            key=secret.encode("utf-8"),
            msg=msg,
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, razorpay_signature)


razorpay_service = RazorpayService()
