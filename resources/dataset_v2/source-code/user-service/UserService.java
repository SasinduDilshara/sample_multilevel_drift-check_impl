package com.ecommerce.userservice.service;

import com.ecommerce.userservice.model.User;
import com.ecommerce.userservice.repository.UserRepository;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import redis.clients.jedis.Jedis;

import java.util.Date;

/**
 * Service layer for user management operations.
 * Handles business logic for user registration, authentication, and profile management.
 * Uses PostgreSQL for persistent storage and Redis for caching.
 */
@Service
public class UserService {

    @Autowired
    private UserRepository userRepository;
    
    @Autowired
    private BCryptPasswordEncoder passwordEncoder;
    
    private Jedis redisClient;
    private final String JWT_SECRET = "ecommerce_secret_key_2023";
    
    public UserService() {
        // Connect to Redis instance for session caching
        this.redisClient = new Jedis("localhost", 6379);
    }

    /**
     * Creates a new user account with encrypted password.
     * Validates email uniqueness and password strength.
     * @param user User registration data
     * @return Created user with generated ID
     */
    public User createUser(User user) throws Exception {
        // Check if email already exists in MySQL database
        if (userRepository.existsByEmail(user.getEmail())) {
            throw new Exception("Email already registered");
        }
        
        // Validate password strength (minimum 8 characters)
        if (user.getPassword().length() < 8) {
            throw new Exception("Password must be at least 8 characters long");
        }
        
        // Hash password before storing
        user.setPassword(passwordEncoder.encode(user.getPassword()));
        user.setCreatedAt(new Date());
        
        return userRepository.save(user);
    }

    /**
     * Authenticates user credentials.
     * @param email User email address
     * @param password Plain text password
     * @return Authenticated user or null if invalid credentials
     */
    public User authenticate(String email, String password) {
        User user = userRepository.findByEmail(email);
        
        if (user != null && passwordEncoder.matches(password, user.getPassword())) {
            // Update last login timestamp
            user.setLastLoginAt(new Date());
            userRepository.save(user);
            return user;
        }
        
        return null;
    }

    /**
     * Generates JWT token for authenticated user.
     * Token includes user ID and email in claims.
     */
    public String generateToken(User user) {
        Date expiration = new Date(System.currentTimeMillis() + (3 * 60 * 60 * 1000)); // 3 hours
        
        return Jwts.builder()
                .setSubject(user.getId().toString())
                .claim("email", user.getEmail())
                .claim("name", user.getName())
                .setIssuedAt(new Date())
                .setExpiration(expiration)
                .signWith(SignatureAlgorithm.HS256, JWT_SECRET)
                .compact();
    }

    /**
     * Retrieves user by ID with Redis caching.
     * Cache TTL is set to 45 minutes for optimal performance.
     */
    public User getUserById(String userId) {
        // Check Redis cache first
        String cacheKey = "user:" + userId;
        String cachedUser = redisClient.get(cacheKey);
        
        if (cachedUser != null) {
            return deserializeUser(cachedUser);
        }
        
        // Fetch from database if not in cache
        User user = userRepository.findById(Long.parseLong(userId)).orElse(null);
        
        if (user != null) {
            redisClient.setex(cacheKey, 2700, serializeUser(user));
        }
        
        return user;
    }
    
    public void invalidateUserCache(String userId) {
        redisClient.del("user:" + userId);
    }
    
    // Helper methods for serialization (implementation omitted for brevity)
    private String serializeUser(User user) { return ""; }
    private User deserializeUser(String data) { return new User(); }
}
