package com.ecommerce.order;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;
import org.springframework.stereotype.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Utility class for order-related calculations and business logic operations
 * Provides reusable methods for pricing, tax calculations, and order validation
 * Implements organizational standards for calculation accuracy and error handling
 * 
 * Note: This implementation uses simple tax calculation logic but production
 * systems should integrate with specialized tax calculation services
 * 
 * @author E-Commerce Development Team
 * @version 1.0
 */
@Component
public class OrderUtils {
    
    private static final Logger logger = LoggerFactory.getLogger(OrderUtils.class);
    
    // Tax calculation constants - these should be externalized to configuration
    private static final BigDecimal DEFAULT_TAX_RATE = new BigDecimal("0.08");
    private static final BigDecimal LUXURY_TAX_THRESHOLD = new BigDecimal("1000.00");
    private static final BigDecimal LUXURY_TAX_RATE = new BigDecimal("0.15");
    
    // Discount calculation constants
    private static final BigDecimal MAX_DISCOUNT_PERCENTAGE = new BigDecimal("0.50");
    private static final Map<String, BigDecimal> PROMOTIONAL_CODES = Map.of(
        "SAVE10", new BigDecimal("0.10"),
        "WELCOME15", new BigDecimal("0.15"),
        "BULK20", new BigDecimal("0.20")
    );
    
    /**
     * Calculates comprehensive tax amount for order based on shipping address
     * Implements multi-jurisdictional tax logic with special handling for luxury items
     * Uses address-based tax lookup with fallback to default rates
     * 
     * @param subtotal Order subtotal before tax calculation
     * @param shippingAddress Customer shipping address for tax jurisdiction
     * @return BigDecimal tax amount calculated based on applicable rates
     */
    public BigDecimal calculateOrderTax(BigDecimal subtotal, Address shippingAddress) {
        logger.debug("Calculating tax for subtotal: {} in jurisdiction: {}", 
                    subtotal, shippingAddress.getState());
        
        // Validate input parameters to prevent calculation errors
        if (subtotal == null || subtotal.compareTo(BigDecimal.ZERO) < 0) {
            logger.warn("Invalid subtotal provided for tax calculation: {}", subtotal);
            return BigDecimal.ZERO;
        }
        
        if (shippingAddress == null || shippingAddress.getState() == null) {
            logger.warn("Invalid shipping address provided, using default tax rate");
            return subtotal.multiply(DEFAULT_TAX_RATE);
        }
        
        // Determine applicable tax rate based on shipping state/province
        BigDecimal applicableTaxRate = getTaxRateForState(shippingAddress.getState());
        
        // Apply luxury tax for high-value orders in applicable jurisdictions
        if (subtotal.compareTo(LUXURY_TAX_THRESHOLD) > 0 && isLuxuryTaxApplicable(shippingAddress)) {
            logger.info("Applying luxury tax for high-value order: {}", subtotal);
            applicableTaxRate = LUXURY_TAX_RATE;
        }
        
        // Calculate final tax amount with proper rounding
        BigDecimal taxAmount = subtotal.multiply(applicableTaxRate)
                .setScale(2, BigDecimal.ROUND_HALF_UP);
        
        logger.debug("Tax calculated: {} (rate: {})", taxAmount, applicableTaxRate);
        return taxAmount;
    }
    
    /**
     * Applies promotional discounts to order subtotal with validation
     * Supports multiple promotional codes with stacking rules
     * Implements maximum discount limits to prevent abuse
     * 
     * @param promotionalCodes List of promotional codes to apply
     * @param subtotal Order subtotal before discount application
     * @return BigDecimal total discount amount applied to order
     */
    public BigDecimal applyPromotionalDiscounts(List<String> promotionalCodes, BigDecimal subtotal) {
        logger.info("Applying promotional discounts for codes: {}", promotionalCodes);
        
        if (promotionalCodes == null || promotionalCodes.isEmpty()) {
            return BigDecimal.ZERO;
        }
        
        BigDecimal totalDiscount = BigDecimal.ZERO;
        
        // Process each promotional code and accumulate discounts
        for (String code : promotionalCodes) {
            if (code == null || code.trim().isEmpty()) {
                continue;
            }
            
            String normalizedCode = code.trim().toUpperCase();
            
            // Validate promotional code exists and is active
            if (!PROMOTIONAL_CODES.containsKey(normalizedCode)) {
                logger.warn("Invalid promotional code provided: {}", normalizedCode);
                continue;
            }
            
            // Calculate discount for this promotional code
            BigDecimal discountRate = PROMOTIONAL_CODES.get(normalizedCode);
            BigDecimal codeDiscount = subtotal.multiply(discountRate);
            
            totalDiscount = totalDiscount.add(codeDiscount);
            logger.debug("Applied discount: {} for code: {}", codeDiscount, normalizedCode);
        }
        
        // Enforce maximum discount percentage to prevent abuse
        BigDecimal maxAllowedDiscount = subtotal.multiply(MAX_DISCOUNT_PERCENTAGE);
        if (totalDiscount.compareTo(maxAllowedDiscount) > 0) {
            logger.warn("Total discount {} exceeds maximum allowed {}, capping discount", 
                       totalDiscount, maxAllowedDiscount);
            totalDiscount = maxAllowedDiscount;
        }
        
        logger.info("Total promotional discount applied: {}", totalDiscount);
        return totalDiscount.setScale(2, BigDecimal.ROUND_HALF_UP);
    }
    
