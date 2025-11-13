/**
 * Shipping cost calculation utility.
 *
 * Calculates shipping costs based on distance, weight, and customer tier.
 *
 * Referenced by:
 * - CheckoutFlow.tsx: Shipping cost display
 * - ShippingService.py: Server-side shipping calculations
 *
 * See shipping-process.md for shipping rules.
 */

/**
 * Calculate shipping cost based on origin, destination, and package weight.
 *
 * Algorithm:
 * 1. Calculate distance between origin and destination
 * 2. Apply base rate + per-mile rate + per-pound rate
 * 3. Apply customer tier free shipping thresholds
 *
 * @param {object} origin - Origin address
 * @param {object} destination - Destination address
 * @param {number} weight - Package weight in pounds
 * @param {string} customerTier - Customer tier (BRONZE, SILVER, GOLD, PLATINUM)
 * @param {number} orderTotal - Order total amount
 * @returns {number} Shipping cost in USD
 */
export function calculateShippingCost(
  origin,
  destination,
  weight,
  customerTier = 'BRONZE',
  orderTotal = 0
) {
  // Check free shipping threshold by tier
  const freeShippingThreshold = getFreeShippingThreshold(customerTier);
  if (orderTotal >= freeShippingThreshold) {
    return 0; // Free shipping
  }

  // Calculate distance
  const distance = calculateDistance(origin, destination);

  // Shipping rates
  const baseRate = 5.99;
  const perMileRate = 0.10;
  const perPoundRate = 0.50;

  // Calculate cost
  const distanceCost = distance * perMileRate;
  const weightCost = weight * perPoundRate;
  const totalCost = baseRate + distanceCost + weightCost;

  // Round to 2 decimal places
  return Math.round(totalCost * 100) / 100;
}

/**
 * Calculate distance between two addresses in miles.
 *
 * Uses Haversine formula for great-circle distance.
 *
 * @param {object} origin - Origin coordinates {lat, lng}
 * @param {object} destination - Destination coordinates {lat, lng}
 * @returns {number} Distance in miles
 */
export function calculateDistance(origin, destination) {
  const R = 3959; // Earth radius in miles

  const lat1 = toRadians(origin.lat);
  const lat2 = toRadians(destination.lat);
  const deltaLat = toRadians(destination.lat - origin.lat);
  const deltaLng = toRadians(destination.lng - origin.lng);

  const a = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
            Math.cos(lat1) * Math.cos(lat2) *
            Math.sin(deltaLng / 2) * Math.sin(deltaLng / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
}

/**
 * Get free shipping threshold by customer tier.
 *
 * Maps to Customer.kt getFreeShippingThreshold() method.
 *
 * @param {string} tier - Customer tier
 * @returns {number} Threshold amount for free shipping
 */
export function getFreeShippingThreshold(tier) {
  const thresholds = {
    'BRONZE': 50.00,    // Free shipping on $50+ orders
    'SILVER': 35.00,    // Free shipping on $35+ orders
    'GOLD': 0,          // Free shipping on all orders
    'PLATINUM': 0       // Free express shipping on all orders
  };

  return thresholds[tier] || 50.00;
}

/**
 * Calculate estimated delivery date.
 *
 * @param {number} distance - Shipping distance in miles
 * @param {string} tier - Customer tier for express shipping
 * @returns {Date} Estimated delivery date
 */
export function calculateDeliveryDate(distance, tier = 'BRONZE') {
  const today = new Date();
  let daysToDeliver;

  // PLATINUM gets express shipping (1-2 days)
  if (tier === 'PLATINUM') {
    daysToDeliver = distance < 500 ? 1 : 2;
  }
  // Standard shipping (3-7 days based on distance)
  else if (distance < 100) {
    daysToDeliver = 3;
  } else if (distance < 500) {
    daysToDeliver = 5;
  } else {
    daysToDeliver = 7;
  }

  const deliveryDate = new Date(today);
  deliveryDate.setDate(today.getDate() + daysToDeliver);

  return deliveryDate;
}

/**
 * Convert degrees to radians.
 */
function toRadians(degrees) {
  return degrees * (Math.PI / 180);
}
