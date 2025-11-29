"""Product domain model.

Represents products in the e-commerce catalog.

Referenced by:
- inventory_service.py: Stock management
- OrderItem.java: Order line items
- ProductCard.tsx: Frontend product display
"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass
class Dimensions:
    """Product dimensions for shipping calculations."""

    length: float  # cm
    width: float  # cm
    height: float  # cm
    weight: float  # kg

    def volume(self) -> float:
        """Calculate volume in cubic centimeters."""
        return self.length * self.width * self.height


@dataclass
class Product:
    """
    Product domain model.

    Attributes:
        id: Product unique identifier
        sku: Stock keeping unit code
        name: Product name
        description: Product description
        price: Base price in USD
        category: Product category
        brand: Product brand
        image_url: Main product image URL
        dimensions: Physical dimensions and weight
        is_active: Whether product is available for sale
    """

    id: UUID
    sku: str
    name: str
    description: str
    price: Decimal
    category: str
    brand: str | None = None
    image_url: str | None = None
    dimensions: Dimensions | None = None
    is_active: bool = True

    def formatted_price(self) -> str:
        """Get formatted price string."""
        return f"${self.price:.2f}"

    def is_available(self) -> bool:
        """Check if product is available for purchase."""
        return self.is_active

    def calculate_shipping_weight(self) -> float:
        """Get shipping weight in kg."""
        if self.dimensions:
            return self.dimensions.weight
        return 0.5  # Default weight
