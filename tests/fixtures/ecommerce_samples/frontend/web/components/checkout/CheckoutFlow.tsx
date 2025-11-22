/**
 * CheckoutFlow component manages multi-step checkout process.
 *
 * Checkout Steps:
 * 1. Review cart items
 * 2. Enter shipping address
 * 3. Select payment method
 * 4. Confirm and place order
 *
 * Dependencies:
 * - Cart.tsx: Shopping cart component
 * - PaymentForm.tsx: Payment input component
 * - orderService.ts: Order creation API client
 * - paymentService.ts: Payment processing client
 * - OrderController.java: Server-side order API
 * - PaymentService.py: Server-side payment processing
 *
 * References:
 * - order-flow.md: Order processing documentation
 * - payment-gateway.md: Payment integration
 */

import React, { useState } from 'react';
import { useCart } from '../../hooks/useCart';
import { Cart } from '../cart/Cart';
import { PaymentForm } from './PaymentForm';
import { orderService } from '../../services/orderService';
import { formatPrice } from '../../utils/formatPrice';

interface CheckoutStep {
  name: string;
  component: React.ReactNode;
}

interface ShippingAddress {
  street: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
}

/**
 * CheckoutFlow component.
 *
 * Orchestrates the checkout process:
 * 1. Cart review
 * 2. Shipping info
 * 3. Payment processing via PaymentForm.tsx
 * 4. Order creation via orderService.ts → OrderController.java
 */
export const CheckoutFlow: React.FC = () => {
  const { items, total, clearCart } = useCart();
  const [currentStep, setCurrentStep] = useState(0);
  const [shippingAddress, setShippingAddress] = useState<ShippingAddress | null>(null);
  const [processing, setProcessing] = useState(false);
  const [orderId, setOrderId] = useState<string | null>(null);

  /**
   * Handle order submission.
   *
   * Flow:
   * 1. Calls orderService.createOrder() (TypeScript)
   * 2. → OrderController.createOrder() (Java)
   * 3. → OrderService.processOrder() (Java)
   * 4. → PaymentService.processPayment() (Python)
   * 5. → InventoryService.reserveStock() (Python)
   *
   * See order-flow.md for complete flow.
   */
  const handlePlaceOrder = async (paymentMethod: string, cardToken: string) => {
    setProcessing(true);

    try {
      // Create order via API
      const order = await orderService.createOrder({
        customerId: getUserId(),
        items: items.map(item => ({
          productId: item.id,
          productName: item.name,
          quantity: item.quantity,
          price: item.price
        })),
        shippingAddress: shippingAddress!,
        paymentMethod,
        cardToken
      });

      // Order created successfully
      setOrderId(order.id);
      clearCart();
      setCurrentStep(3); // Show confirmation

      console.log(`Order created: ${order.id}`);
    } catch (error) {
      console.error('Order creation failed:', error);
      alert('Failed to place order. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  /**
   * Calculate shipping cost using calculateShipping.js utility.
   */
  const calculateShippingCost = (): number => {
    // Would call calculateShipping.js for actual calculation
    return total >= 50 ? 0 : 5.99; // Free shipping over $50
  };

  const shippingCost = calculateShippingCost();
  const orderTotal = total + shippingCost;

  const steps: CheckoutStep[] = [
    {
      name: 'Review Cart',
      component: (
        <div className="checkout-step">
          <h2>Review Your Order</h2>
          <Cart />
          <button
            onClick={() => setCurrentStep(1)}
            disabled={items.length === 0}
          >
            Continue to Shipping
          </button>
        </div>
      )
    },
    {
      name: 'Shipping',
      component: (
        <div className="checkout-step">
          <h2>Shipping Address</h2>
          <ShippingAddressForm
            onSubmit={(address) => {
              setShippingAddress(address);
              setCurrentStep(2);
            }}
          />
        </div>
      )
    },
    {
      name: 'Payment',
      component: (
        <div className="checkout-step">
          <h2>Payment Information</h2>

          <div className="order-summary">
            <div>Subtotal: {formatPrice(total).price}</div>
            <div>
              Shipping: {shippingCost === 0 ? 'FREE' : formatPrice(shippingCost).price}
            </div>
            <div className="total">
              Total: {formatPrice(orderTotal).price}
            </div>
          </div>

          <PaymentForm
            amount={orderTotal}
            onPaymentComplete={handlePlaceOrder}
            processing={processing}
          />
        </div>
      )
    },
    {
      name: 'Confirmation',
      component: (
        <div className="checkout-step">
          <h2>Order Confirmed!</h2>
          <div className="success-message">
            <p>Thank you for your order!</p>
            <p>Order ID: {orderId}</p>
            <p>You will receive a confirmation email shortly.</p>
          </div>
          <button onClick={() => window.location.href = '/orders'}>
            View Orders
          </button>
        </div>
      )
    }
  ];

  return (
    <div className="checkout-flow">
      <div className="checkout-steps">
        {steps.map((step, index) => (
          <div
            key={index}
            className={`step ${index === currentStep ? 'active' : ''} ${index < currentStep ? 'completed' : ''}`}
          >
            {step.name}
          </div>
        ))}
      </div>

      <div className="checkout-content">
        {steps[currentStep].component}
      </div>
    </div>
  );
};

const getUserId = (): string => {
  // Would get from auth context
  return 'current-user-id';
};

const ShippingAddressForm: React.FC<{
  onSubmit: (address: ShippingAddress) => void;
}> = ({ onSubmit }) => {
  // Form implementation
  return <div>Shipping form...</div>;
};
