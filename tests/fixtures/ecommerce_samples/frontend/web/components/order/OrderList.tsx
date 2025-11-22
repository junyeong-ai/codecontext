/**
 * OrderList component displays customer's order history.
 *
 * Dependencies:
 * - orderService.ts: Fetches orders from API
 * - OrderStatus.tsx: Displays order status
 * - Order.java: Server-side order entity
 * - OrderController.java: API endpoints
 *
 * API: GET /api/v1/orders?customerId={id}
 * See api-design.md for API specification.
 */

import React, { useEffect, useState } from 'react';
import { orderService } from '../../services/orderService';
import { OrderStatus } from './OrderStatus';

interface Order {
  id: string;
  status: string;
  totalAmount: number;
  items: OrderItem[];
  createdAt: string;
}

interface OrderItem {
  productId: string;
  productName: string;
  quantity: number;
  price: number;
}

interface OrderListProps {
  customerId: string;
}

/**
 * OrderList component.
 *
 * Fetches customer orders via orderService.ts which calls
 * OrderController.listOrders() endpoint.
 */
export const OrderList: React.FC<OrderListProps> = ({ customerId }) => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadOrders();
  }, [customerId]);

  /**
   * Load orders from API.
   * Calls orderService.getCustomerOrders() which invokes:
   * - orderService.ts TypeScript client
   * - OrderController.listOrders() Java endpoint
   * - OrderService.getCustomerOrders() Java service
   */
  const loadOrders = async () => {
    try {
      setLoading(true);
      const customerOrders = await orderService.getCustomerOrders(customerId);
      setOrders(customerOrders);
    } catch (err) {
      setError('Failed to load orders');
      console.error('Error loading orders:', err);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Calculate order line total.
   * Similar logic to OrderItem.getLineTotal() in Java.
   */
  const calculateLineTotal = (item: OrderItem): number => {
    return item.price * item.quantity;
  };

  if (loading) {
    return <div className="loading">Loading orders...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (orders.length === 0) {
    return (
      <div className="empty-state">
        <h3>No orders yet</h3>
        <p>Start shopping to see your orders here!</p>
      </div>
    );
  }

  return (
    <div className="order-list">
      <h2>Your Orders</h2>
      {orders.map(order => (
        <div key={order.id} className="order-card">
          <div className="order-header">
            <div className="order-id">Order #{order.id.slice(0, 8)}</div>
            <OrderStatus status={order.status} />
          </div>

          <div className="order-items">
            {order.items.map((item, index) => (
              <div key={index} className="order-item">
                <div className="item-name">{item.productName}</div>
                <div className="item-details">
                  Qty: {item.quantity} × ${item.price.toFixed(2)}
                </div>
                <div className="item-total">
                  ${calculateLineTotal(item).toFixed(2)}
                </div>
              </div>
            ))}
          </div>

          <div className="order-footer">
            <div className="order-date">
              {new Date(order.createdAt).toLocaleDateString()}
            </div>
            <div className="order-total">
              Total: ${order.totalAmount.toFixed(2)}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
