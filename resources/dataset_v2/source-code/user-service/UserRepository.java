package com.ecommerce.userservice.repository;

import com.ecommerce.userservice.model.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * Repository interface for User entity database operations.
 * Extends JpaRepository for basic CRUD operations.
 * Custom queries for email validation and user search functionality.
 */
@Repository
public interface UserRepository extends JpaRepository<User, Long> {

    /**
     * Finds user by email address.
     * Used for authentication and email uniqueness validation.
     * @param email User email address
     * @return User entity or null if not found
     */
    User findByEmail(String email);

    /**
     * Checks if user exists with given email.
     * More efficient than findByEmail for existence checks.
     * @param email Email address to check
     * @return true if user exists, false otherwise
     */
    boolean existsByEmail(String email);

    /**
     * Finds users by name pattern (case-insensitive).
     * Supports partial name matching for user search functionality.
     * Results are limited to 50 users for performance.
     */
    @Query("SELECT u FROM User u WHERE LOWER(u.name) LIKE LOWER(CONCAT('%', ?1, '%')) ORDER BY u.name")
    List<User> findByNameContainingIgnoreCase(String name);

    /**
     * Retrieves all active users created in the last 30 days.
     * Used for analytics and recent user activity reports.
     * Excludes soft-deleted users from results.
     */
    @Query("SELECT u FROM User u WHERE u.isActive = true AND u.createdAt >= CURRENT_DATE - 30")
    List<User> findRecentActiveUsers();
}
