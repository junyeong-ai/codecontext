package com.ecommerce.order.domain;

/**
 * Order status enumeration defining order lifecycle states.
 *
 * Used by Order entity and OrderService for state management.
 * Referenced in order-flow.md documentation.
 */
public enum OrderStatus {
    /**
     * Order created, awaiting payment.
     */
    PENDING,

    /**
     * Payment is being processed.
     */
    PAYMENT_PROCESSING,

    /**
     * Payment successful, order confirmed.
     */
    CONFIRMED,

    /**
     * Warehouse preparing items for shipment.
     */
    PREPARING,

    /**
     * Order has been shipped to customer.
     */
    SHIPPED,

    /**
     * Order delivered to customer.
     */
    DELIVERED,

    /**
     * Order cancelled before shipment.
     */
    CANCELLED,

    /**
     * Payment failed, order cannot proceed.
     */
    PAYMENT_FAILED,

    /**
     * Order refunded after delivery.
     */
    REFUNDED
}
