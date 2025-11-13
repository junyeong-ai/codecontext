# Order Processing Flow

## Overview

This document describes the complete order lifecycle from cart checkout to order delivery, including all service interactions and state transitions.

## Order States

```
PENDING → PAYMENT_PROCESSING → CONFIRMED → PREPARING → SHIPPED → DELIVERED
                ↓
              CANCELLED
                ↓
              REFUNDED
```

## State Definitions

- **PENDING**: Order created, awaiting payment
- **PAYMENT_PROCESSING**: Payment gateway processing payment
- **CONFIRMED**: Payment successful, order confirmed
- **PREPARING**: Warehouse preparing items for shipment
- **SHIPPED**: Order dispatched to customer
- **DELIVERED**: Customer received order
- **CANCELLED**: Order cancelled (before shipment)
- **REFUNDED**: Order refunded after delivery

## Order Creation Flow

### Step 1: Cart to Order Conversion

**Frontend:**
```typescript
// CheckoutFlow.tsx calls orderService.createOrder()
const order = await orderService.createOrder({
  items: cartItems,
  shippingAddress: selectedAddress,
  paymentMethod: selectedPaymentMethod
});
```

**Backend:**
```java
// OrderController.java receives request
@PostMapping("/orders")
public OrderResponse createOrder(@RequestBody CreateOrderRequest request) {
    return orderService.processOrder(request);
}
```

### Step 2: Inventory Validation

```java
// OrderService.java validates stock
for (OrderItem item : request.getItems()) {
    boolean available = inventoryService.checkStock(
        item.getProductId(),
        item.getQuantity()
    );
    if (!available) {
        throw new OutOfStockException(item.getProductId());
    }
}
```

**Python Integration:**
```python
# inventory_service.py provides stock check
def check_stock(product_id: str, quantity: int) -> bool:
    stock = inventory_repository.get_stock(product_id)
    return stock.available_quantity >= quantity
```

### Step 3: Order Creation

```java
// OrderService.java creates order entity
Order order = Order.builder()
    .customerId(request.getCustomerId())
    .status(OrderStatus.PENDING)
    .totalAmount(calculateTotal(request.getItems()))
    .createdAt(Instant.now())
    .build();

// Add order items
for (CreateOrderItemRequest itemRequest : request.getItems()) {
    OrderItem item = OrderItem.builder()
        .productId(itemRequest.getProductId())
        .quantity(itemRequest.getQuantity())
        .price(itemRequest.getPrice())
        .build();
    order.addItem(item);  // CONTAINS relationship
}

// Save to database
Order savedOrder = orderRepository.save(order);
```

### Step 4: Payment Processing

```java
// OrderService.java calls PaymentService
PaymentRequest paymentRequest = PaymentRequest.builder()
    .orderId(savedOrder.getId())
    .amount(savedOrder.getTotalAmount())
    .paymentMethod(request.getPaymentMethod())
    .build();

PaymentResult result = paymentService.processPayment(paymentRequest);
```

**Python Payment Service:**
```python
# payment_service.py processes payment
def process_payment(payment_request: PaymentRequest) -> PaymentResult:
    # Route to appropriate gateway
    gateway = payment_gateway.get_gateway(payment_request.payment_method)

    # Process transaction
    transaction = gateway.charge(
        amount=payment_request.amount,
        card_token=payment_request.card_token
    )

    # Record payment
    payment = Payment(
        order_id=payment_request.order_id,
        amount=payment_request.amount,
        transaction_id=transaction.id,
        status=transaction.status
    )
    payment_repository.save(payment)

    return PaymentResult(success=transaction.success)
```

### Step 5: Order Confirmation

```java
// OrderService.java updates order status
if (paymentResult.isSuccess()) {
    order.setStatus(OrderStatus.CONFIRMED);
    order.setPaymentId(paymentResult.getPaymentId());
    orderRepository.save(order);

    // Reserve inventory
    inventoryService.reserveStock(order.getItems());

    // Create shipping label
    shippingService.createShipment(order);

    // Send confirmation email
    notificationService.sendOrderConfirmation(order);
} else {
    order.setStatus(OrderStatus.CANCELLED);
    orderRepository.save(order);
}
```

## Shipping Coordination

### Shipping Service Integration

