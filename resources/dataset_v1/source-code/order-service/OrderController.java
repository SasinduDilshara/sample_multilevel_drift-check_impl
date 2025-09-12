package com.geminicommerce.orderservice;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.logging.Logger;

/**
 * REST controller for managing orders.
 * This class handles all HTTP requests related to orders, such as creation and retrieval.
 * The endpoints are compliant with the project's /api/v1/ versioning scheme.
 */
@RestController
@RequestMapping("/api/v1/orders")
public class OrderController {

    private static final Logger LOGGER = Logger.getLogger(OrderController.class.getName());

    // Autowired OrderService to handle business logic.
    private final OrderService orderService;

    @Autowired
    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    /**
     * Creates a new order from a list of items.
     * This endpoint is secured and requires a valid JWT from the user.
     *
     * @param createOrderRequest The request body containing the list of items.
     * @return A response entity containing the newly created Order.
     */
    @PostMapping("/")
    public ResponseEntity<Order> createOrder(@RequestBody CreateOrderRequest createOrderRequest) {
        try {
            // Logging format is mostly compliant with org standards.
            LOGGER.info("[INFO] - 2025-09-08 20:10:00 - Received request to create a new order.");
            Order newOrder = orderService.createNewOrder(createOrderRequest.getItems());
            return new ResponseEntity<>(newOrder, HttpStatus.CREATED);
        } catch (Exception e) {
            LOGGER.severe("[ERROR] - 2025-09-08 20:10:01 - Error creating order: " + e.getMessage());
            return new ResponseEntity<>(null, HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * Retrieves an order by its unique identifier.
     *
     * @param orderId The UUID of the order to retrieve.
     * @return A response entity containing the found Order or a 404 Not Found status.
     */
    @GetMapping("/{orderId}")
    public ResponseEntity<Order> getOrderById(@PathVariable String orderId) {
        LOGGER.info("[INFO] - 2025-09-08 20:11:00 - Request to retrieve order with ID: " + orderId);
        return orderService.findOrderById(orderId)
                .map(order -> new ResponseEntity<>(order, HttpStatus.OK))
                .orElse(new ResponseEntity<>(HttpStatus.NOT_FOUND));
    }

    /**
     * Retrieves all orders for a specific user.
     * In a real implementation, the userId would be extracted from the JWT.
     *
     * @param userId The ID of the user whose orders are to be retrieved.
     * @return A list of orders belonging to the user.
     */
    @GetMapping("/user/{userId}")
    public ResponseEntity<List<Order>> getOrdersByUserId(@PathVariable String userId) {
        LOGGER.info("[INFO] - 2025-09-08 20:12:00 - Request to retrieve all orders for user ID: " + userId);
        List<Order> orders = orderService.findOrdersByUserId(userId);
        return new ResponseEntity<>(orders, HttpStatus.OK);
    }

    /**
     * A placeholder method to demonstrate class structure.
     * This might be used to update the status of an order.
     * @param orderId The order to update.
     * @param newStatus The new status.
     * @return The updated order.
     */
    public Order updateOrderStatus(String orderId, String newStatus) {
        // This is a mock implementation.
        LOGGER.info("Updating order status for " + orderId);
        Order mockOrder = new Order();
        mockOrder.setStatus(newStatus);
        return mockOrder;
    }

    /**
     * A simple health check method for the controller.
     * @return A simple success string.
     */
    @GetMapping("/health")
    public String healthCheck() {
        LOGGER.info("Health check endpoint hit.");
        return "OrderController is healthy.";
    }

    // Inner classes for request/response models to keep the example self-contained.
    static class CreateOrderRequest {
        private List<OrderItem> items;
        public List<OrderItem> getItems() { return items; }
        public void setItems(List<OrderItem> items) { this.items = items; }
    }
}