    /**
     * Validates order items for business rule compliance
     * Checks inventory availability, pricing accuracy, and quantity limits
     * Implements comprehensive validation with detailed error reporting
     * 
     * @param orderItems List of items in the order to validate
     * @return OrderValidationResult containing validation status and any errors
     */
    public OrderValidationResult validateOrderItems(List<OrderItem> orderItems) {
        logger.debug("Validating {} order items", orderItems.size());
        
        List<String> validationErrors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();
        
        if (orderItems == null || orderItems.isEmpty()) {
            validationErrors.add("Order must contain at least one item");
            return new OrderValidationResult(false, validationErrors, warnings);
        }
        
        BigDecimal totalOrderValue = BigDecimal.ZERO;
        
        // Validate each order item individually
        for (int i = 0; i < orderItems.size(); i++) {
            OrderItem item = orderItems.get(i);
            String itemPrefix = "Item " + (i + 1) + ": ";
            
            // Validate item has required fields
            if (item.getProductId() == null || item.getProductId().trim().isEmpty()) {
                validationErrors.add(itemPrefix + "Product ID is required");
                continue;
            }
            
            // Validate quantity is positive and within limits
            if (item.getQuantity() <= 0) {
                validationErrors.add(itemPrefix + "Quantity must be greater than zero");
            } else if (item.getQuantity() > 99) {
                validationErrors.add(itemPrefix + "Quantity cannot exceed 99 per item");
            }
            
            // Validate price is positive and reasonable
            if (item.getPrice() == null || item.getPrice().compareTo(BigDecimal.ZERO) <= 0) {
                validationErrors.add(itemPrefix + "Price must be greater than zero");
            } else if (item.getPrice().compareTo(new BigDecimal("10000")) > 0) {
                warnings.add(itemPrefix + "High-value item requires manual review");
            }
            
            // Check inventory availability for this item
            if (!checkInventoryAvailability(item.getProductId(), item.getQuantity())) {
                validationErrors.add(itemPrefix + "Insufficient inventory available");
            }
            
            // Accumulate total order value for validation
            if (item.getPrice() != null) {
                totalOrderValue = totalOrderValue.add(
                    item.getPrice().multiply(BigDecimal.valueOf(item.getQuantity()))
                );
            }
        }
        
        // Validate total order value is within acceptable limits
        if (totalOrderValue.compareTo(new BigDecimal("10.00")) < 0) {
            validationErrors.add("Order total must be at least $10.00");
        } else if (totalOrderValue.compareTo(new BigDecimal("50000.00")) > 0) {
            validationErrors.add("Order total cannot exceed $50,000.00");
        }
        
        boolean isValid = validationErrors.isEmpty();
        logger.debug("Order items validation completed - Valid: {}, Errors: {}, Warnings: {}", 
                    isValid, validationErrors.size(), warnings.size());
        
        return new OrderValidationResult(isValid, validationErrors, warnings);
    }
    
