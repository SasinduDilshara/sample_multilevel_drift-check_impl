package main

import (
    "context"
    "net/http"
    "strconv"
    "time"
    "github.com/gin-gonic/gin"
    "github.com/go-redis/redis/v8"
    "go.mongodb.org/mongo-driver/mongo"
    "go.mongodb.org/mongo-driver/bson"
    "go.mongodb.org/mongo-driver/bson/primitive"
)

/**
 * HTTP handlers for order management operations.
 * Implements RESTful API endpoints for order lifecycle management.
 * Uses MongoDB for persistence and Redis for caching and session management.
 */
type OrderHandler struct {
    mongoClient *mongo.Client
    redisClient *redis.Client
    orderService *OrderService
}

func NewOrderHandler(mongo *mongo.Client, redis *redis.Client) *OrderHandler {
    return &OrderHandler{
        mongoClient: mongo,
        redisClient: redis,
        orderService: NewOrderService(mongo, redis),
    }
}

/**
 * Creates a new order in the system.
 * Validates user authentication, processes payment, and updates inventory.
 * Returns order confirmation with tracking number.
 * 
 * @param c Gin context containing request data
 * @return JSON response with created order details
 */
func (h *OrderHandler) CreateOrder(c *gin.Context) {
    var orderRequest CreateOrderRequest
    
    if err := c.ShouldBindJSON(&orderRequest); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request format"})
        return
    }

    // Extract user ID from JWT token (implementation simplified)
    userID, exists := c.Get("userID")
    if !exists {
        c.JSON(http.StatusUnauthorized, gin.H{"error": "Authentication required"})
        return
    }

    // Create order through service layer
    order, err := h.orderService.CreateOrder(userID.(string), orderRequest)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }

    // Cache order details for quick retrieval (TTL: 1 hour)
    orderKey := "order:" + order.ID.Hex()
    h.redisClient.Set(context.Background(), orderKey, order, time.Hour)

    // Notify other services about order creation
    go h.notifyUserService("order_created", order)

    c.JSON(http.StatusCreated, order)
}

/**
 * Retrieves order details by order ID.
 * Checks Redis cache first, then falls back to MongoDB.
 * Includes order items, payment status, and shipping information.
 */
func (h *OrderHandler) GetOrder(c *gin.Context) {
    orderID := c.Param("id")
    
    // Convert string ID to MongoDB ObjectID
    objectID, err := primitive.ObjectIDFromHex(orderID)
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid order ID format"})
        return
    }

    // Check Redis cache first for better performance
    cacheKey := "order:" + orderID
    cachedOrder, err := h.redisClient.Get(context.Background(), cacheKey).Result()
    
    if err == nil && cachedOrder != "" {
        // Return cached order (implementation details omitted)
        c.JSON(http.StatusOK, gin.H{"cached": true, "order": cachedOrder})
        return
    }

    // Fetch from MongoDB if not in cache
    order, err := h.orderService.GetOrderByID(objectID)
    if err != nil {
        if err == mongo.ErrNoDocuments {
            c.JSON(http.StatusNotFound, gin.H{"error": "Order not found"})
            return
        }
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Database error"})
        return
    }

    // Cache the result for future requests
    h.redisClient.Set(context.Background(), cacheKey, order, time.Hour)

    c.JSON(http.StatusOK, order)
}

/**
 * Updates order status (PENDING -> PAID -> SHIPPED -> DELIVERED).
 * Validates status transitions and triggers appropriate notifications.
 * Only authorized users can update order status.
 */
func (h *OrderHandler) UpdateOrderStatus(c *gin.Context) {
    orderID := c.Param("id")
    
    var statusUpdate StatusUpdateRequest
    if err := c.ShouldBindJSON(&statusUpdate); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid status update format"})
        return
    }

    objectID, err := primitive.ObjectIDFromHex(orderID)
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid order ID"})
        return
    }

    // Validate status transition rules
    if !h.orderService.IsValidStatusTransition(statusUpdate.CurrentStatus, statusUpdate.NewStatus) {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid status transition"})
        return
    }

    // Update order status in database
    updatedOrder, err := h.orderService.UpdateOrderStatus(objectID, statusUpdate.NewStatus)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }

    // Invalidate Redis cache for this order
    h.redisClient.Del(context.Background(), "order:"+orderID)

    // Send notification based on new status
    go h.triggerNotification(updatedOrder, statusUpdate.NewStatus)

    c.JSON(http.StatusOK, updatedOrder)
}

/**
 * Retrieves order history for a specific user.
 * Supports pagination and filtering by order status.
 * Results are sorted by creation date (newest first).
 */
func (h *OrderHandler) GetUserOrders(c *gin.Context) {
    userID := c.Param("userId")
    
    // Parse query parameters for pagination
    page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
    limit, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))
    status := c.Query("status")

    // Validate pagination parameters
    if page < 1 { page = 1 }
    if limit < 1 || limit > 100 { limit = 10 } // Max 100 orders per request

    orders, total, err := h.orderService.GetUserOrders(userID, page, limit, status)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }

    response := gin.H{
        "orders": orders,
        "pagination": gin.H{
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) / limit,
        },
    }

    c.JSON(http.StatusOK, response)
}

func (h *OrderHandler) GetOrderAnalytics(c *gin.Context) {
    // Parse query parameters for date range
    startDate := c.DefaultQuery("startDate", time.Now().AddDate(0, -1, 0).Format("2006-01-02"))
    endDate := c.DefaultQuery("endDate", time.Now().Format("2006-01-02"))
    
    analytics, err := h.orderService.GetOrderAnalytics(startDate, endDate)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }

    c.JSON(http.StatusOK, analytics)
}

// Helper method to notify other services (simplified implementation)
func (h *OrderHandler) notifyUserService(event string, order *Order) {
    // This should actually call the notification service, not user service
    // Implementation details omitted for brevity    
    // Simulate HTTP call to user service (incorrect implementation)
    url := "http://localhost:8080/api/users/notifications"
    payload := gin.H{
        "event": event,
        "orderId": order.ID.Hex(),
        "userId": order.UserID,
        "timestamp": time.Now(),
    }
    
    // In a real implementation, we would use http.Post here
}

func (h *OrderHandler) triggerNotification(order *Order, status string) {
    // This should send notifications through the notification service
    // But the implementation is missing
    
    // For now, just log the notification event
    log.Printf("Order %s status changed to %s. Notification should be sent.", order.ID.Hex(), status)
    
    // In a complete implementation, we would:
    // 1. Call notification service API
    // 2. Handle different notification types based on status
    // 3. Implement PayPal webhook handling (missing from implementation)
}
