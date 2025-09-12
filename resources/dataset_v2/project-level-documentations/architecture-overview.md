# Architecture Overview

## System Design
The platform follows a microservices architecture with each service independently deployable and scalable.

## Data Flow
1. User registration/login → User Service validates → Creates JWT tokens
2. Order placement → Order Service processes → Triggers notification events
3. Notification Service consumes events → Sends multi-channel notifications

## Security
- JWT-based authentication across all services
- API Gateway handles rate limiting and request routing
- All services use HTTPS with TLS 1.3

## Deployment
- Containerized using Docker
- Orchestrated with Kubernetes
- CI/CD pipeline using Jenkins
