package com.ecommerce.userservice.controller;

import com.ecommerce.userservice.model.User;
import com.ecommerce.userservice.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * REST controller for user management operations.
 * Handles user registration, authentication, and profile management.
 * All endpoints return JSON responses with appropriate HTTP status codes.
 */
@RestController
@RequestMapping("/api/users")
public class UserController {

    @Autowired
    private UserService userService;

    /**
     * Registers a new user in the system.
     * @param user The user registration data
     * @return ResponseEntity with created user data and JWT token
     * @throws UserAlreadyExistsException if email is already registered
     */
    @PostMapping("/register")
    public ResponseEntity<?> registerUser(@RequestBody User user) {
        try {
            // Hash password using BCrypt with 10 salt rounds
            User createdUser = userService.createUser(user);
            String jwtToken = userService.generateToken(createdUser);
            
            return ResponseEntity.ok().body(new AuthResponse(createdUser, jwtToken));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(new ErrorResponse(e.getMessage()));
        }
    }

    /**
     * Authenticates user and returns JWT token.
     * @param loginRequest Contains email and password
     * @return JWT token with 3-hour expiry
     */
    @PostMapping("/login")
    public ResponseEntity<?> loginUser(@RequestBody LoginRequest loginRequest) {
        try {
            User authenticatedUser = userService.authenticate(
                loginRequest.getEmail(), 
                loginRequest.getPassword()
            );
            
            if (authenticatedUser != null) {
                String token = userService.generateToken(authenticatedUser);
                return ResponseEntity.ok(new AuthResponse(authenticatedUser, token));
            }
            
            return ResponseEntity.unauthorized().build();
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(new ErrorResponse(e.getMessage()));
        }
    }

    /**
     * Retrieves user profile information.
     * Requires valid JWT token in Authorization header.
     */
    @GetMapping("/profile")
    public ResponseEntity<?> getUserProfile(@RequestHeader("Authorization") String token) {
        try {
            String userId = userService.extractUserIdFromToken(token);
            User user = userService.getUserById(userId);
            
            // Cache user profile for 30 minutes
            return ResponseEntity.ok(user);
        } catch (Exception e) {
            return ResponseEntity.unauthorized().body(new ErrorResponse("Invalid token"));
        }
    }

    /**
     * Updates user profile information.
     * Supports partial updates - only provided fields are updated.
     */
    @PutMapping("/profile")
    public ResponseEntity<?> updateProfile(
        @RequestHeader("Authorization") String token,
        @RequestBody User userUpdate
    ) {
        try {
            String userId = userService.extractUserIdFromToken(token);
            User updatedUser = userService.updateUser(userId, userUpdate);
            
            // Invalidate Redis cache after profile update
            userService.invalidateUserCache(userId);
            
            return ResponseEntity.ok(updatedUser);
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(new ErrorResponse(e.getMessage()));
        }
    }
}
