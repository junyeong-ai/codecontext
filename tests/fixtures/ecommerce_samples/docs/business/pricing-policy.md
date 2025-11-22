# Pricing Policy

## Overview

Dynamic pricing with customer tier discounts, promotional campaigns, and coupon codes.

## Price Calculation Formula

```
Final Price = (Base Price - Coupon Discount) × (1 - Tier Discount) × (1 - Campaign Discount)
```

## Tier-Based Discounts

See `customer-tier.md` for tier definitions and benefits.

| Tier | Discount Rate |
|------|---------------|
| BRONZE | 0% |
| SILVER | 5% |
| GOLD | 10% |
| PLATINUM | 15% |

## Promotional Campaigns

### Campaign Types

1. **Percentage Discount**: 20% off all orders
2. **Fixed Amount**: $10 off orders over $50
3. **Buy One Get One**: BOGO on selected products
4. **Free Shipping**: No minimum order

### Implementation (`OrderService.java`)

```java
public BigDecimal applyPromotions(Order order, List<Campaign> activeCampaigns) {
    BigDecimal finalPrice = order.getSubtotal();

    for (Campaign campaign : activeCampaigns) {
        if (campaign.isApplicable(order)) {
            finalPrice = campaign.apply(finalPrice);
        }
    }

    return finalPrice;
}
```

## Coupon System

### Coupon Types (Kotlin Model)

```kotlin
data class Coupon(
    val code: String,
    val type: CouponType,
    val value: BigDecimal,
    val minimumOrder: BigDecimal,
    val expiresAt: LocalDateTime,
    val usageLimit: Int,
    val usageCount: Int
)

enum class CouponType {
    PERCENTAGE,  // e.g., 10% off
    FIXED_AMOUNT // e.g., $5 off
}
```

## Price Display

### Frontend Implementation (`formatPrice.js`)

```javascript
export function formatPrice(price, tierDiscount = 0) {
  const originalPrice = price;
  const discountedPrice = price * (1 - tierDiscount);

  if (tierDiscount > 0) {
    return {
      original: `$${originalPrice.toFixed(2)}`,
      discounted: `$${discountedPrice.toFixed(2)}`,
      savings: `Save $${(originalPrice - discountedPrice).toFixed(2)}`
    };
  }

  return {
    price: `$${price.toFixed(2)}`
  };
}
```

## Related Code

- Order service: `OrderService.java`
- Customer tiers: `CustomerTier.kt`, `CustomerService.kt`
- Price formatting: `formatPrice.js`
- Product display: `ProductCard.tsx`
