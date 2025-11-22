"""Payment Service - Payment processing orchestration.

This module coordinates payment operations across multiple payment gateways.

Dependencies:
- payment_gateway.py: Gateway abstraction layer
- payment.py: Payment domain model
- transaction.py: Transaction model
- OrderService.java: Calls this service for payment processing

See payment-gateway.md for implementation details.
"""

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Payment service coordinating gateway operations.

    Called by OrderService.java when processing orders.
    CALLS PaymentGateway implementations for actual payment processing.
    """

    def __init__(
        self,
        stripe_gateway: "StripePaymentGateway",
        paypal_gateway: "PayPalPaymentGateway",
        payment_repository: "PaymentRepository",
    ):
        """
        Initialize payment service with gateways.

        Args:
            stripe_gateway: Stripe gateway implementation
            paypal_gateway: PayPal gateway implementation
            payment_repository: Payment data access layer
        """
        self.gateways = {"CREDIT_CARD": stripe_gateway, "PAYPAL": paypal_gateway}
        self.repository = payment_repository
        self.logger = logger

    def process_payment(self, payment_request: "PaymentRequest") -> "PaymentResult":
        """
        Process payment through appropriate gateway.

        Called by OrderService.java when order is confirmed.
        CALLS PaymentGateway.charge() to process actual transaction.

        Args:
            payment_request: Payment request with order details

        Returns:
            PaymentResult with success status and transaction info

        Raises:
            PaymentDeclinedException: Card declined by issuer
            PaymentGatewayException: Gateway error
            UnsupportedPaymentMethodException: Unknown payment method
        """
        # Select gateway
        gateway = self.gateways.get(payment_request.payment_method)
        if not gateway:
            raise UnsupportedPaymentMethodException(
                f"Payment method {payment_request.payment_method} not supported"
            )

        self.logger.info(
            f"Processing payment for order {payment_request.order_id} "
            f"amount ${payment_request.amount}"
        )

        try:
            # Process transaction via gateway
            transaction = gateway.charge(
                amount=payment_request.amount, token=payment_request.card_token
            )

            # Record payment
            payment = Payment(
                order_id=payment_request.order_id,
                amount=payment_request.amount,
                payment_method=payment_request.payment_method,
                transaction_id=transaction.id,
                status=transaction.status,
                created_at=transaction.created_at,
            )
            self.repository.save(payment)

            self.logger.info(f"Payment successful: {payment.id} (transaction: {transaction.id})")

            return PaymentResult(success=True, payment_id=payment.id, transaction_id=transaction.id)

        except PaymentDeclinedException as e:
            # Card declined - record and return failure
            self.logger.warning(f"Payment declined for order {payment_request.order_id}: {e}")

            payment = Payment(
                order_id=payment_request.order_id,
                amount=payment_request.amount,
                payment_method=payment_request.payment_method,
                status=PaymentStatus.DECLINED,
                error_message=str(e),
            )
            self.repository.save(payment)

            return PaymentResult(success=False, error_code="CARD_DECLINED", error_message=str(e))

        except PaymentGatewayException as e:
            # Gateway error - record and return failure
            self.logger.error(f"Payment gateway error for order {payment_request.order_id}: {e}")

            payment = Payment(
                order_id=payment_request.order_id,
                amount=payment_request.amount,
                payment_method=payment_request.payment_method,
                status=PaymentStatus.ERROR,
                error_message=str(e),
            )
            self.repository.save(payment)

            return PaymentResult(success=False, error_code="GATEWAY_ERROR", error_message=str(e))

    def refund_payment(self, payment_id: UUID, reason: str) -> "RefundResult":
        """
        Process refund for existing payment.

        Called by OrderService.java when order is cancelled.
        CALLS PaymentGateway.refund() to process refund transaction.

        Args:
            payment_id: ID of original payment
            reason: Refund reason

        Returns:
            RefundResult with refund transaction info
        """
        payment = self.repository.get(payment_id)

        if payment.status != PaymentStatus.COMPLETED:
            raise InvalidRefundException(f"Cannot refund payment in status {payment.status}")

        gateway = self.gateways.get(payment.payment_method)

        self.logger.info(f"Processing refund for payment {payment_id}: {reason}")

        # Process refund via gateway
        refund_transaction = gateway.refund(
            transaction_id=payment.transaction_id, amount=payment.amount
        )

        # Update payment record
        payment.status = PaymentStatus.REFUNDED
        payment.refund_transaction_id = refund_transaction.id
        payment.refund_reason = reason
        self.repository.save(payment)

        self.logger.info(f"Refund successful: {refund_transaction.id}")

        return RefundResult(success=True, refund_id=refund_transaction.id, amount=payment.amount)

    def get_payment_status(self, payment_id: UUID) -> "PaymentStatus":
        """
        Get current payment status.

        Called from frontend via paymentService.ts

        Args:
            payment_id: Payment ID

        Returns:
            PaymentStatus enum value
        """
        payment = self.repository.get(payment_id)
        return payment.status
