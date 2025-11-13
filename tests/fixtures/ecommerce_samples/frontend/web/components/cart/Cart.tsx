/**
 * Cart component displays shopping cart with add/remove functionality.
 *
 * Dependencies:
 * - useCart.ts: Cart state management hook
 * - ProductCard.tsx: Product display component
 * - formatPrice.js: Price formatting utility
 *
 * Referenced in:
 * - CheckoutFlow.tsx: Cart review step
 */

import React from 'react';
import { useCart } from '../../hooks/useCart';
import { formatPrice } from '../../utils/formatPrice';

interface CartItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
  imageUrl?: string;
}

/**
 * Shopping cart component.
 *
 * Uses useCart.ts hook for cart state management.
 * Formats prices using formatPrice.js utility.
 */
export const Cart: React.FC = () => {
  const { items, total, updateQuantity, removeItem } = useCart();

  /**
   * Handle quantity change for cart item.
   */
  const handleQuantityChange = (itemId: string, newQuantity: number) => {
    if (newQuantity <= 0) {
      removeItem(itemId);
    } else {
      updateQuantity(itemId, newQuantity);
    }
  };

  /**
   * Calculate line total for cart item.
   * Similar to OrderItem.getLineTotal() in Order.java
   */
  const calculateLineTotal = (item: CartItem): number => {
    return item.price * item.quantity;
  };

  if (items.length === 0) {
    return (
      <div className="cart-empty">
        <h3>Your cart is empty</h3>
        <p>Add some items to get started!</p>
      </div>
    );
  }

  return (
    <div className="cart">
      <h2>Shopping Cart ({items.length} items)</h2>

      <div className="cart-items">
        {items.map(item => (
          <div key={item.id} className="cart-item">
            {item.imageUrl && (
              <img src={item.imageUrl} alt={item.name} className="item-image" />
            )}

            <div className="item-details">
              <h3>{item.name}</h3>
              <div className="item-price">
                {formatPrice(item.price).price}
              </div>
            </div>

            <div className="item-controls">
              <div className="quantity-control">
                <button
                  onClick={() => handleQuantityChange(item.id, item.quantity - 1)}
                  aria-label="Decrease quantity"
                >
                  -
                </button>
                <span className="quantity">{item.quantity}</span>
                <button
                  onClick={() => handleQuantityChange(item.id, item.quantity + 1)}
                  aria-label="Increase quantity"
                >
                  +
                </button>
              </div>

              <div className="item-total">
                {formatPrice(calculateLineTotal(item)).price}
              </div>

              <button
                onClick={() => removeItem(item.id)}
                className="remove-button"
                aria-label="Remove item"
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="cart-summary">
        <div className="summary-line">
          <span>Subtotal:</span>
          <span>{formatPrice(total).price}</span>
        </div>

        <div className="summary-line shipping">
          <span>Shipping:</span>
          <span>{total >= 50 ? 'FREE' : formatPrice(5.99).price}</span>
        </div>

        <div className="summary-line total">
          <span>Total:</span>
          <span>{formatPrice(total >= 50 ? total : total + 5.99).price}</span>
        </div>

        <button
          className="checkout-button"
          onClick={() => window.location.href = '/checkout'}
        >
          Proceed to Checkout
        </button>
      </div>
    </div>
  );
};
