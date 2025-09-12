# E-Commerce Microservices Platform

A modern e-commerce platform built with microservices architecture supporting user management, order processing, and multi-channel notifications.

## Services Overview
- **User Service** (Java/Spring Boot): Handles user registration, authentication, and profile management
- **Order Service** (Go): Manages order creation, payment processing, and order tracking
- **Notification Service** (Ballerina): Sends email and SMS notifications to users

## Technology Stack
- User Service: Java 17, Spring Boot 2.7, PostgreSQL
- Order Service: Go 1.19, Gin Framework, Redis Cache
- Notification Service: Ballerina Swan Lake, AWS SES, Twilio

## Database Architecture
- User data stored in PostgreSQL with Redis caching
- Order data persisted in MongoDB with Redis session storage
- Notification logs stored in lightweight SQLite database

## Communication
Services communicate via REST APIs and asynchronous message queues (RabbitMQ).
