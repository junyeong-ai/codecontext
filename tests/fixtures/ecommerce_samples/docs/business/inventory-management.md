# Inventory Management System

## Overview

Multi-warehouse inventory management with real-time stock tracking, reservation system, and automatic reordering.

## Components

### Inventory Service (`inventory_service.py`)

Main service coordinating all inventory operations:

```python
class InventoryService:
    """Manages product inventory across warehouses."""

    def check_stock(self, product_id: str, quantity: int) -> bool:
        """Check if product is available in requested quantity."""
        total_stock = sum(
            warehouse.get_stock(product_id).available_quantity
            for warehouse in warehouses
        )
        return total_stock >= quantity

    def reserve_stock(self, order_items: List[OrderItem]) -> Reservation:
        """Reserve stock for order, called by OrderService.java"""
        reservations = []
        for item in order_items:
            warehouse = self._select_warehouse(item.product_id)
            reservation = warehouse.reserve(
                product_id=item.product_id,
                quantity=item.quantity
            )
            reservations.append(reservation)
        return Reservation(items=reservations)
```

### Models

**Product Model (`product.py`):**
```python
class Product:
    id: UUID
    sku: str
    name: str
    price: Decimal
    category: str
    weight: float
    dimensions: Dimensions
```

**Stock Model (`stock.py`):**
```python
class Stock:
    product_id: UUID
    warehouse_id: UUID
    available_quantity: int
    reserved_quantity: int
    reorder_point: int
    reorder_quantity: int
```

**Warehouse Model (`warehouse.py`):**
```python
class Warehouse:
    id: UUID
    name: str
    address: Address
    capacity: int
    current_utilization: float
```

## Stock Operations

### Stock Reservation Flow

1. **Order Created** - `OrderService.java` calls `inventory_service.check_stock()`
2. **Stock Check** - Verify availability across warehouses
3. **Reserve Stock** - Create temporary reservation (30 min TTL)
4. **Payment Success** - Convert reservation to committed
5. **Payment Failure** - Release reservation automatically

### Integration with Order Service

```java
// OrderService.java
public Order processOrder(CreateOrderRequest request) {
    // Validate inventory
    for (OrderItem item : request.getItems()) {
        if (!inventoryService.checkStock(item.getProductId(), item.getQuantity())) {
            throw new OutOfStockException(item.getProductId());
        }
    }

    // Create order
    Order order = createOrder(request);

    // Reserve stock
    Reservation reservation = inventoryService.reserveStock(order.getItems());
    order.setReservationId(reservation.getId());

    return order;
}
```

## Warehouse Selection

### Algorithm

```python
def _select_warehouse(self, product_id: str) -> Warehouse:
    """Select optimal warehouse for product fulfillment."""
    candidates = [
        w for w in self.warehouses
        if w.has_stock(product_id) and w.has_capacity()
    ]

    # Prioritize by:
    # 1. Highest stock level
    # 2. Closest to customer
    # 3. Lowest utilization
    return max(candidates, key=lambda w: (
        w.get_stock(product_id).available_quantity,
        -w.distance_to_customer,
        -w.current_utilization
    ))
```

## Auto-Reordering

```python
def check_reorder_points(self) -> List[ReorderRequest]:
    """Check stock levels and generate reorder requests."""
    reorder_requests = []

    for warehouse in self.warehouses:
        for stock in warehouse.get_all_stocks():
            if stock.available_quantity <= stock.reorder_point:
                request = ReorderRequest(
                    product_id=stock.product_id,
                    warehouse_id=warehouse.id,
                    quantity=stock.reorder_quantity,
                    priority=self._calculate_priority(stock)
                )
                reorder_requests.append(request)

    return reorder_requests
```

## Related Code

- Service: `inventory_service.py`
- Models: `product.py`, `stock.py`, `warehouse.py`
- Repository: `inventory_repository.py`
- Integration: `OrderService.java`
