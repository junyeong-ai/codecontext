package com.ecommerce.customer.domain

import java.math.BigDecimal
import java.time.LocalDateTime
import java.util.UUID

/**
 * Customer domain entity.
 *
 * Managed by CustomerService and referenced by OrderService.java for tier discounts.
 * See customer-tier.md for tier benefits and upgrade rules.
 */
data class Customer(
    val id: UUID,
    val email: String,
    val firstName: String,
    val lastName: String,
    var tier: CustomerTier,
    val totalOrders: Int,
    val totalPurchases: BigDecimal,
    val createdAt: LocalDateTime,
    val updatedAt: LocalDateTime
) {
    /**
     * Get full customer name.
     */
    fun getFullName(): String = "$firstName $lastName"

    /**
     * Check if customer qualifies for tier upgrade.
     * Called by CustomerService.updateCustomerTier()
     */
    fun qualifiesForUpgrade(): Boolean {
        val requiredAmount = when (tier) {
            CustomerTier.BRONZE -> BigDecimal("500.00")
            CustomerTier.SILVER -> BigDecimal("2000.00")
            CustomerTier.GOLD -> BigDecimal("5000.00")
            CustomerTier.PLATINUM -> return false  // Already at highest
        }

        return totalPurchases >= requiredAmount
    }

    /**
     * Get tier discount rate.
     * Referenced by OrderService.java for price calculations.
     * See pricing-policy.md for discount rules.
     */
    fun getTierDiscount(): BigDecimal {
        return when (tier) {
            CustomerTier.BRONZE -> BigDecimal.ZERO
            CustomerTier.SILVER -> BigDecimal("0.05")  // 5%
            CustomerTier.GOLD -> BigDecimal("0.10")    // 10%
            CustomerTier.PLATINUM -> BigDecimal("0.15") // 15%
        }
    }

    /**
     * Get minimum order amount for free shipping.
     */
    fun getFreeShippingThreshold(): BigDecimal {
        return when (tier) {
            CustomerTier.BRONZE -> BigDecimal("50.00")
            CustomerTier.SILVER -> BigDecimal("35.00")
            CustomerTier.GOLD -> BigDecimal.ZERO
            CustomerTier.PLATINUM -> BigDecimal.ZERO
        }
    }

    /**
     * Check if customer has priority support.
     */
    fun hasPrioritySupport(): Boolean {
        return tier == CustomerTier.GOLD || tier == CustomerTier.PLATINUM
    }

    /**
     * Calculate lifetime value (LTV).
     */
    fun calculateLifetimeValue(): BigDecimal {
        return totalPurchases
    }

    companion object {
        /**
         * Create new customer with default BRONZE tier.
         */
        fun create(
            email: String,
            firstName: String,
            lastName: String
        ): Customer {
            return Customer(
                id = UUID.randomUUID(),
                email = email,
                firstName = firstName,
                lastName = lastName,
                tier = CustomerTier.BRONZE,
                totalOrders = 0,
                totalPurchases = BigDecimal.ZERO,
                createdAt = LocalDateTime.now(),
                updatedAt = LocalDateTime.now()
            )
        }
    }
}
