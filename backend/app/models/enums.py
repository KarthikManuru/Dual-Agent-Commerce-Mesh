import enum
from typing import Optional


class OrderStatus(str, enum.Enum):
    """Full order state machine — 15 states including 2 terminal failure states."""

    DISCOVERED = "DISCOVERED"
    SELECTED = "SELECTED"
    OFFER_CREATED = "OFFER_CREATED"
    NEGOTIATING = "NEGOTIATING"
    OFFER_ACCEPTED = "OFFER_ACCEPTED"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    CONSENT_RECEIVED = "CONSENT_RECEIVED"
    ORDER_CREATED = "ORDER_CREATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_AUTHORIZED = "PAYMENT_AUTHORIZED"
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    ORDER_PAID = "ORDER_PAID"
    FULFILLED = "FULFILLED"
    # Terminal failure states
    PAYMENT_FAILED = "PAYMENT_FAILED"
    CANCELLED = "CANCELLED"


# Valid state transitions: from_status -> list of allowed to_statuses
ORDER_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.DISCOVERED: [OrderStatus.SELECTED, OrderStatus.CANCELLED],
    OrderStatus.SELECTED: [OrderStatus.OFFER_CREATED, OrderStatus.CANCELLED],
    OrderStatus.OFFER_CREATED: [OrderStatus.NEGOTIATING, OrderStatus.OFFER_ACCEPTED, OrderStatus.CANCELLED],
    OrderStatus.NEGOTIATING: [OrderStatus.OFFER_CREATED, OrderStatus.OFFER_ACCEPTED, OrderStatus.CANCELLED],
    OrderStatus.OFFER_ACCEPTED: [OrderStatus.CONSENT_REQUIRED, OrderStatus.CANCELLED],
    OrderStatus.CONSENT_REQUIRED: [OrderStatus.CONSENT_RECEIVED, OrderStatus.CANCELLED],
    OrderStatus.CONSENT_RECEIVED: [OrderStatus.ORDER_CREATED, OrderStatus.CANCELLED],
    OrderStatus.ORDER_CREATED: [OrderStatus.PAYMENT_PENDING, OrderStatus.CANCELLED],
    OrderStatus.PAYMENT_PENDING: [OrderStatus.PAYMENT_AUTHORIZED, OrderStatus.PAYMENT_FAILED, OrderStatus.CANCELLED],
    OrderStatus.PAYMENT_AUTHORIZED: [OrderStatus.PAYMENT_CAPTURED, OrderStatus.PAYMENT_FAILED, OrderStatus.CANCELLED],
    OrderStatus.PAYMENT_CAPTURED: [OrderStatus.ORDER_PAID],
    OrderStatus.ORDER_PAID: [OrderStatus.FULFILLED],
    # Terminal states — no transitions out
    OrderStatus.FULFILLED: [],
    OrderStatus.PAYMENT_FAILED: [],
    OrderStatus.CANCELLED: [],
}


class IllegalTransitionError(Exception):
    """Raised when an invalid order state transition is attempted."""

    def __init__(self, from_status: OrderStatus, to_status: OrderStatus):
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Illegal order transition: {from_status.value} -> {to_status.value}. "
            f"Allowed transitions from {from_status.value}: "
            f"{[s.value for s in ORDER_TRANSITIONS.get(from_status, [])]}"
        )


def validate_transition(from_status: OrderStatus, to_status: OrderStatus) -> None:
    """
    Validate that a state transition is allowed.
    Raises IllegalTransitionError if the transition is not in ORDER_TRANSITIONS.
    """
    allowed = ORDER_TRANSITIONS.get(from_status, [])
    if to_status not in allowed:
        raise IllegalTransitionError(from_status, to_status)


# Linear progression order for idempotency checks during payment flow.
# Used to determine if an order has already moved past a target state,
# so that concurrent /verify and webhook handlers can no-op gracefully.
_PAYMENT_PROGRESSION: list[OrderStatus] = [
    OrderStatus.PAYMENT_PENDING,
    OrderStatus.PAYMENT_AUTHORIZED,
    OrderStatus.PAYMENT_CAPTURED,
    OrderStatus.ORDER_PAID,
    OrderStatus.FULFILLED,
]


def is_at_or_past(current: OrderStatus, target: OrderStatus) -> bool:
    """
    Check if current status is at or past the target in the payment progression.
    Returns True if the order has already reached or passed the target state.
    Returns False if either status is not in the payment progression (e.g. CANCELLED).
    """
    try:
        current_idx = _PAYMENT_PROGRESSION.index(current)
        target_idx = _PAYMENT_PROGRESSION.index(target)
        return current_idx >= target_idx
    except ValueError:
        return False

