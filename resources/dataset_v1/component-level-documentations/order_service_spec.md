# Order Service - API Specification

This document details the API endpoints for the Order Service.

## Endpoints

### `POST /orders`

-   **Description**: Creates a new order for the authenticated user.
-   **Request Body**:
    ```json
    {
      "items": [
        {
          "productId": "prod-123",
          "quantity": 2
        },
        {
          "productId": "prod-456",
          "quantity": 1
        }
      ]
    }
    ```
-   **Success Response (201 Created)**:
    ```json
    {
      "orderId": "ord-abc-123",
      "status": "CREATED",
      "totalAmount": 120.50,
      "createdAt": "2025-09-08T20:00:00Z"
    }
    ```

### `GET /orders/{id}`

-   **Description**: Retrieves an order by its ID.
-   **URL Parameters**:
    -   `id` (string): The unique identifier of the order.
-   **Success Response (200 OK)**:
    ```json
    {
      "orderId": "ord-abc-123",
      "status": "SHIPPED",
      "items": [...],
      "totalAmount": 120.50,
      "createdAt": "2025-09-08T20:00:00Z"
    }
    ```
