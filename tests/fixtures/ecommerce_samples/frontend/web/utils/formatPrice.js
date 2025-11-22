/**
 * Price formatting utility.
 *
 * Formats prices with currency symbol and applies tier discounts.
 *
 * Referenced by:
 * - ProductCard.tsx: Product price display
 * - Cart.tsx: Cart totals
 * - CheckoutFlow.tsx: Order summary
 *
 * See pricing-policy.md for discount rules.
 */

/**
 * Format price with optional tier discount.
 *
 * @param {number} price - Base price
 * @param {number} tierDiscount - Discount rate (0.0 to 1.0)
 * @returns {object} Formatted price object
 *
 * Examples:
 * formatPrice(29.99, 0) → { price: "$29.99" }
 * formatPrice(29.99, 0.10) → {
 *   original: "$29.99",
 *   discounted: "$26.99",
 *   savings: "Save $3.00"
 * }
 */
export function formatPrice(price, tierDiscount = 0) {
  if (typeof price !== 'number' || price < 0) {
    return { price: '$0.00' };
  }

  const originalPrice = price;
  const discountedPrice = price * (1 - tierDiscount);

  // If discount applied, show original and discounted prices
  if (tierDiscount > 0) {
    const savings = originalPrice - discountedPrice;

    return {
      original: `$${originalPrice.toFixed(2)}`,
      discounted: `$${discountedPrice.toFixed(2)}`,
      savings: `Save $${savings.toFixed(2)}`,
      discountPercent: `${(tierDiscount * 100).toFixed(0)}% off`
    };
  }

  // No discount
  return {
    price: `$${price.toFixed(2)}`
  };
}

/**
 * Format price range for variable pricing.
 *
 * @param {number} minPrice - Minimum price
 * @param {number} maxPrice - Maximum price
 * @returns {string} Formatted price range
 */
export function formatPriceRange(minPrice, maxPrice) {
  if (minPrice === maxPrice) {
    return `$${minPrice.toFixed(2)}`;
  }
  return `$${minPrice.toFixed(2)} - $${maxPrice.toFixed(2)}`;
}

/**
 * Calculate tier discount based on customer tier.
 *
 * Maps to CustomerTier.kt enum discount rates.
 *
 * @param {string} tier - Customer tier (BRONZE, SILVER, GOLD, PLATINUM)
 * @returns {number} Discount rate (0.0 to 0.15)
 */
export function getTierDiscount(tier) {
  const discounts = {
    'BRONZE': 0.00,    // 0%
    'SILVER': 0.05,    // 5%
    'GOLD': 0.10,      // 10%
    'PLATINUM': 0.15   // 15%
  };

  return discounts[tier] || 0;
}

/**
 * Format currency amount with thousands separator.
 *
 * @param {number} amount - Amount to format
 * @returns {string} Formatted amount
 */
export function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount);
}
