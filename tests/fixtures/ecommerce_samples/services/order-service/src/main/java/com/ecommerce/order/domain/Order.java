package com.ecommerce.order.domain;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Order domain entity representing customer orders.
 *
 * Managed by OrderService and persisted via OrderRepository.
 * References CustomerService for customer tier information.
 */
public class Order {
    private UUID id;
    private UUID customerId;
    private OrderStatus status;
    private BigDecimal totalAmount;
    private List<OrderItem> items;
    private UUID paymentId;
    private UUID reservationId;
    private String cancellationReason;
    private Instant createdAt;
    private Instant updatedAt;

    public Order() {
        this.items = new ArrayList<>();
        this.createdAt = Instant.now();
        this.status = OrderStatus.PENDING;
    }

    // Builder pattern
    public static OrderBuilder builder() {
        return new OrderBuilder();
    }

    /**
     * Add item to order.
     * Creates CONTAINS relationship between Order and OrderItem.
     */
    public void addItem(OrderItem item) {
        this.items.add(item);
        item.setOrder(this);  // Bidirectional CONTAINS ↔ CONTAINED_BY
    }

    /**
     * Check if order can be cancelled.
     * Only PENDING and CONFIRMED orders can be cancelled.
     */
    public boolean canBeCancelled() {
        return status == OrderStatus.PENDING ||
               status == OrderStatus.CONFIRMED;
    }

    /**
     * Check if order has been paid.
     */
    public boolean isPaid() {
        return paymentId != null &&
               (status == OrderStatus.CONFIRMED ||
                status == OrderStatus.PREPARING ||
                status == OrderStatus.SHIPPED ||
                status == OrderStatus.DELIVERED);
    }

    // Getters and setters
    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public UUID getCustomerId() { return customerId; }
    public void setCustomerId(UUID customerId) { this.customerId = customerId; }

    public OrderStatus getStatus() { return status; }
    public void setStatus(OrderStatus status) {
        this.status = status;
        this.updatedAt = Instant.now();
    }

    public BigDecimal getTotalAmount() { return totalAmount; }
    public void setTotalAmount(BigDecimal totalAmount) {
        this.totalAmount = totalAmount;
    }

    public List<OrderItem> getItems() { return items; }
    public void setItems(List<OrderItem> items) { this.items = items; }

    public UUID getPaymentId() { return paymentId; }
    public void setPaymentId(UUID paymentId) { this.paymentId = paymentId; }

    public UUID getReservationId() { return reservationId; }
    public void setReservationId(UUID reservationId) {
        this.reservationId = reservationId;
    }

    public String getCancellationReason() { return cancellationReason; }
    public void setCancellationReason(String reason) {
        this.cancellationReason = reason;
    }

    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    // Builder class
    public static class OrderBuilder {
        private Order order = new Order();

        public OrderBuilder customerId(UUID customerId) {
            order.setCustomerId(customerId);
            return this;
        }

        public OrderBuilder status(OrderStatus status) {
            order.setStatus(status);
            return this;
        }

        public OrderBuilder totalAmount(BigDecimal amount) {
            order.setTotalAmount(amount);
            return this;
        }

        public OrderBuilder createdAt(Instant createdAt) {
            order.createdAt = createdAt;
            return this;
        }

        public Order build() {
            order.setId(UUID.randomUUID());
            return order;
        }
    }
}