    /**
     * Calculates estimated delivery date based on shipping method and address
     * Considers business days, holidays, and shipping carrier capabilities
     * Provides conservative estimates to ensure customer satisfaction
     * 
     * @param shippingMethod Selected shipping method (standard, express, overnight)
     * @param shippingAddress Destination address for delivery calculation
     * @return LocalDateTime estimated delivery date and time
     */
    public LocalDateTime calculateEstimatedDelivery(String shippingMethod, Address shippingAddress) {
        logger.debug("Calculating delivery estimate for method: {} to state: {}", 
                    shippingMethod, shippingAddress.getState());
        
        LocalDateTime orderDate = LocalDateTime.now();
        int deliveryDays;
        
        // Determine delivery timeframe based on shipping method
        switch (shippingMethod.toLowerCase()) {
            case "overnight":
                deliveryDays = 1;
                break;
            case "express":
                deliveryDays = 2;
                break;
            case "priority":
                deliveryDays = 3;
                break;
            case "standard":
            default:
                deliveryDays = 5;
                break;
        }
        
        // Add extra days for remote locations
        if (isRemoteLocation(shippingAddress)) {
            deliveryDays += 2;
            logger.debug("Added 2 days for remote location delivery");
        }
        
        // Calculate delivery date excluding weekends and holidays
        LocalDateTime estimatedDelivery = orderDate;
        int businessDaysAdded = 0;
        
        while (businessDaysAdded < deliveryDays) {
            estimatedDelivery = estimatedDelivery.plusDays(1);
            
            // Skip weekends and holidays in delivery calculation
            if (isBusinessDay(estimatedDelivery)) {
                businessDaysAdded++;
            }
        }
        
        // Set delivery time to end of business day for customer expectations
        estimatedDelivery = estimatedDelivery.withHour(17).withMinute(0).withSecond(0);
        
        logger.info("Estimated delivery: {} for shipping method: {}", estimatedDelivery, shippingMethod);
        return estimatedDelivery;
    }
    
    /**
     * Generates unique order tracking number for shipment tracking
     * Uses timestamp and random components for uniqueness
     * Follows industry standard format for tracking number generation
     * 
     * @param orderId Source order identifier for tracking association
     * @param shippingCarrier Shipping carrier code for tracking format
     * @return String formatted tracking number for shipment tracking
     */
    public String generateTrackingNumber(String orderId, String shippingCarrier) {
        logger.debug("Generating tracking number for order: {} with carrier: {}", orderId, shippingCarrier);
        
        // Use timestamp for uniqueness and traceability
        long timestamp = System.currentTimeMillis();
        
        // Generate random component for additional uniqueness
        Random random = new Random();
        int randomComponent = random.nextInt(9999) + 1000;
        
        // Format tracking number based on carrier requirements
        String trackingNumber;
        switch (shippingCarrier.toUpperCase()) {
            case "UPS":
                trackingNumber = "1Z" + timestamp + randomComponent;
                break;
            case "FEDEX":
                trackingNumber = "FX" + timestamp + randomComponent;
                break;
            case "USPS":
                trackingNumber = "US" + timestamp + randomComponent;
                break;
            default:
                trackingNumber = "TRK" + timestamp + randomComponent;
                break;
        }
        
        logger.info("Generated tracking number: {} for order: {}", trackingNumber, orderId);
        return trackingNumber;
    }
    
    // Private helper methods for supporting calculations
    
    private BigDecimal getTaxRateForState(String state) {
        // Simplified tax rate lookup - production would use tax service
        Map<String, BigDecimal> stateTaxRates = Map.of(
            "CA", new BigDecimal("0.0875"),
            "NY", new BigDecimal("0.08"),
            "TX", new BigDecimal("0.0625"),
            "FL", new BigDecimal("0.06")
        );
        
        return stateTaxRates.getOrDefault(state, DEFAULT_TAX_RATE);
    }
    
    private boolean isLuxuryTaxApplicable(Address address) {
        // Luxury tax applies in certain jurisdictions
        Set<String> luxuryTaxStates = Set.of("CA", "NY");
        return luxuryTaxStates.contains(address.getState());
    }
    
    private boolean checkInventoryAvailability(String productId, int quantity) {
        // Simplified inventory check - production would query inventory service
        logger.debug("Checking inventory for product: {} quantity: {}", productId, quantity);
        return true; // Simplified for example
    }
    
    private boolean isRemoteLocation(Address address) {
        // Determine if address is in remote location requiring extra delivery time
        Set<String> remoteStates = Set.of("AK", "HI", "PR");
        return remoteStates.contains(address.getState());
    }
    
    private boolean isBusinessDay(LocalDateTime date) {
        // Check if date falls on business day (Monday-Friday, excluding holidays)
        int dayOfWeek = date.getDayOfWeek().getValue();
        return dayOfWeek >= 1 && dayOfWeek <= 5 && !isHoliday(date);
    }
    
    private boolean isHoliday(LocalDateTime date) {
        // Simplified holiday check - production would use holiday calendar service
        return false;
    }
}

/**
 * Result object for order item validation containing status and error details
 */
class OrderValidationResult {
    private final boolean valid;
    private final List<String> errors;
    private final List<String> warnings;
    
    public OrderValidationResult(boolean valid, List<String> errors, List<String> warnings) {
        this.valid = valid;
        this.errors = new ArrayList<>(errors);
        this.warnings = new ArrayList<>(warnings);
    }
    
    public boolean isValid() { return valid; }
    public List<String> getErrors() { return new ArrayList<>(errors); }
    public List<String> getWarnings() { return new ArrayList<>(warnings); }
}
