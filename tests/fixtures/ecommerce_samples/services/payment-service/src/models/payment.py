"""Payment domain model.

Represents payment transactions in the e-commerce system.

Referenced by:
- payment_service.py: Payment processing logic
- OrderService.java: Order-payment relationship
- PaymentForm.tsx: Frontend payment submission

See payment-gateway.md for payment flow documentation.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


class PaymentStatus(Enum):
    """Payment status enum."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DECLINED = "declined"
    FAILED = "failed"
    REFUNDED = "refunded"
    ERROR = "error"


@dataclass
class Payment:
    """
    Payment domain model.

    Attributes:
        id: Payment unique identifier
        order_id: Reference to Order entity (Java)
        amount: Payment amount in USD
        payment_method: Payment method (CREDIT_CARD, PAYPAL)
        transaction_id: External gateway transaction ID
        status: Current payment status
        error_message: Error message if failed
        refund_transaction_id: Refund transaction ID if refunded
        refund_reason: Reason for refund
        created_at: Payment creation timestamp
        updated_at: Last update timestamp
    """

    id: UUID
    order_id: UUID
    amount: Decimal
    payment_method: str
    transaction_id: str | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    error_message: str | None = None
    refund_transaction_id: str | None = None
    refund_reason: str | None = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if self.id is None:
            self.id = uuid4()
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def is_successful(self) -> bool:
        """Check if payment was successful."""
        return self.status == PaymentStatus.COMPLETED

    def can_be_refunded(self) -> bool:
        """Check if payment can be refunded."""
        return self.status == PaymentStatus.COMPLETED

    def mark_as_completed(self, transaction_id: str) -> None:
        """Mark payment as completed with transaction ID."""
        self.status = PaymentStatus.COMPLETED
        self.transaction_id = transaction_id
        self.updated_at = datetime.now()

    def mark_as_declined(self, error_message: str) -> None:
        """Mark payment as declined with error message."""
        self.status = PaymentStatus.DECLINED
        self.error_message = error_message
        self.updated_at = datetime.now()

    def mark_as_refunded(self, refund_transaction_id: str, reason: str) -> None:
        """Mark payment as refunded."""
        self.status = PaymentStatus.REFUNDED
        self.refund_transaction_id = refund_transaction_id
        self.refund_reason = reason
        self.updated_at = datetime.now()


@dataclass
class Transaction:
    """Transaction record from payment gateway."""

    id: str
    status: PaymentStatus
    amount: Decimal
    created_at: datetime
