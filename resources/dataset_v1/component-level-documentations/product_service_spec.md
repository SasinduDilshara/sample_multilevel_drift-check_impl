# Product Service - API Specification

This document details the API endpoints for the Product Service.

## Endpoints

### `GET /products`

-   **Description**: Retrieves a list of all products.
-   **Query Parameters**:
    -   `page` (optional, integer): The page number for pagination.
    -   `limit` (optional, integer): The number of items per page.
-   **Success Response (200 OK)**:
    ```json
    [
      {
        "productId": "prod-123",
        "name": "Wireless Mouse",
        "price": 25.99,
        "stock": 150
      }
    ]
    ```

### `GET /products/{id}`

-   **Description**: Retrieves details for a specific product by its ID.
-   **URL Parameters**:
    -   `id` (string): The unique identifier of the product.
-   **Success Response (200 OK)**:
    ```json
    {
      "productId": "prod-123",
      "name": "Wireless Mouse",
      "description": "An ergonomic wireless mouse.",
      "price": 25.99,
      "stock": 150
    }
    ```
