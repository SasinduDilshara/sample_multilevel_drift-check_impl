# Gemini Commerce - Core Feature Specifications

This document outlines the core features of the platform.

1.  **User Registration**: Users must be able to register with an `email` and `password`. The system should validate the email format and enforce password strength requirements.
2.  **User Login**: Registered users must be able to log in using their email and password.
3.  **JWT on Login**: Upon successful login, the `user-service` must return a JSON object containing a valid `accessToken` and a `refreshToken`.
4.  **Product Listing**: The `product-service` must provide an endpoint to list all available products.
5.  **Product Details**: The `product-service` must provide an endpoint to fetch details for a single product by its ID.
6.  **Order Creation**: Users must be able to create an order. The creation process requires a list of `productId` and `quantity` pairs.
7.  **Order History**: Users must be able to view their past orders.
8.  **Payment Processing**: The `payment-service` must be able to process credit card payments.
9.  **Order Confirmation Email**: After a successful order and payment, the `notification-service` must send an order confirmation email to the user.
10. **Inventory Check**: The `order-service` must check with the `product-service` to ensure sufficient inventory exists before confirming an order.
