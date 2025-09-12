# User Service Specification

## Overview
Handles all user-related operations including authentication, profile management, and user preferences.

## Database Schema
- Users table with PostgreSQL as primary database
- Redis for session caching and JWT token blacklisting
- User avatars stored in AWS S3

## API Endpoints
- POST /api/users/register - User registration
- POST /api/users/login - User authentication  
- GET /api/users/profile - Get user profile
- PUT /api/users/profile - Update user profile
- POST /api/users/forgot-password - Password reset request

## Authentication
- JWT tokens with RSA-256 signature
- Token expiry: 2 hours for access tokens, 7 days for refresh tokens
- Password hashing using BCrypt with salt rounds of 12

## Caching Strategy
- User profiles cached in Redis for 30 minutes
- Session data cached for token lifetime
- Cache invalidation on profile updates
