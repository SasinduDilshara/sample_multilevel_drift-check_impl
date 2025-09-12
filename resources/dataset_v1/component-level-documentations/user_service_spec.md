# User Service - API Specification

This document details the API endpoints for the User Service.

## Endpoints

### `POST /register`

-   **Description**: Registers a new user.
-   **Request Body**:
    ```json
    {
      "email": "user@example.com",
      "password": "aStrongPassword123"
    }
    ```
-   **Success Response (201 Created)**:
    ```json
    {
      "userId": "uuid-string-12345",
      "email": "user@example.com"
    }
    ```

### `POST /login`

-   **Description**: Authenticates a user.
-   **Request Body**:
    ```json
    {
      "email": "user@example.com",
      "password": "aStrongPassword123"
    }
    ```
-   **Success Response (200 OK)**: The response contains two tokens.
    ```json
    {
      "accessToken": "jwt-access-token",
      "refreshToken": "jwt-refresh-token"
    }
    ```
