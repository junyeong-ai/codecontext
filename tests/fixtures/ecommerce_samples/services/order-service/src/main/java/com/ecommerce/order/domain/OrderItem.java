package com.ecommerce.order.domain;

import java.math.BigDecimal;
import java.util.UUID;

/**
 * OrderItem entity representing individual items within an order.
 *
 * Has CONTAINED_BY relationship with Order (parent).
 * References Product entity via productId.
 */
public class OrderItem {
    private UUID id;
    private UUID productId;
    private String productName;
    private int quantity;
    private BigDecimal price;
    private Order order;  // CONTAINED_BY relationship

    public OrderItem() {
        this.id = UUID.randomUUID();
    }

    public static OrderItemBuilder builder() {
        return new OrderItemBuilder();
    }

    /**
     * Calculate line total for this item.
     */
    public BigDecimal getLineTotal() {
        return price.multiply(BigDecimal.valueOf(quantity));
    }

    // Getters and setters
    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public UUID getProductId() { return productId; }
    public void setProductId(UUID productId) { this.productId = productId; }

    public String getProductName() { return productName; }
    public void setProductName(String productName) {
        this.productName = productName;
    }

    public int getQuantity() { return quantity; }
    public void setQuantity(int quantity) { this.quantity = quantity; }

    public BigDecimal getPrice() { return price; }
    public void setPrice(BigDecimal price) { this.price = price; }

    public Order getOrder() { return order; }
    public void setOrder(Order order) { this.order = order; }

    // Builder
    public static class OrderItemBuilder {
        private OrderItem item = new OrderItem();

        public OrderItemBuilder productId(UUID productId) {
            item.setProductId(productId);
            return this;
        }

        public OrderItemBuilder productName(String name) {
            item.setProductName(name);
            return this;
        }

        public OrderItemBuilder quantity(int quantity) {
            item.setQuantity(quantity);
            return this;
        }

        public OrderItemBuilder price(BigDecimal price) {
            item.setPrice(price);
            return this;
        }

        public OrderItem build() {
            return item;
        }
    }
}
