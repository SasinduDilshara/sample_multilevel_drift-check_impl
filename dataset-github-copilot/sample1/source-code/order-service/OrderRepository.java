package com.ecommerce.order;

import java.util.*;
import java.time.LocalDateTime;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

/**
 * Order repository for database operations
 * Handles CRUD operations for order entities
 * 
 * @author Development Team
 */
@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {
    
    /**
     * Find order by order ID
     * @param orderId the order identifier
     * @return Optional containing order if found
     */
    Optional<Order> findByOrderId(String orderId);
    
    /**
     * Finds all orders for a customer
     * @param customerId customer identifier  
     * @return list of customer orders
     */
    List<Order> findByCustomerId(String customerId);
    
    /**
     * Find orders by status
     * @param status order status to filter by
     * @return list of orders with specified status
     */
    List<Order> findByStatus(String status);
    
    /**
     * Find orders within date range
     * @param startDate start of date range
     * @param endDate end of date range
     * @return orders created within date range
     */
    @Query("SELECT o FROM Order o WHERE o.createdAt BETWEEN :startDate AND :endDate")
    List<Order> findByDateRange(@Param("startDate") LocalDateTime startDate, 
                               @Param("endDate") LocalDateTime endDate);
    
    /**
     * Get order count by customer
     * @param customerId customer identifier
     * @return number of orders for customer
     */
    long countByCustomerId(String customerId);
    
    /**
     * Find recent orders for customer
     * @param customerId customer identifier
     * @param days number of days to look back
     * @return recent orders
     */
    @Query("SELECT o FROM Order o WHERE o.customerId = :customerId AND o.createdAt >= :sinceDate ORDER BY o.createdAt DESC")
    List<Order> findRecentOrders(@Param("customerId") String customerId, 
                                @Param("sinceDate") LocalDateTime sinceDate);
    
    // Find orders by total amount range - simple implementation
    List<Order> findByTotalBetween(Double minAmount, Double maxAmount);
    
    // Get pending orders - basic query
    @Query("SELECT o FROM Order o WHERE o.status = 'PENDING'")
    List<Order> getPendingOrders();
    
    // Update order status - direct update
    @Query("UPDATE Order o SET o.status = :status WHERE o.orderId = :orderId")
    void updateOrderStatus(@Param("orderId") String orderId, @Param("status") String status);
    
    // Delete old orders - cleanup method
    void deleteByCreatedAtBefore(LocalDateTime cutoffDate);
}
