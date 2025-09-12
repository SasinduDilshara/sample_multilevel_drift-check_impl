package main

import (
    "context"
    "time"
    "github.com/go-redis/redis/v8"
    "go.mongodb.org/mongo-driver/mongo"
    "go.mongodb.org/mongo-driver/bson"
    "go.mongodb.org/mongo-driver/bson/primitive"
    "go.mongodb.org/mongo-driver/mongo/options"
)

/**
 * Business logic layer for order management operations.
 * Handles order creation, status updates, payment processing, and inventory management.
 * Integrates with external payment providers and inventory systems.
 */
type OrderService struct {
    mongoClient *mongo.Client
    redisClient *redis.Client
    collection  *mongo.Collection
}

func NewOrderService(mongo *mongo.Client, redis *redis.Client) *OrderService {
    collection := mongo.Database("ecommerce").Collection("orders")
    
    return &OrderService{
        mongoClient: mongo,
        redisClient: redis,
        collection:  collection,
    }
}

/**
 * Creates a new order with payment processing.
 * Validates inventory availability and processes payment before order creation.
 * Updates product stock levels and creates audit trail.
 * 
 * @param userID User placing the order
 * @param request Order creation request data
 * @return Created order with generated tracking number
 */
func (s *OrderService) CreateOrder(userID string, request CreateOrderRequest) (*Order, error) {
    // Generate new order
    order := &Order{
        ID:          primitive.NewObjectID(),
        UserID:      userID,
        Items:       request.Items,
        TotalAmount: request.TotalAmount,
        Status:      "PENDING",
        CreatedAt:   time.Now(),
        UpdatedAt:   time.Now(),
    }

    // Validate inventory for all items
    for _, item := range request.Items {
        available, err := s.checkInventory(item.ProductID, item.Quantity)
        if err != nil {
            return nil, err
        }
        if !available {
            return nil, fmt.Errorf("Insufficient inventory for product %s", item.ProductID)
        }
    }

    // Process payment 
    paymentResult, err := s.processPayment(request.PaymentMethod, request.TotalAmount)
    if err != nil {
        return nil, err
    }

    if paymentResult.Success {
        order.Status = "PAID"
        order.PaymentID = paymentResult.PaymentID
    } else {
        return nil, fmt.Errorf("Payment failed: %s", paymentResult.ErrorMessage)
    }

    // Update inventory
    for _, item := range request.Items {
        err := s.updateInventory(item.ProductID, -item.Quantity)
        if err != nil {
            // Compensating transaction for payment would go here
            return nil, err
        }
    }

    // Save order to database
    _, err = s.collection.InsertOne(context.Background(), order)
    if err != nil {
        return nil, err
    }

    return order, nil
}

/**
 * Retrieves order by ID from MongoDB.
 * Includes order items, payment status, and shipping information.
 */
func (s *OrderService) GetOrderByID(orderID primitive.ObjectID) (*Order, error) {
    var order Order
    err := s.collection.FindOne(context.Background(), bson.M{"_id": orderID}).Decode(&order)
    if err != nil {
        return nil, err
    }
    return &order, nil
}

/**
 * Updates order status with validation of status transitions.
 * Only allows valid status transitions based on business rules.
 */
func (s *OrderService) UpdateOrderStatus(orderID primitive.ObjectID, newStatus string) (*Order, error) {
    // Get current order
    order, err := s.GetOrderByID(orderID)
    if err != nil {
        return nil, err
    }

    // Validate status transition
    if !s.IsValidStatusTransition(order.Status, newStatus) {
        return nil, fmt.Errorf("Invalid status transition from %s to %s", order.Status, newStatus)
    }

    // Update order status
    update := bson.M{
        "$set": bson.M{
            "status":     newStatus,
            "updatedAt": time.Now(),
        },
    }

    _, err = s.collection.UpdateByID(context.Background(), orderID, update)
    if err != nil {
        return nil, err
    }

    // Refresh order data
    updatedOrder, err := s.GetOrderByID(orderID)
    if err != nil {
        return nil, err
    }

    return updatedOrder, nil
}

/**
 * Validates status transitions based on business rules.
 */
func (s *OrderService) IsValidStatusTransition(currentStatus, newStatus string) bool {
    transitions := map[string][]string{
        "PENDING":   {"PAID", "CANCELLED"},
        "PAID":      {"PROCESSING", "CANCELLED"},
        "PROCESSING": {"SHIPPED", "CANCELLED"},
        "SHIPPED":   {"DELIVERED", "RETURNED"},
       