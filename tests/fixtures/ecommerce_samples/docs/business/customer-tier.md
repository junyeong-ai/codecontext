# Customer Tier System

## Overview

Four-tier customer loyalty program with automatic upgrades based on purchase history and lifetime value.

## Customer Tiers

### Tier Definitions (`CustomerTier.kt`)

```kotlin
enum class CustomerTier {
    BRONZE,  // Default tier, $0-$499 lifetime
    SILVER,  // $500-$1,999 lifetime
    GOLD,    // $2,000-$4,999 lifetime
    PLATINUM // $5,000+ lifetime
}
```

## Tier Benefits

| Tier | Discount | Free Shipping | Priority Support | Exclusive Deals |
|------|----------|---------------|------------------|-----------------|
| BRONZE | 0% | Orders $50+ | No | No |
| SILVER | 5% | Orders $35+ | No | Yes |
| GOLD | 10% | All orders | Yes | Yes |
| PLATINUM | 15% | All orders + Express | Yes | Yes + Early Access |

## Tier Calculation

### Customer Service Implementation (`CustomerService.kt`)

```kotlin
class CustomerService(
    private val customerRepository: CustomerRepository
) {
    fun calculateTier(customer: Customer): CustomerTier {
        val lifetimeValue = customer.totalPurchases

        return when {
            lifetimeValue >= BigDecimal("5000.00") -> CustomerTier.PLATINUM
            lifetimeValue >= BigDecimal("2000.00") -> CustomerTier.GOLD
            lifetimeValue >= BigDecimal("500.00") -> CustomerTier.SILVER
            else -> CustomerTier.BRONZE
        }
    }

    fun updateCustomerTier(customerId: UUID) {
        val customer = customerRepository.findById(customerId)
        val newTier = calculateTier(customer)

        if (newTier != customer.tier) {
            val previousTier = customer.tier
            customer.tier = newTier
            customerRepository.save(customer)

            // Send tier upgrade notification
            notificationService.sendTierUpgradeEmail(
                customer,
                previousTier,
                newTier
            )
        }
    }
}
```

## Integration with Order Service

### Discount Application

```java
// OrderService.java
public BigDecimal calculateOrderTotal(Order order) {
    BigDecimal subtotal = order.getItems().stream()
        .map(item -> item.getPrice().multiply(
            BigDecimal.valueOf(item.getQuantity())
        ))
        .reduce(BigDecimal.ZERO, BigDecimal::add);

    // Get customer tier discount
    Customer customer = customerService.getCustomer(order.getCustomerId());
    BigDecimal discount = getTierDiscount(customer.getTier());

    // Apply discount
    BigDecimal total = subtotal.multiply(
        BigDecimal.ONE.subtract(discount)
    );

    return total;
}

private BigDecimal getTierDiscount(CustomerTier tier) {
    return switch (tier) {
        case BRONZE -> BigDecimal.ZERO;
        case SILVER -> new BigDecimal("0.05");  // 5%
        case GOLD -> new BigDecimal("0.10");    // 10%
        case PLATINUM -> new BigDecimal("0.15"); // 15%
    };
}
```

## Pricing Policy Integration

See `pricing-policy.md` for detailed discount calculation rules.

## Related Code

- Customer domain: `Customer.kt`, `CustomerTier.kt`
- Customer service: `CustomerService.kt`
- Customer repository: `CustomerRepository.kt`
- Order integration: `OrderService.java`
