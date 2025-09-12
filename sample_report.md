### Project Summary

The e-commerce microservices platform exhibits significant documentation drift across multiple components, with the most critical issues being database technology mismatches, incorrect authentication specifications, and missing payment gateway implementations described in component documentation. Cross-component drift occurs where services reference incorrect endpoints and missing notification integrations, compromising system reliability and maintainability.

***

### Component Analysis

**User Service**

* Component documentation specifies JWT tokens with **RSA-256 signature**, but the implementation uses **HS256 algorithm** in the `generateToken()` method
* Component specification states **BCrypt with salt rounds of 12**, but the inline comment in UserController incorrectly claims **10 salt rounds**  
* Component documentation describes **2 hours for access tokens, 7 days for refresh tokens**, but the implementation only generates access tokens with **3-hour expiry** and no refresh token functionality
* API documentation states the `/profile` endpoint **caches for 30 minutes**, but the `getUserById()` method implementation **caches for 45 minutes**
* Component specification claims **PostgreSQL as primary database**, but service code references **MySQL database** in the `createUser()` method comment

**Order Service**

* Component documentation specifies **PayPal integration for alternative payment methods**, but the payment processing implementation and webhook handling are completely missing from the codebase
* Project documentation states **MongoDB for order data**, but component documentation incorrectly claims **Redis for cart session management** when Redis is only used for caching
* API documentation describes **PUT /api/orders/{id}/status** endpoint, but the handler method expects **StatusUpdateRequest** structure that is never defined in the codebase
* Inline comments in `notifyUserService()` method incorrectly state it calls the **user service**, when it should call the **notification service** according to project architecture
* Component specification lists order state **DELIVERED**, but the `IsValidStatusTransition()` method validation logic is incomplete and cuts off mid-implementation

**Notification Service**

* Component documentation specifies **Firebase Cloud Messaging for push notifications** and **WebSocket connections for in-app notifications**, but the email_client.bal implementation only supports **HTTP-based email delivery**
* Component specification describes **AWS SES** integration, but the implementation uses a **generic HTTP email service** with custom API authentication instead of AWS SES
* Rate limiting documentation specifies **100 emails per minute per user**, but the bulk SMS processing in sms_client.bal has **no rate limiting delays implemented** as noted in the code comments
* Component documentation claims **PDF invoice attachments** for order confirmations, but the email template implementation only supports basic **HTML content with no attachment handling**
* SMS client documentation describes **Twilio integration**, but the module comment header incorrectly describes it as a **"verification service module"** rather than a general SMS notification service
