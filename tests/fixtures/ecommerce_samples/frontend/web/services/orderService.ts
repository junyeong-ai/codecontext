/**
 * Order Service - TypeScript client for order API.
 *
 * Provides type-safe interface to OrderController.java endpoints.
 *
 * API Endpoints:
 * - POST /api/v1/orders - Create order
 * - GET /api/v1/orders/{id} - Get order
 * - GET /api/v1/orders?customerId={id} - List orders
 *
 * See api-design.md for complete API specification.
 *
 * Called by:
 * - CheckoutFlow.tsx: Order creation
 * - OrderList.tsx: Fetch order history
 * - OrderStatus.tsx: Track order status
 */

import { api } from '../config/api';

interface CreateOrderRequest {
  customerId: string;
  items: OrderItemRequest[];
  shippingAddress: ShippingAddress;
  paymentMethod: string;
  cardToken: string;
}

interface OrderItemRequest {
  productId: string;
  productName: string;
  quantity: number;
  price: number;
}

interface ShippingAddress {
  street: string;
  city: string;
  state: string;
  zipCode: string;
  country: string;
}

interface OrderResponse {
  id: string;
  customerId: string;
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

/**
 * OrderService client class.
 *
 * Communicates with OrderController.java REST API.
 */
class OrderService {
  private readonly apiUrl = '/api/v1/orders';

  /**
   * Create new order.
   *
   * Calls OrderController.createOrder() which:
   * 1. Validates inventory via InventoryService.py
   * 2. Processes payment via PaymentService.py
   * 3. Creates order entity in Order.java
   * 4. Returns order response
   *
   * See order-flow.md for complete flow.
   */
  async createOrder(request: CreateOrderRequest): Promise<OrderResponse> {
    const response = await fetch(this.apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAuthToken()}`
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new OrderError(error.message || 'Failed to create order');
    }

    return await response.json();
  }

  /**
   * Get order by ID.
   *
   * Calls OrderController.getOrder() → OrderService.getOrder()
   */
  async getOrder(orderId: string): Promise<OrderResponse> {
    const response = await fetch(`${this.apiUrl}/${orderId}`, {
      headers: {
        'Authorization': `Bearer ${this.getAuthToken()}`
      }
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new OrderNotFoundError(`Order ${orderId} not found`);
      }
      throw new OrderError('Failed to fetch order');
    }

    return await response.json();
  }

  /**
   * Get customer's order history.
   *
   * Calls OrderController.listOrders() → OrderService.getCustomerOrders()
   * Used by OrderList.tsx to display order history.
   */
  async getCustomerOrders(customerId: string): Promise<OrderResponse[]> {
    const response = await fetch(
      `${this.apiUrl}?customerId=${customerId}`,
      {
        headers: {
          'Authorization': `Bearer ${this.getAuthToken()}`
        }
      }
    );

    if (!response.ok) {
      throw new OrderError('Failed to fetch orders');
    }

    return await response.json();
  }

  /**
   * Cancel order.
   *
   * Calls OrderController.cancelOrder() → OrderService.cancelOrder()
   */
  async cancelOrder(orderId: string, reason: string): Promise<void> {
    const response = await fetch(`${this.apiUrl}/${orderId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAuthToken()}`
      },
      body: JSON.stringify({ reason })
    });

    if (!response.ok) {
      throw new OrderError('Failed to cancel order');
    }
  }

  /**
   * Get auth token from storage.
   */
  private getAuthToken(): string {
    return localStorage.getItem('auth_token') || '';
  }
}

/**
 * Order error class.
 */
class OrderError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'OrderError';
  }
}

/**
 * Order not found error.
 */
class OrderNotFoundError extends OrderError {
  constructor(message: string) {
    super(message);
    this.name = 'OrderNotFoundError';
  }
}

/**
 * Singleton instance.
 */
export const orderService = new OrderService();
