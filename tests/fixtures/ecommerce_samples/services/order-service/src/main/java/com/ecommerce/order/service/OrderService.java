package com.ecommerce.order.service;

import com.ecommerce.order.domain.Order;
import com.ecommerce.order.domain.OrderItem;
import com.ecommerce.order.domain.OrderStatus;
import com.ecommerce.order.repository.OrderRepository;
import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

/**
 * OrderService handles order processing business logic.
 *
 * Dependencies:
 * - OrderRepository for data persistence
 * - PaymentService (Python) for payment processing
 * - InventoryService (Python) for stock management
 * - ShippingService (Python) for shipping coordination
 * - CustomerService (Kotlin) for customer tier information
 *
 * Referenced in order-flow.md documentation.
 */
public class OrderService {
    private final OrderRepository orderRepository;
    private final PaymentServiceClient paymentService;
    private final InventoryServiceClient inventoryService;
    private final ShippingServiceClient shippingService;
    private final CustomerServiceClient customerService;

    public OrderService(
        OrderRepository orderRepository,
        PaymentServiceClient paymentService,
        InventoryServiceClient inventoryService,
        ShippingServiceClient shippingService,
        CustomerServiceClient customerService
    ) {
        this.orderRepository = orderRepository;
        this.paymentService = paymentService;
        this.inventoryService = inventoryService;
        this.shippingService = shippingService;
        this.customerService = customerService;
    }

    /**
     * Process new order with payment and inventory validation.
     *
     * Flow:
     * 1. Validate inventory via inventoryService.checkStock()
     * 2. Calculate total with customer tier discount
     * 3. Create order entity
     * 4. Reserve inventory
     * 5. Process payment via paymentService.processPayment()
     * 6. Update order status based on payment result
     * 7. Create shipment if payment successful
     *
     * Called by OrderController.createOrder()
     */
    public Order processOrder(CreateOrderRequest request) {
        // Step 1: Validate inventory
        for (OrderItemRequest itemRequest : request.getItems()) {
            boolean available = inventoryService.checkStock(
                itemRequest.getProductId(),
                itemRequest.getQuantity()
            );
            if (!available) {
                throw new OutOfStockException(
                    "Product " + itemRequest.getProductId() + " out of stock"
                );
            }
        }

        // Step 2: Calculate total with tier discount
        BigDecimal subtotal = calculateSubtotal(request.getItems());
        BigDecimal tierDiscount = getTierDiscount(request.getCustomerId());
        BigDecimal totalAmount = subtotal.multiply(
            BigDecimal.ONE.subtract(tierDiscount)
        );

        // Step 3: Create order
        Order order = Order.builder()
            .customerId(request.getCustomerId())
            .status(OrderStatus.PENDING)
            .totalAmount(totalAmount)
            .build();

        for (OrderItemRequest itemRequest : request.getItems()) {
            OrderItem item = OrderItem.builder()
                .productId(itemRequest.getProductId())
                .productName(itemRequest.getProductName())
                .quantity(itemRequest.getQuantity())
                .price(itemRequest.getPrice())
                .build();
            order.addItem(item);  // CONTAINS relationship
        }

        Order savedOrder = orderRepository.save(order);

        // Step 4: Reserve inventory
        ReservationResult reservation = inventoryService.reserveStock(
            savedOrder.getItems()
        );
        savedOrder.setReservationId(reservation.getReservationId());

        // Step 5: Process payment
        savedOrder.setStatus(OrderStatus.PAYMENT_PROCESSING);
        orderRepository.save(savedOrder);

        PaymentRequest paymentRequest = new PaymentRequest(
            savedOrder.getId(),
            savedOrder.getTotalAmount(),
            request.getPaymentMethod(),
            request.getCardToken()
        );

        PaymentResult paymentResult = paymentService.processPayment(
            paymentRequest
        );

        // Step 6: Update status based on payment
        if (paymentResult.isSuccess()) {
            savedOrder.setStatus(OrderStatus.CONFIRMED);
            savedOrder.setPaymentId(paymentResult.getPaymentId());

            // Step 7: Create shipment
            shippingService.createShipment(savedOrder);
        } else {
            savedOrder.setStatus(OrderStatus.PAYMENT_FAILED);
            // Release inventory reservation
            inventoryService.releaseReservation(
                savedOrder.getReservationId()
            );
        }

        return orderRepository.save(savedOrder);
    }

    /**
     * Cancel order and process refund if applicable.
     * CALLS relationship with paymentService.refund()
     */
    public void cancelOrder(UUID orderId, String reason) {
        Order order = orderRepository.findById(orderId)
            .orElseThrow(() -> new OrderNotFoundException(orderId));

        if (!order.canBeCancelled()) {
            throw new OrderCannotBeCancelledException(
                "Order in status " + order.getStatus() + " cannot be cancelled"
            );
        }

        // Release inventory
        if (order.getReservationId() != null) {
            inventoryService.releaseReservation(order.getReservationId());
        }

        // Process refund if paid
        if (order.isPaid()) {
            paymentService.refund(order.getPaymentId(), reason);
        }

        order.setStatus(OrderStatus.CANCELLED);
        order.setCancellationReason(reason);
        orderRepository.save(order);
    }

    /**
     * Calculate order subtotal before discounts.
     */
    private BigDecimal calculateSubtotal(List<OrderItemRequest> items) {
        return items.stream()
            .map(item -> item.getPrice().multiply(
                BigDecimal.valueOf(item.getQuantity())
            ))
            .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    /**
     * Get customer tier discount percentage.
     * CALLS CustomerService.kt to get tier information.
     */
    private BigDecimal getTierDiscount(UUID customerId) {
        Customer customer = customerService.getCustomer(customerId);

        return switch (customer.getTier()) {
            case BRONZE -> BigDecimal.ZERO;
            case SILVER -> new BigDecimal("0.05");  // 5%
            case GOLD -> new BigDecimal("0.10");    // 10%
            case PLATINUM -> new BigDecimal("0.15"); // 15%
        };
    }

    /**
     * Get order by ID.
     * CALLS OrderRepository.findById()
     */
    public Order getOrder(UUID orderId) {
        return orderRepository.findById(orderId)
            .orElseThrow(() -> new OrderNotFoundException(orderId));
    }

    /**
     * Get customer's order history.
     */
    public List<Order> getCustomerOrders(UUID customerId) {
        return orderRepository.findByCustomerId(customerId);
    }
}
