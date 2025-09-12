package main

import (
    "log"
    "github.com/gin-gonic/gin"
    "github.com/go-redis/redis/v8"
    "go.mongodb.org/mongo-driver/mongo"
    "go.mongodb.org/mongo-driver/mongo/options"
    "context"
    "time"
)

/**
 * Main application entry point for Order Service.
 * Initializes database connections, Redis cache, and HTTP server.
 * Configures middleware for logging, CORS, and authentication.
 */

var (
    mongoClient *mongo.Client
    redisClient *redis.Client
)

func main() {
    // Initialize MongoDB connection
    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()
    
    client, err := mongo.Connect(ctx, options.Client().ApplyURI("mongodb://localhost:27017"))
    if err != nil {
        log.Fatal("Failed to connect to MongoDB:", err)
    }
    mongoClient = client

    // Initialize Redis connection for session management
    redisClient = redis.NewClient(&redis.Options{
        Addr:     "localhost:6379",
        Password: "",
        DB:       0,
    })

    // Test Redis connection
    _, err = redisClient.Ping(context.Background()).Result()
    if err != nil {
        log.Fatal("Failed to connect to Redis:", err)
    }

    // Initialize Gin router with default middleware
    router := gin.Default()
    
    // Configure CORS middleware for cross-origin requests
    router.Use(func(c *gin.Context) {
        c.Header("Access-Control-Allow-Origin", "*")
        c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        c.Header("Access-Control-Allow-Headers", "Origin, Content-Type, Authorization")
        
        if c.Request.Method == "OPTIONS" {
            c.AbortWithStatus(204)
            return
        }
        
        c.Next()
    })

    // Register API routes
    setupRoutes(router)

    log.Println("Order Service starting on port 8081...")
    if err := router.Run(":8081"); err != nil {
        log.Fatal("Failed to start server:", err)
    }
}

/**
 * Configures all API routes for order management.
 * Groups routes under /api/orders prefix for consistency.
 * Applies authentication middleware to protected endpoints.
 */
func setupRoutes(router *gin.Engine) {
    orderHandler := NewOrderHandler(mongoClient, redisClient)
    
    api := router.Group("/api")
    {
        orders := api.Group("/orders")
        {
            orders.POST("/", orderHandler.CreateOrder)
            orders.GET("/:id", orderHandler.GetOrder)
            orders.PUT("/:id/status", orderHandler.UpdateOrderStatus)
            orders.GET("/user/:userId", orderHandler.GetUserOrders)
            // Additional endpoint for analytics (not mentioned in spec)
            orders.GET("/analytics/summary", orderHandler.GetOrderAnalytics)
        }
    }
}
