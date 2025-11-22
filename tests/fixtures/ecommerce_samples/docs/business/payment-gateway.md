# Payment Gateway Integration

## Overview

This document describes the payment gateway integration strategy, including supported payment methods, gateway abstraction, and error handling patterns.

## Supported Payment Methods

### Credit Cards
- Visa, MasterCard, American Express, Discover
- Processing via Stripe Gateway
- PCI DSS compliance through tokenization

### Digital Wallets
- PayPal
- Apple Pay
- Google Pay

### Bank Transfer
- ACH (US)
- SEPA (Europe)
- Wire transfer

## Gateway Abstraction Layer

### Architecture

```python
# payment_gateway.py - Gateway abstraction
from abc import ABC, abstractmethod
from typing import Protocol

class PaymentGateway(Protocol):
    """Abstract payment gateway interface."""

    def charge(self, amount: Decimal, token: str) -> Transaction:
        """Process a payment charge."""
        ...

    def refund(self, transaction_id: str, amount: Decimal) -> Transaction:
        """Process a refund."""
        ...

    def verify_card(self, token: str) -> bool:
        """Verify card validity."""
        ...
```

### Stripe Implementation

```python
# payment_gateway.py

class StripePaymentGateway:
    """Stripe payment gateway implementation."""

    def __init__(self, api_key: str):
        self.client = stripe.Client(api_key)

    def charge(self, amount: Decimal, token: str) -> Transaction:
        """Process Stripe charge."""
        try:
            stripe_charge = self.client.charges.create(
                amount=int(amount * 100),  # Convert to cents
                currency='usd',
                source=token,
                description='E-commerce purchase'
            )

            return Transaction(
                id=stripe_charge.id,
                status=self._map_status(stripe_charge.status),
                amount=Decimal(stripe_charge.amount) / 100,
                created_at=datetime.fromtimestamp(stripe_charge.created)
            )
        except stripe.error.CardError as e:
            raise PaymentDeclinedException(e.user_message)
        except stripe.error.StripeError as e:
            raise PaymentGatewayException(str(e))

    def refund(self, transaction_id: str, amount: Decimal) -> Transaction:
        """Process Stripe refund."""
        refund = self.client.refunds.create(
            charge=transaction_id,
            amount=int(amount * 100)
        )

        return Transaction(
            id=refund.id,
            status=TransactionStatus.REFUNDED,
            amount=Decimal(refund.amount) / 100,
            created_at=datetime.fromtimestamp(refund.created)
        )
```

### PayPal Implementation

```python
# payment_gateway.py

class PayPalPaymentGateway:
    """PayPal payment gateway implementation."""

    def __init__(self, client_id: str, client_secret: str):
        self.client = paypalrestsdk.Api({
            'mode': 'live',
            'client_id': client_id,
            'client_secret': client_secret
        })

    def charge(self, amount: Decimal, token: str) -> Transaction:
        """Process PayPal payment."""
        payment = paypalrestsdk.Payment({
            'intent': 'sale',
            'payer': {'payment_method': 'paypal'},
            'transactions': [{
                'amount': {
                    'total': str(amount),
                    'currency': 'USD'
                }
            }],
            'redirect_urls': {
                'return_url': 'https://example.com/payment/success',
                'cancel_url': 'https://example.com/payment/cancel'
            }
        })

        if payment.create():
            return Transaction(
                id=payment.id,
                status=TransactionStatus.PENDING,
                amount=amount
            )
        else:
            raise PaymentGatewayException(payment.error)
```

## Payment Service Integration

### Payment Processing

```python
# payment_service.py - Main orchestrator

class PaymentService:
    """Payment service coordinating gateway operations."""

    def __init__(
        self,
        stripe_gateway: StripePaymentGateway,
        paypal_gateway: PayPalPaymentGateway,
        payment_repository: PaymentRepository
    ):
        self.gateways = {
            PaymentMethod.CREDIT_CARD: stripe_gateway,
            PaymentMethod.PAYPAL: paypal_gateway
        }
        self.repository = payment_repository

    def process_payment(self, request: PaymentRequest) -> PaymentResult:
        """
        Process payment through appropriate gateway.

        Called by OrderService.java when order is confirmed.
        """
        # Select gateway
        gateway = self.gateways.get(request.payment_method)
        if not gateway:
            raise UnsupportedPaymentMethodException(
                request.payment_method
            )

        # Process transaction
        try:
            transaction = gateway.charge(
                amount=request.amount,
                token=request.card_token
            )

            # Record payment
            payment = Payment(
                order_id=request.order_id,
                amount=request.amount,
                payment_method=request.payment_method,
                transaction_id=transaction.id,
                status=transaction.status,
                created_at=transaction.created_at
            )
            self.repository.save(payment)

            return PaymentResult(
                success=True,
                payment_id=payment.id,
                transaction_id=transaction.id
            )

        except PaymentDeclinedException as e:
            # Card declined
            payment = Payment(
                order_id=request.order_id,
                amount=request.amount,
                status=PaymentStatus.DECLINED,
                error_message=str(e)
            )
            self.repository.save(payment)

            return PaymentResult(
                success=False,
                error_code='CARD_DECLINED',
                error_message=str(e)
            )

        except PaymentGatewayException as e:
            # Gateway error
            payment = Payment(
                order_id=request.order_id,
                amount=request.amount,
                status=PaymentStatus.ERROR,
                error_message=str(e)
            )
            self.repository.save(payment)

            return PaymentResult(
                success=False,
                error_code='GATEWAY_ERROR',
                error_message=str(e)
            )
```

