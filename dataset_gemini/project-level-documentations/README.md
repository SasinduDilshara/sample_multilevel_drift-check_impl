# Gemini Commerce Platform

Welcome to the Gemini Commerce Platform, a modern, microservices-based e-commerce solution.

## Overview

This platform is composed of several core services that work together to provide a complete online shopping experience. The primary goal is to create a scalable, maintainable, and robust system.

## Microservices

-   **User Service (Ballerina)**: Manages user accounts, registration, and authentication.
-   **Product Service (Python)**: Manages the product catalog, inventory, and pricing.
-   **Order Service (Java)**: Manages customer orders, from creation to fulfillment.
-   **Payment Service (Go)**: Handles all payment processing and integration with payment gateways.
-   **Notification Service (Node.js)**: Sends notifications (email, SMS) to users.

## Getting Started

To run the project locally, you will need Docker and Docker Compose installed.

1.  Clone the repository.
2.  Navigate to the root directory.
3.  Run `docker-compose up --build`.

## API Versioning

All APIs across all services must be versioned. The current version is **v1**, and all API paths must be prefixed with `/api/v1/`. For example: `https://api.geminicommerce.com/api/v1/products`.
