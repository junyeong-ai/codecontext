package com.ecommerce.customer.service

import com.ecommerce.customer.domain.Customer
import com.ecommerce.customer.domain.CustomerTier
import com.ecommerce.customer.repository.CustomerRepository
import java.math.BigDecimal
import java.util.UUID
import org.slf4j.LoggerFactory

/**
 * CustomerService handles customer operations and tier management.
 *
 * Dependencies:
 * - CustomerRepository: Data persistence
 * - NotificationService: Tier upgrade emails
 *
 * Called by:
 * - OrderService.java: Get customer tier for discount calculation
 * - Frontend: Customer profile management
 *
 * References:
 * - customer-tier.md: Tier system documentation
 * - pricing-policy.md: Discount rules
 */
class CustomerService(
    private val customerRepository: CustomerRepository
) {
    private val logger = LoggerFactory.getLogger(CustomerService::class.java)

    /**
     * Get customer by ID.
     * Called by OrderService.java for tier discount calculation.
     */
    fun getCustomer(customerId: UUID): Customer {
        return customerRepository.findById(customerId)
            ?: throw CustomerNotFoundException("Customer $customerId not found")
    }

    /**
     * Calculate appropriate tier based on lifetime purchases.
     *
     * Tier Thresholds (see customer-tier.md):
     * - PLATINUM: $5,000+
     * - GOLD: $2,000 - $4,999
     * - SILVER: $500 - $1,999
     * - BRONZE: $0 - $499
     */
    fun calculateTier(customer: Customer): CustomerTier {
        val lifetimeValue = customer.totalPurchases

        return when {
            lifetimeValue >= BigDecimal("5000.00") -> CustomerTier.PLATINUM
            lifetimeValue >= BigDecimal("2000.00") -> CustomerTier.GOLD
            lifetimeValue >= BigDecimal("500.00") -> CustomerTier.SILVER
            else -> CustomerTier.BRONZE
        }
    }

    /**
     * Update customer tier based on purchase history.
     * Called after each successful order.
     *
     * If tier changes, sends upgrade notification email.
     */
    fun updateCustomerTier(customerId: UUID) {
        val customer = getCustomer(customerId)
        val newTier = calculateTier(customer)

        if (newTier != customer.tier) {
            val previousTier = customer.tier

            logger.info(
                "Customer {} tier upgrade: {} -> {}",
                customerId,
                previousTier,
                newTier
            )

            // Update tier
            customer.tier = newTier
            customerRepository.save(customer)

            // Send notification
            sendTierUpgradeNotification(customer, previousTier, newTier)
        }
    }

    /**
     * Update customer purchase history after order completion.
     * Called by OrderService.java when order is delivered.
     */
    fun recordPurchase(customerId: UUID, orderAmount: BigDecimal) {
        val customer = getCustomer(customerId)

        // Update totals
        val updatedCustomer = customer.copy(
            totalOrders = customer.totalOrders + 1,
            totalPurchases = customer.totalPurchases + orderAmount
        )

        customerRepository.save(updatedCustomer)

        // Check for tier upgrade
        updateCustomerTier(customerId)

        logger.info(
            "Recorded purchase for customer {}: \${} " +
            "(total orders: {}, lifetime: \${})",
            customerId,
            orderAmount,
            updatedCustomer.totalOrders,
            updatedCustomer.totalPurchases
        )
    }

    /**
     * Get customer profile with tier information.
     * Called from frontend customer dashboard.
     */
    fun getCustomerProfile(customerId: UUID): CustomerProfile {
        val customer = getCustomer(customerId)

        return CustomerProfile(
            id = customer.id,
            email = customer.email,
            fullName = customer.getFullName(),
            tier = customer.tier,
            tierDisplayName = customer.tier.getDisplayName(),
            discountRate = customer.getTierDiscount(),
            totalOrders = customer.totalOrders,
            lifetimeValue = customer.totalPurchases,
            hasPrioritySupport = customer.hasPrioritySupport(),
            freeShippingThreshold = customer.getFreeShippingThreshold(),
            nextTier = customer.tier.getNextTier(),
            progressToNextTier = calculateProgressToNextTier(customer)
        )
    }

    /**
     * Calculate progress to next tier (0.0 to 1.0).
     */
    private fun calculateProgressToNextTier(customer: Customer): Double {
        val nextTier = customer.tier.getNextTier() ?: return 1.0

        val currentThreshold = when (customer.tier) {
            CustomerTier.BRONZE -> BigDecimal.ZERO
            CustomerTier.SILVER -> BigDecimal("500.00")
            CustomerTier.GOLD -> BigDecimal("2000.00")
            CustomerTier.PLATINUM -> return 1.0
        }

        val nextThreshold = when (nextTier) {
            CustomerTier.SILVER -> BigDecimal("500.00")
            CustomerTier.GOLD -> BigDecimal("2000.00")
            CustomerTier.PLATINUM -> BigDecimal("5000.00")
            else -> return 1.0
        }

        val progress = customer.totalPurchases - currentThreshold
        val required = nextThreshold - currentThreshold

        return (progress.toDouble() / required.toDouble()).coerceIn(0.0, 1.0)
    }

    /**
     * Send tier upgrade notification email.
     */
    private fun sendTierUpgradeNotification(
        customer: Customer,
        previousTier: CustomerTier,
        newTier: CustomerTier
    ) {
        logger.info(
            "Sending tier upgrade notification to {}",
            customer.email
        )

        // Implementation would call NotificationService
        // notificationService.sendTierUpgradeEmail(...)
    }

    /**
     * Create new customer account.
     */
    fun createCustomer(
        email: String,
        firstName: String,
        lastName: String
    ): Customer {
        logger.info("Creating new customer: {}", email)

        val customer = Customer.create(email, firstName, lastName)
        return customerRepository.save(customer)
    }
}