## Frontend Integration

### Payment Form Component

```typescript
// PaymentForm.tsx

interface PaymentFormProps {
  amount: number;
  onPaymentComplete: (result: PaymentResult) => void;
}

export const PaymentForm: React.FC<PaymentFormProps> = ({
  amount,
  onPaymentComplete
}) => {
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('CREDIT_CARD');
  const [processing, setProcessing] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setProcessing(true);

    try {
      // Tokenize card via Stripe.js
      const {token} = await stripe.createToken(cardElement);

      // Call payment service
      const result = await paymentService.processPayment({
        amount,
        paymentMethod,
        cardToken: token.id
      });

      onPaymentComplete(result);
    } catch (error) {
      console.error('Payment failed:', error);
      // Show error to user
    } finally {
      setProcessing(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <CardElement options={CARD_ELEMENT_OPTIONS} />
      <button type="submit" disabled={processing}>
        {processing ? 'Processing...' : `Pay $${amount}`}
      </button>
    </form>
  );
};
```

### Payment Service Client

```typescript
// paymentService.ts

export class PaymentService {
  private apiUrl = '/api/v1/payments';

  async processPayment(request: PaymentRequest): Promise<PaymentResult> {
    const response = await fetch(this.apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getAuthToken()}`
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      throw new PaymentError('Payment processing failed');
    }

    return await response.json();
  }

  async getPaymentStatus(paymentId: string): Promise<PaymentStatus> {
    const response = await fetch(`${this.apiUrl}/${paymentId}`);
    return await response.json();
  }
}

export const paymentService = new PaymentService();
```

## Error Handling

### Retry Strategy

```python
# payment_service.py

def process_payment_with_retry(
    request: PaymentRequest,
    max_retries: int = 3
) -> PaymentResult:
    """Process payment with exponential backoff retry."""

    for attempt in range(max_retries):
        try:
            return process_payment(request)
        except PaymentGatewayException as e:
            if attempt == max_retries - 1:
                raise
            # Exponential backoff: 1s, 2s, 4s
            time.sleep(2 ** attempt)
```

### Error Codes

| Code | Description | Action |
|------|-------------|--------|
| `CARD_DECLINED` | Card declined by issuer | Try different card |
| `INSUFFICIENT_FUNDS` | Not enough balance | Try different card |
| `EXPIRED_CARD` | Card expired | Update card |
| `INVALID_CARD` | Invalid card number | Check card details |
| `GATEWAY_ERROR` | Gateway unavailable | Retry later |
| `FRAUD_DETECTED` | Suspicious transaction | Contact support |

## Webhook Handling

### Stripe Webhooks

```python
# payment_service.py

def handle_stripe_webhook(event: StripeEvent) -> None:
    """Handle Stripe webhook events."""

    if event.type == 'charge.succeeded':
        payment = payment_repository.get_by_transaction_id(
            event.data.object.id
        )
        payment.status = PaymentStatus.COMPLETED
        payment_repository.save(payment)

        # Notify OrderService
        order_service.on_payment_completed(payment.order_id)

    elif event.type == 'charge.failed':
        payment = payment_repository.get_by_transaction_id(
            event.data.object.id
        )
        payment.status = PaymentStatus.FAILED
        payment_repository.save(payment)

        # Notify OrderService
        order_service.on_payment_failed(payment.order_id)
```

## Configuration

### Payment Gateway Config

```javascript
// payment.config.js

export const paymentConfig = {
  stripe: {
    publicKey: process.env.STRIPE_PUBLIC_KEY,
    secretKey: process.env.STRIPE_SECRET_KEY,
    webhookSecret: process.env.STRIPE_WEBHOOK_SECRET
  },
  paypal: {
    clientId: process.env.PAYPAL_CLIENT_ID,
    clientSecret: process.env.PAYPAL_CLIENT_SECRET,
    mode: process.env.PAYPAL_MODE || 'sandbox'
  },
  retryAttempts: 3,
  retryDelay: 1000, // milliseconds
  timeout: 30000 // 30 seconds
};
```

## Security

### PCI Compliance
- Never store raw card numbers
- Use tokenization for all transactions
- Encrypt sensitive data at rest
- Use HTTPS for all API calls

### Fraud Detection
- Velocity checks (max transactions per hour)
- Address verification (AVS)
- Card verification value (CVV) checks
- 3D Secure authentication

## Monitoring

### Metrics
- Payment success rate (target: >98%)
- Average processing time (target: <2s)
- Decline rate by reason
- Gateway uptime

### Alerts
- Payment success rate drops below 95%
- Gateway response time >5s
- High decline rate (>10%)

## Related Code

- Gateway abstraction: `payment_gateway.py`
- Payment service: `payment_service.py`
- Payment models: `payment.py`, `transaction.py`
- Frontend components: `PaymentForm.tsx`
- Configuration: `payment.config.js`
- Order integration: `OrderService.java`