```python
# shipping_service.py creates shipment
def create_shipment(order_data: OrderData) -> Shipment:
    # Calculate shipping cost
    cost = calculate_shipping_cost(
        origin=warehouse.address,
        destination=order_data.shipping_address,
        weight=order_data.total_weight
    )

    # Create shipping label
    carrier = select_carrier(order_data.shipping_speed)
    label = carrier.create_label(order_data)

    # Record shipment
    shipment = Shipment(
        order_id=order_data.order_id,
        carrier=carrier.name,
        tracking_number=label.tracking_number,
        cost=cost,
        estimated_delivery=calculate_delivery_date(order_data)
    )
    shipping_repository.save(shipment)

    return shipment
```

**JavaScript Calculation:**
```javascript
// calculateShipping.js
export function calculateShippingCost(origin, destination, weight) {
  const distance = calculateDistance(origin, destination);
  const baseRate = 5.99;
  const perMileRate = 0.10;
  const perPoundRate = 0.50;

  return baseRate + (distance * perMileRate) + (weight * perPoundRate);
}
```

## Order Status Updates

### Frontend Tracking

```typescript
// OrderStatus.tsx displays current status
const OrderStatus: React.FC<{orderId: string}> = ({orderId}) => {
  const [order, setOrder] = useState<Order | null>(null);

  useEffect(() => {
    // Poll for status updates
    const interval = setInterval(async () => {
      const updated = await orderService.getOrder(orderId);
      setOrder(updated);
    }, 30000); // Poll every 30 seconds

    return () => clearInterval(interval);
  }, [orderId]);

  return (
    <OrderStatusTimeline
      status={order?.status}
      events={order?.statusHistory}
    />
  );
};
```

## Cancellation and Refunds

### Order Cancellation

```java
// OrderService.java handles cancellation
public void cancelOrder(UUID orderId, String reason) {
    Order order = orderRepository.findById(orderId)
        .orElseThrow(() -> new OrderNotFoundException(orderId));

    // Can only cancel before shipment
    if (!order.canBeCancelled()) {
        throw new OrderCannotBeCancelledException(
            "Order already shipped"
        );
    }

    // Release inventory
    inventoryService.releaseReservation(order.getItems());

    // Process refund
    if (order.isPaid()) {
        paymentService.refund(order.getPaymentId());
    }

    // Update status
    order.setStatus(OrderStatus.CANCELLED);
    order.setCancellationReason(reason);
    orderRepository.save(order);
}
```

### Refund Processing

```python
# payment_service.py handles refunds
def refund_payment(payment_id: str, reason: str) -> RefundResult:
    payment = payment_repository.get(payment_id)

    # Process refund via gateway
    gateway = payment_gateway.get_gateway(payment.payment_method)
    refund_transaction = gateway.refund(
        transaction_id=payment.transaction_id,
        amount=payment.amount
    )

    # Record refund
    payment.status = PaymentStatus.REFUNDED
    payment.refund_transaction_id = refund_transaction.id
    payment_repository.save(payment)

    return RefundResult(success=True, refund_id=refund_transaction.id)
```

## Customer Notifications

### Notification Events

- Order confirmed → Email + SMS
- Order shipped → Email + Push notification
- Order delivered → Email + Request review
- Order cancelled → Email
- Refund processed → Email

## Performance Considerations

### Optimizations

1. **Inventory Check**: Cache product stock for 1 minute
2. **Payment Processing**: Use async processing with callbacks
3. **Shipping Label**: Generate in background job
4. **Status Updates**: Use event-driven architecture

## Error Handling

### Payment Failures

```java
try {
    paymentService.processPayment(paymentRequest);
} catch (PaymentDeclinedException e) {
    order.setStatus(OrderStatus.PAYMENT_FAILED);
    notificationService.sendPaymentFailureNotification(order);
} catch (PaymentGatewayException e) {
    // Retry with exponential backoff
    retryPayment(order, maxRetries);
}
```

## Related Code

- Order domain: `Order.java`, `OrderItem.java`, `OrderStatus.java`
- Order service: `OrderService.java`, `OrderController.java`
- Payment integration: `payment_service.py`, `payment_gateway.py`
- Shipping integration: `shipping_service.py`, `calculateShipping.js`
- Frontend: `CheckoutFlow.tsx`, `OrderStatus.tsx`
