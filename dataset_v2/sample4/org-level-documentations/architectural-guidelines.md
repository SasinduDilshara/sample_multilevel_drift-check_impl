# Architectural-Guidelines

1. System must follow microservices architecture.
2. Services must communicate using REST over HTTP/JSON.
3. Shared libraries must be version controlled.
4. Service discovery handled via registry.
5. Circuit breakers must be used for resilience.
6. Use message queues for async communication.
7. Databases must be per service (no sharing).
8. API gateway must handle request routing.
9. Cache frequently accessed data in Redis.
10. Apply zero-downtime deployment strategy.
11. Implement centralized logging.
12. Use role-based access control across services.