# Specifications

1. User service: registration, login, profile management.
2. Book service: catalog, search, filter by category.
3. Order service: order placement, tracking, cancellation.
4. Payment service: handle payments and refunds.
5. Notification service: email + SMS alerts.
6. Sales service: monthly/annual sales analytics.
7. Each service has its own database schema.
8. Services interact over REST APIs.
9. Use JWT for authentication across services.
10. Apply rate limiting on order and payment endpoints.