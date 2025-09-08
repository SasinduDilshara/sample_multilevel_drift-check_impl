package com.ecommerce.order;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Comprehensive order processing service handling the complete order lifecycle
 * from creation to fulfillment. Implements business logic for order validation,
 * payment coordination, inventory management, and shipping integration.
 * 
 * This service follows the organizational architecture guidelines for microservices
 * and implements proper error handling, logging, and transaction management.
 * 
 * @author E-Commerce Development Team
 * @version 1.0
 * @since 2024-01-01
 */
@Service
@Transactional
public class OrderService {
    
    private static final Logger logger = LoggerFactory.getLogger(OrderService.class);
    
    // Service dependencies injected via Spring dependency injection
    @Autowired
    private OrderRepository orderRepository;
    
    @Autowired
    private InventoryService inventoryService;
    
    @Autowired
    private PaymentService paymentService;
    
    @Autowired
    private ShippingService shippingService;
    
    @Autowired
    private NotificationService notificationService;
    
    @Autowired
    private EventPublisher eventPublisher;
    
    // Configuration constants for order processing business rules
    private static final BigDecimal MINIMUM_ORDER_AMOUNT = new BigDecimal("10.00");
    private static final BigDecimal MAXIMUM_ORDER_AMOUNT = new BigDecimal("50000.00");
    private static final int MAX_ITEMS_PER_ORDER = 100;
    private static final int ORDER_EXPIRY_HOURS = 24;
    
    /**
     * Creates a new order with comprehensive validation and processing
     * Validates customer information, inventory availability, and payment details
     * Implements proper error handling and transaction rollback on failures
     * 
     * @param orderRequest Contains customer details, items, and payment information
     * @return OrderResponse with order details and processing status
     * @throws OrderValidationException when order data validation fails
     * @throws InsufficientInventoryException when items are out of stock
     * @throws PaymentProcessingException when payment authorization fails
     */
    public OrderResponse createOrder(OrderRequest orderRequest) throws OrderValidationException, 
            InsufficientInventoryException, PaymentProcessingException {
        
        logger.info("Creating new order for customer: {}", orderRequest.getCustomerId());
        
        // Validate order request data against business rules and constraints
        validateOrderRequest(orderRequest);
        
        // Generate unique order identifier for tracking and reference
        String orderId = generateOrderId();
        logger.debug("Generated order ID: {}", orderId);
        
        // Calculate comprehensive order totals including taxes and discounts
        OrderTotals orderTotals = calculateOrderTotals(orderRequest);
        logger.info("Order totals calculated - Subtotal: {}, Tax: {}, Total: {}", 
                   orderTotals.getSubtotal(), orderTotals.getTax(), orderTotals.getTotal());
        
        // Reserve inventory for all order items to prevent overselling
        Map<String, Integer> inventoryReservations = reserveInventoryForOrder(orderRequest.getItems());
        logger.info("Inventory reserved for {} items", inventoryReservations.size());
        
        try {
            // Authorize payment for the calculated order total
            PaymentAuthorizationResult paymentAuth = authorizePayment(orderRequest, orderTotals);
            logger.info("Payment authorized with transaction ID: {}", paymentAuth.getTransactionId());
            
            // Create order entity with all calculated information
            Order order = buildOrderEntity(orderId, orderRequest, orderTotals, paymentAuth);
            
            // Persist order to database with proper transaction handling
            Order savedOrder = orderRepository.save(order);
            logger.info("Order saved to database with ID: {}", savedOrder.getOrderId());
            
            // Send order confirmation notification to customer
            notificationService.sendOrderConfirmation(savedOrder);
            
            // Publish order created event for other microservices
            eventPublisher.publishOrderCreatedEvent(savedOrder);
            
            // Initiate asynchronous fulfillment process
            CompletableFuture.runAsync(() -> initiateOrderFulfillment(savedOrder));
            
            return buildOrderResponse(savedOrder);
            
        } catch (Exception e) {
            // Rollback inventory reservations on any failure
            releaseInventoryReservations(inventoryReservations);
            logger.error("Order creation failed, inventory reservations released", e);
            throw e;
        }
    }
    
    /**
     * Retrieves order details by order identifier
     * Includes comprehensive order information and current status
     * Implements proper authorization to ensure customers can only view their orders
     * 
     * @param orderId Unique identifier of the order to retrieve
     * @param customerId Customer identifier for authorization validation
     * @return OrderDetails Complete order information including items and status
     * @throws OrderNotFoundException when order is not found
     * @throws UnauthorizedAccessException when customer lacks access rights
     */
    public OrderDetails getOrderDetails(String orderId, String customerId) 
            throws OrderNotFoundException, UnauthorizedAccessException {
        
        logger.info("Retrieving order details for order: {} by customer: {}", orderId, customerId);
        
        // Fetch order from database with related entities
        Optional<Order> orderOptional = orderRepository.findByOrderIdWithItems(orderId);
        if (orderOptional.isEmpty()) {
            logger.warn("Order not found: {}", orderId);
            throw new OrderNotFoundException("Order not found with ID: " + orderId);
        }
        
        Order order = orderOptional.get();
        
        // Validate customer has permission to view this order
        if (!order.getCustomerId().equals(customerId) && !isAdminUser(customerId)) {
            logger.warn("Unauthorized access attempt to order: {} by customer: {}", orderId, customerId);
            throw new UnauthorizedAccessException("Customer not authorized to view this order");
        }
        
        // Track order view for analytics and customer service
        trackOrderView(orderId, customerId);
        
        // Build comprehensive order details response
        OrderDetails orderDetails = buildOrderDetails(order);
        
        logger.debug("Order details retrieved successfully for order: {}", orderId);
        return orderDetails;
    }
    
