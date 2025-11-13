package com.ecommerce.order.controller;

import com.ecommerce.order.domain.Order;
import com.ecommerce.order.service.OrderService;
import java.util.List;
import java.util.UUID;

/**
 * OrderController provides REST API endpoints for order operations.
 *
 * API Endpoints:
 * - POST /api/v1/orders - Create order
 * - GET /api/v1/orders/{id} - Get order by ID
 * - GET /api/v1/orders - List customer orders
 * - DELETE /api/v1/orders/{id} - Cancel order
 *
 * See api-design.md for complete API specification.
 * Called from CheckoutFlow.tsx via orderService.ts
 */
public class OrderController {
    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    /**
     * Create new order.
     * POST /api/v1/orders
     *
     * Called from:
     * - CheckoutFlow.tsx frontend component
     * - orderService.ts TypeScript client
     */
    public OrderResponse createOrder(CreateOrderRequest request) {
        // CALLS OrderService.processOrder()
        Order order = orderService.processOrder(request);

        return new OrderResponse(
            order.getId(),
            order.getCustomerId(),
            order.getStatus(),
            order.getTotalAmount(),
            order.getItems(),
            order.getCreatedAt()
        );
    }

    /**
     * Get order by ID.
     * GET /api/v1/orders/{orderId}
     *
     * Called from:
     * - OrderStatus.tsx for status tracking
     * - OrderList.tsx for order details
     */
    public OrderResponse getOrder(UUID orderId) {
        // CALLS OrderService.getOrder()
        Order order = orderService.getOrder(orderId);
        return mapToResponse(order);
    }

    /**
     * List customer orders.
     * GET /api/v1/orders?customerId={customerId}
     *
     * Called from OrderList.tsx
     */
    public List<OrderResponse> listOrders(UUID customerId) {
        // CALLS OrderService.getCustomerOrders()
        List<Order> orders = orderService.getCustomerOrders(customerId);
        return orders.stream()
            .map(this::mapToResponse)
            .toList();
    }

    /**
     * Cancel order.
     * DELETE /api/v1/orders/{orderId}
     */
    public void cancelOrder(UUID orderId, CancelOrderRequest request) {
        // CALLS OrderService.cancelOrder()
        orderService.cancelOrder(orderId, request.getReason());
    }

    /**
     * Map Order entity to API response.
     */
    private OrderResponse mapToResponse(Order order) {
        return new OrderResponse(
            order.getId(),
            order.getCustomerId(),
            order.getStatus(),
            order.getTotalAmount(),
            order.getItems(),
            order.getCreatedAt()
        );
    }
}
