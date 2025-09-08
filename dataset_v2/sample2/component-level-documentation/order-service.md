# Order-Service

1. Handles order placement, tracking, cancellation.
2. Supports refunds (critical feature).
3. Returns detailed invoice data.
4. Order IDs must be UUIDs.
5. Inline comments should describe order flow.
6. Integrates with payment service.
7. Must ensure idempotency for order placement.
8. Provides order history for each user.
9. Includes admin endpoint for all orders.
10. Supports async processing via queue.