    /**
     * Updates order status through the defined state machine workflow
     * Ensures only valid state transitions are allowed
     * Triggers appropriate notifications and events for status changes
     * 
     * @param orderId Unique identifier of the order to update
     * @param newStatus Target status for the order transition
     * @param updateReason Reason for the status change for audit trail
     * @return boolean indicating success of the status update operation
     * @throws InvalidStatusTransitionException when status transition is not allowed
     */
    public boolean updateOrderStatus(String orderId, OrderStatus newStatus, String updateReason) 
            throws InvalidStatusTransitionException {
        
        logger.info("Updating order status for order: {} to status: {}", orderId, newStatus);
        
        // Retrieve current order state from database
        Order order = orderRepository.findByOrderId(orderId)
                .orElseThrow(() -> new OrderNotFoundException("Order not found: " + orderId));
        
        OrderStatus currentStatus = order.getStatus();
        
        // Validate status transition is allowed according to business rules
        if (!isValidStatusTransition(currentStatus, newStatus)) {
            logger.error("Invalid status transition from {} to {} for order: {}", 
                        currentStatus, newStatus, orderId);
            throw new InvalidStatusTransitionException(
                String.format("Cannot transition from %s to %s", currentStatus, newStatus));
        }
        
        // Update order status with timestamp and reason
        order.setStatus(newStatus);
        order.setLastUpdated(LocalDateTime.now());
        order.addStatusHistory(currentStatus, newStatus, updateReason);
        
        // Persist status update to database
        orderRepository.save(order);
        
        // Send status update notification to customer
        notificationService.sendStatusUpdateNotification(order);
        
        // Publish status change event for other services
        eventPublisher.publishOrderStatusChangedEvent(order, currentStatus, newStatus);
        
        // Execute status-specific business logic
        executeStatusSpecificActions(order, newStatus);
        
        logger.info("Order status updated successfully for order: {}", orderId);
        return true;
    }
    
    /**
     * Processes order cancellation with proper validation and cleanup
     * Handles refund processing and inventory restoration
     * Implements different cancellation policies based on order status
     * 
     * @param orderId Unique identifier of the order to cancel
     * @param customerId Customer requesting the cancellation
     * @param cancellationReason Reason for order cancellation
     * @return CancellationResult with refund information and processing status
     * @throws OrderCancellationException when cancellation is not allowed
     */
    public CancellationResult cancelOrder(String orderId, String customerId, String cancellationReason) 
            throws OrderCancellationException {
        
        logger.info("Processing order cancellation for order: {} by customer: {}", orderId, customerId);
        
        // Retrieve order and validate cancellation eligibility
        Order order = orderRepository.findByOrderId(orderId)
                .orElseThrow(() -> new OrderNotFoundException("Order not found: " + orderId));
        
        // Validate customer authorization for cancellation
        if (!order.getCustomerId().equals(customerId) && !isAdminUser(customerId)) {
            throw new OrderCancellationException("Customer not authorized to cancel this order");
        }
        
        // Check if order status allows cancellation
        if (!isCancellationAllowed(order.getStatus())) {
            throw new OrderCancellationException(
                "Order cannot be cancelled in current status: " + order.getStatus());
        }
        
        // Calculate refund amount based on cancellation policy
        BigDecimal refundAmount = calculateRefundAmount(order);
        logger.info("Calculated refund amount: {} for order: {}", refundAmount, orderId);
        
        // Process refund through payment service
        RefundResult refundResult = null;
        if (refundAmount.compareTo(BigDecimal.ZERO) > 0) {
            refundResult = paymentService.processRefund(order.getPaymentTransactionId(), refundAmount);
            logger.info("Refund processed with transaction ID: {}", refundResult.getRefundTransactionId());
        }
        
        // Restore inventory for cancelled order items
        restoreInventoryForOrder(order.getItems());
        
        // Update order status to cancelled
        order.setStatus(OrderStatus.CANCELLED);
        order.setCancellationReason(cancellationReason);
        order.setCancelledAt(LocalDateTime.now());
        order.setLastUpdated(LocalDateTime.now());
        
        // Persist cancellation to database
        orderRepository.save(order);
        
        // Send cancellation confirmation to customer
        notificationService.sendCancellationConfirmation(order, refundResult);
        
        // Publish order cancelled event
        eventPublisher.publishOrderCancelledEvent(order, cancellationReason);
        
        logger.info("Order cancellation completed successfully for order: {}", orderId);
        
        return CancellationResult.builder()
                .orderId(orderId)
                .refundAmount(refundAmount)
                .refundTransactionId(refundResult != null ? refundResult.getRefundTransactionId() : null)
                .estimatedRefundDays(getEstimatedRefundDays(order.getPaymentMethod()))
                .build();
    }
    
