# Gemini Commerce - Architectural Guidelines

This document outlines the high-level architectural principles for the Gemini Commerce platform.

1.  **Microservices Architecture**: The platform must be built on a microservices architecture.
2.  **Stateless Services**: All services should be stateless to allow for horizontal scaling.
3.  **Synchronous Communication**: All inter-service communication must be synchronous via REST APIs.
4.  **JSON for Data Transfer**: All API requests and responses must use JSON as the data format.
5.  **Centralized Configuration**: Configuration should be managed centrally, not within individual service code.
6.  **Authentication**: All endpoints must be secured. Services must use JWT (JSON Web Tokens) for authentication.
7.  **Database per Service**: Each microservice must have its own private database. Direct database access between services is strictly forbidden.
8.  **Health Check Endpoint**: Every microservice must expose a `/health` endpoint that returns a `200 OK` status if the service is operational.
9.  **API Gateway**: A single API Gateway will serve as the entry point for all client requests.
10. **Containerization**: All services must be containerized using Docker for consistent deployment environments.
