"""Inventory Service - Multi-warehouse inventory management.

Manages product stock across warehouses with reservation system.

Dependencies:
- product.py: Product domain model
- stock.py: Stock tracking model
- warehouse.py: Warehouse model
- OrderService.java: Calls this service for stock validation

Referenced in:
- order-flow.md: Order processing flow
- inventory-management.md: Inventory system documentation
"""

import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class InventoryService:
    """
    Manages product inventory across warehouses.

    CALLED_BY OrderService.java for stock operations.
    CALLS InventoryRepository for data access.
    REFERENCES Product, Stock, and Warehouse models.
    """

    def __init__(self, inventory_repository: "InventoryRepository", warehouses: list["Warehouse"]):
        """
        Initialize inventory service.

        Args:
            inventory_repository: Data access layer
            warehouses: List of available warehouses
        """
        self.repository = inventory_repository
        self.warehouses = warehouses
        self.logger = logger

    def check_stock(self, product_id: UUID, quantity: int) -> bool:
        """
        Check if product is available in requested quantity.

        Called by OrderService.java before creating order.

        Args:
            product_id: Product to check
            quantity: Required quantity

        Returns:
            True if available, False otherwise
        """
        self.logger.info(f"Checking stock for product {product_id}, quantity: {quantity}")

        # Sum available quantity across all warehouses
        total_stock = sum(
            warehouse.get_stock(product_id).available_quantity
            for warehouse in self.warehouses
            if warehouse.has_stock(product_id)
        )

        available = total_stock >= quantity

        self.logger.info(
            f"Stock check result: {available} (total: {total_stock}, required: {quantity})"
        )

        return available

    def reserve_stock(self, order_items: list["OrderItem"]) -> "Reservation":
        """
        Reserve stock for order.

        Called by OrderService.java after order creation.
        Creates temporary reservation with 30-minute TTL.

        Args:
            order_items: List of OrderItem entities from Order.java

        Returns:
            Reservation object with reservation details

        Raises:
            OutOfStockException: If insufficient stock
        """
        self.logger.info(f"Reserving stock for {len(order_items)} items")

        reservations = []

        for item in order_items:
            # Select optimal warehouse
            warehouse = self._select_warehouse(item.product_id)

            if not warehouse:
                raise OutOfStockException(f"Product {item.product_id} not available")

            # Create reservation
            reservation = warehouse.reserve(product_id=item.product_id, quantity=item.quantity)

            reservations.append(reservation)

            self.logger.info(
                f"Reserved {item.quantity} units of {item.product_id} at warehouse {warehouse.id}"
            )

        return Reservation(items=reservations)

    def release_reservation(self, reservation_id: UUID) -> None:
        """
        Release stock reservation.

        Called by OrderService.java when:
        - Payment fails
        - Order is cancelled
        - Reservation expires

        Args:
            reservation_id: Reservation to release
        """
        self.logger.info(f"Releasing reservation {reservation_id}")

        reservation = self.repository.get_reservation(reservation_id)

        for item in reservation.items:
            warehouse = self._get_warehouse(item.warehouse_id)
            warehouse.release_reservation(product_id=item.product_id, quantity=item.quantity)

        self.repository.delete_reservation(reservation_id)

    def commit_reservation(self, reservation_id: UUID) -> None:
        """
        Commit reservation to actual stock reduction.

        Called by OrderService.java after successful payment.

        Args:
            reservation_id: Reservation to commit
        """
        self.logger.info(f"Committing reservation {reservation_id}")

        reservation = self.repository.get_reservation(reservation_id)

        for item in reservation.items:
            warehouse = self._get_warehouse(item.warehouse_id)
            warehouse.commit_reservation(product_id=item.product_id, quantity=item.quantity)

        reservation.status = ReservationStatus.COMMITTED
        self.repository.save_reservation(reservation)

    def _select_warehouse(self, product_id: UUID) -> Optional["Warehouse"]:
        """
        Select optimal warehouse for product fulfillment.

        Selection criteria (priority order):
        1. Has stock available
        2. Highest stock level
        3. Closest to customer (if available)
        4. Lowest utilization

        Args:
            product_id: Product to select warehouse for

        Returns:
            Selected warehouse or None if unavailable
        """
        candidates = [w for w in self.warehouses if w.has_stock(product_id) and w.has_capacity()]

        if not candidates:
            return None

        # Prioritize by stock level
        return max(candidates, key=lambda w: w.get_stock(product_id).available_quantity)

    def _get_warehouse(self, warehouse_id: UUID) -> "Warehouse":
        """Get warehouse by ID."""
        return next((w for w in self.warehouses if w.id == warehouse_id), None)

    def check_reorder_points(self) -> list["ReorderRequest"]:
        """
        Check stock levels and generate reorder requests.

        Runs periodically to maintain stock levels.

        Returns:
            List of reorder requests for low-stock products
        """
        self.logger.info("Checking reorder points")

        reorder_requests = []

        for warehouse in self.warehouses:
            for stock in warehouse.get_all_stocks():
                if stock.available_quantity <= stock.reorder_point:
                    request = ReorderRequest(
                        product_id=stock.product_id,
                        warehouse_id=warehouse.id,
                        quantity=stock.reorder_quantity,
                        priority=self._calculate_priority(stock),
                    )
                    reorder_requests.append(request)

                    self.logger.info(
                        f"Reorder needed: {stock.product_id} at warehouse {warehouse.id}"
                    )

        return reorder_requests

    def _calculate_priority(self, stock: "Stock") -> int:
        """Calculate reorder priority (1=urgent, 5=low)."""
        utilization = stock.reserved_quantity / stock.available_quantity

        if utilization > 0.9:
            return 1  # Urgent
        elif utilization > 0.7:
            return 2  # High
        elif utilization > 0.5:
            return 3  # Medium
        else:
            return 4  # Low