    /**
     * Retrieves order history for a customer with filtering and pagination
     * Supports filtering by date range, status, and other criteria
     * Implements proper data access controls and performance optimization
     * 
     * @param customerId Customer identifier for order history lookup
     * @param filterCriteria Optional filtering criteria for order history
     * @param pagination Pagination parameters for large result sets
     * @return OrderHistoryResponse with filtered and paginated order list
     */
    public OrderHistoryResponse getOrderHistory(String customerId, OrderFilterCriteria filterCriteria, 
            PaginationRequest pagination) {
        
        logger.info("Retrieving order history for customer: {} with {} filters", 
                   customerId, filterCriteria.getActiveFilterCount());
        
        // Build database query with filtering and pagination
        OrderQueryBuilder queryBuilder = new OrderQueryBuilder()
                .forCustomer(customerId)
                .withFilters(filterCriteria)
                .withPagination(pagination)
                .includingTotals();
        
        // Execute query with performance optimization
        List<Order> orders = orderRepository.findWithQuery(queryBuilder.build());
        int totalCount = orderRepository.countWithQuery(queryBuilder.buildCountQuery());
        
        // Transform orders to response DTOs with minimal data
        List<OrderSummary> orderSummaries = orders.stream()
                .map(this::buildOrderSummary)
                .collect(Collectors.toList());
        
        // Calculate summary statistics for the response
        OrderStatistics statistics = calculateOrderStatistics(orders);
        
        logger.debug("Retrieved {} orders out of {} total for customer: {}", 
                    orders.size(), totalCount, customerId);
        
        return OrderHistoryResponse.builder()
                .orders(orderSummaries)
                .totalCount(totalCount)
                .currentPage(pagination.getPage())
                .totalPages((totalCount + pagination.getSize() - 1) / pagination.getSize())
                .statistics(statistics)
                .build();
    }
    
    // Private helper methods for order processing
    
    private void validateOrderRequest(OrderRequest request) throws OrderValidationException {
        // Comprehensive validation of order request data
        List<String> validationErrors = new ArrayList<>();
        
        if (request.getCustomerId() == null || request.getCustomerId().trim().isEmpty()) {
            validationErrors.add("Customer ID is required");
        }
        
        if (request.getItems() == null || request.getItems().isEmpty()) {
            validationErrors.add("Order must contain at least one item");
        }
        
        if (request.getItems() != null && request.getItems().size() > MAX_ITEMS_PER_ORDER) {
            validationErrors.add("Order cannot contain more than " + MAX_ITEMS_PER_ORDER + " items");
        }
        
        // Validate shipping address is complete
        if (request.getShippingAddress() == null || !isValidAddress(request.getShippingAddress())) {
            validationErrors.add("Valid shipping address is required");
        }
        
        // Validate payment information is present
        if (request.getPaymentMethod() == null) {
            validationErrors.add("Payment method is required");
        }
        
        if (!validationErrors.isEmpty()) {
            throw new OrderValidationException("Order validation failed", validationErrors);
        }
    }
    
    private OrderTotals calculateOrderTotals(OrderRequest request) {
        // Calculate subtotal from all order items
        BigDecimal subtotal = request.getItems().stream()
                .map(item -> item.getPrice().multiply(BigDecimal.valueOf(item.getQuantity())))
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        
        // Apply discounts if any promotional codes are provided
        BigDecimal discount = calculateDiscounts(request.getPromotionalCodes(), subtotal);
        
        // Calculate shipping costs based on address and items
        BigDecimal shipping = shippingService.calculateShippingCost(
                request.getShippingAddress(), request.getItems());
        
        // Calculate taxes based on shipping address jurisdiction
        BigDecimal tax = calculateTaxes(subtotal.subtract(discount), request.getShippingAddress());
        
        // Calculate final total amount
        BigDecimal total = subtotal.subtract(discount).add(shipping).add(tax);
        
        return OrderTotals.builder()
                .subtotal(subtotal)
                .discount(discount)
                .shipping(shipping)
                .tax(tax)
                .total(total)
                .build();
    }
    
    private String generateOrderId() {
        // Generate unique order identifier with timestamp and random component
        return "ORD-" + System.currentTimeMillis() + "-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
    }
    
    // Additional private helper methods would be implemented for:
    // - reserveInventoryForOrder()
    // - authorizePayment()
    // - buildOrderEntity()
    // - buildOrderResponse()
    // - initiateOrderFulfillment()
    // - isValidStatusTransition()
    // - executeStatusSpecificActions()
    // - isCancellationAllowed()
    // - calculateRefundAmount()
    // - restoreInventoryForOrder()
    // - calculateDiscounts()
    // - calculateTaxes()
    // - isValidAddress()
    // - buildOrderDetails()
    // - buildOrderSummary()
    // - calculateOrderStatistics()
}
