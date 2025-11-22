package com.ecommerce.customer.domain

/**
 * Customer tier enumeration.
 *
 * Defines loyalty program tiers with associated benefits.
 * Referenced by:
 * - Customer.kt: Customer tier property
 * - CustomerService.kt: Tier calculation logic
 * - OrderService.java: Discount calculation
 * - pricing-policy.md: Pricing documentation
 * - customer-tier.md: Tier system documentation
 *
 * Tier Thresholds:
 * - BRONZE: $0 - $499 lifetime purchases (default)
 * - SILVER: $500 - $1,999 lifetime purchases
 * - GOLD: $2,000 - $4,999 lifetime purchases
 * - PLATINUM: $5,000+ lifetime purchases
 */
enum class CustomerTier {
    /**
     * Bronze tier - Default tier for new customers.
     * Benefits:
     * - 0% discount
     * - Free shipping on orders $50+
     * - Standard support
     */
    BRONZE,

    /**
     * Silver tier - First loyalty tier.
     * Benefits:
     * - 5% discount on all orders
     * - Free shipping on orders $35+
     * - Standard support
     * - Access to exclusive deals
     */
    SILVER,

    /**
     * Gold tier - Premium tier.
     * Benefits:
     * - 10% discount on all orders
     * - Free shipping on all orders
     * - Priority support
     * - Access to exclusive deals
     */
    GOLD,

    /**
     * Platinum tier - Highest tier.
     * Benefits:
     * - 15% discount on all orders
     * - Free express shipping on all orders
     * - Priority support
     * - Early access to new products
     * - Exclusive platinum-only deals
     */
    PLATINUM;

    /**
     * Get display name for tier.
     */
    fun getDisplayName(): String {
        return when (this) {
            BRONZE -> "Bronze Member"
            SILVER -> "Silver Member"
            GOLD -> "Gold Member"
            PLATINUM -> "Platinum Member"
        }
    }

    /**
     * Get next tier for upgrade path.
     */
    fun getNextTier(): CustomerTier? {
        return when (this) {
            BRONZE -> SILVER
            SILVER -> GOLD
            GOLD -> PLATINUM
            PLATINUM -> null  // Already at highest tier
        }
    }

    /**
     * Get tier color for UI display.
     * Referenced by frontend components for styling.
     */
    fun getColorCode(): String {
        return when (this) {
            BRONZE -> "#CD7F32"
            SILVER -> "#C0C0C0"
            GOLD -> "#FFD700"
            PLATINUM -> "#E5E4E2"
        }
    }
}
