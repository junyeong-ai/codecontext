"""Payment Gateway Abstraction Layer.

Provides abstraction for multiple payment gateway integrations.

Implementations:
- StripePaymentGateway: Stripe credit card processing
- PayPalPaymentGateway: PayPal digital wallet

Referenced by payment_service.py for payment processing.
See payment-gateway.md documentation for integration patterns.
"""

from datetime import datetime
from decimal import Decimal
from typing import Protocol

import paypalrestsdk
import stripe


class PaymentGateway(Protocol):
    """
    Abstract payment gateway interface.

    All payment gateway implementations IMPLEMENT this protocol.
    """

    def charge(self, amount: Decimal, token: str) -> "Transaction":
        """Process a payment charge."""
        ...

    def refund(self, transaction_id: str, amount: Decimal) -> "Transaction":
        """Process a refund."""
        ...

    def verify_card(self, token: str) -> bool:
        """Verify card validity."""
        ...


class StripePaymentGateway:
    """
    Stripe payment gateway implementation.

    IMPLEMENTS PaymentGateway protocol.
    CALLED_BY PaymentService for credit card processing.

    Configuration:
    - API key from payment.config.js
    - Webhook secret for event handling
    """

    def __init__(self, api_key: str):
        """
        Initialize Stripe gateway.

        Args:
            api_key: Stripe API secret key
        """
        self.client = stripe.Client(api_key)

    def charge(self, amount: Decimal, token: str) -> "Transaction":
        """
        Process Stripe charge.

        Args:
            amount: Amount to charge in dollars
            token: Stripe card token from frontend

        Returns:
            Transaction object with charge details

        Raises:
            PaymentDeclinedException: Card declined
            PaymentGatewayException: Stripe API error
        """
        try:
            stripe_charge = self.client.charges.create(
                amount=int(amount * 100),  # Convert to cents
                currency="usd",
                source=token,
                description="E-commerce purchase",
            )

            return Transaction(
                id=stripe_charge.id,
                status=self._map_status(stripe_charge.status),
                amount=Decimal(stripe_charge.amount) / 100,
                created_at=datetime.fromtimestamp(stripe_charge.created),
            )

        except stripe.error.CardError as e:
            # Card was declined
            raise PaymentDeclinedException(e.user_message)

        except stripe.error.StripeError as e:
            # Stripe API error
            raise PaymentGatewayException(str(e))

    def refund(self, transaction_id: str, amount: Decimal) -> "Transaction":
        """
        Process Stripe refund.

        Args:
            transaction_id: Original charge ID
            amount: Amount to refund

        Returns:
            Transaction object with refund details
        """
        refund = self.client.refunds.create(charge=transaction_id, amount=int(amount * 100))

        return Transaction(
            id=refund.id,
            status=TransactionStatus.REFUNDED,
            amount=Decimal(refund.amount) / 100,
            created_at=datetime.fromtimestamp(refund.created),
        )

    def verify_card(self, token: str) -> bool:
        """Verify card token is valid."""
        try:
            self.client.tokens.retrieve(token)
            return True
        except stripe.error.InvalidRequestError:
            return False

    def _map_status(self, stripe_status: str) -> "TransactionStatus":
        """Map Stripe status to internal status."""
        mapping = {
            "succeeded": TransactionStatus.COMPLETED,
            "pending": TransactionStatus.PENDING,
            "failed": TransactionStatus.FAILED,
        }
        return mapping.get(stripe_status, TransactionStatus.UNKNOWN)


class PayPalPaymentGateway:
    """
    PayPal payment gateway implementation.

    IMPLEMENTS PaymentGateway protocol.
    CALLED_BY PaymentService for PayPal payments.
    """

    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize PayPal gateway.

        Args:
            client_id: PayPal API client ID
            client_secret: PayPal API client secret
        """
        self.client = paypalrestsdk.Api(
            {"mode": "live", "client_id": client_id, "client_secret": client_secret}
        )

    def charge(self, amount: Decimal, token: str) -> "Transaction":
        """
        Process PayPal payment.

        Args:
            amount: Amount to charge
            token: PayPal payment token

        Returns:
            Transaction object with payment details
        """
        payment = paypalrestsdk.Payment(
            {
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "transactions": [{"amount": {"total": str(amount), "currency": "USD"}}],
                "redirect_urls": {
                    "return_url": "https://example.com/payment/success",
                    "cancel_url": "https://example.com/payment/cancel",
                },
            }
        )

        if payment.create():
            return Transaction(
                id=payment.id,
                status=TransactionStatus.PENDING,
                amount=amount,
                created_at=datetime.now(),
            )
        else:
            raise PaymentGatewayException(payment.error)

    def refund(self, transaction_id: str, amount: Decimal) -> "Transaction":
        """Process PayPal refund."""
        sale = paypalrestsdk.Sale.find(transaction_id)
        refund = sale.refund({"amount": {"total": str(amount), "currency": "USD"}})

        if refund.success():
            return Transaction(
                id=refund.id,
                status=TransactionStatus.REFUNDED,
                amount=amount,
                created_at=datetime.now(),
            )
        else:
            raise PaymentGatewayException(refund.error)

    def verify_card(self, token: str) -> bool:
        """PayPal doesn't use card tokens directly."""
        return True
