# Banking Platform API Specification

## API Overview
The Banking Platform API provides secure access to banking services through RESTful endpoints. All APIs follow OpenAPI 3.0 specifications and require OAuth 2.0 authentication.

## Base URL
- **Production**: `https://api.bankingcorp.com/v1`
- **Staging**: `https://api-staging.bankingcorp.com/v1`
- **Development**: `http://localhost:8080/api/v1`

## Authentication
All API requests require a valid JWT token obtained through OAuth 2.0 flow:

```http
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

## Core API Endpoints

### Account Management

#### Get Account Information
```http
GET /accounts/{accountId}
```

**Response:**
```json
{
  "accountId": "12345678901234567890",
  "accountNumber": "1234567890",
  "accountType": "CHECKING",
  "balance": 2500.00,
  "currency": "USD",
  "status": "ACTIVE",
  "customerId": "customer-123",
  "createdAt": "2024-01-15T10:30:00Z",
  "lastModified": "2024-01-20T14:45:00Z"
}
```

#### Create New Account
```http
POST /accounts
```

**Request Body:**
```json
{
  "customerId": "customer-123",
  "accountType": "SAVINGS",
  "currency": "USD",
  "initialDeposit": 1000.00
}
```

#### Update Account Status
```http
PATCH /accounts/{accountId}/status
```

**Request Body:**
```json
{
  "status": "SUSPENDED",
  "reason": "Suspicious activity detected"
}
```

### Transaction Processing

#### Process Transfer
```http
POST /transactions/transfer
```

**Request Body:**
```json
{
  "fromAccountId": "12345678901234567890",
  "toAccountId": "09876543210987654321",
  "amount": 500.00,
  "currency": "USD",
  "description": "Monthly rent payment",
  "reference": "RENT-2024-01"
}
```

**Response:**
```json
{
  "transactionId": "txn-abc123def456",
  "status": "COMPLETED",
  "fromAccount": "12345678901234567890",
  "toAccount": "09876543210987654321",
  "amount": 500.00,
  "fee": 2.50,
  "timestamp": "2024-01-20T15:30:00Z",
  "confirmationCode": "CNF789123"
}
```

#### Get Transaction History
```http
GET /accounts/{accountId}/transactions
```

**Query Parameters:**
- `startDate`: ISO 8601 date (optional)
- `endDate`: ISO 8601 date (optional)
- `limit`: Maximum number of results (default: 50, max: 100)
- `offset`: Pagination offset (default: 0)
- `type`: Transaction type filter (CREDIT, DEBIT, TRANSFER)

### Customer Management

#### Get Customer Profile
```http
GET /customers/{customerId}
```

**Response:**
```json
{
  "customerId": "customer-123",
  "firstName": "John",
  "lastName": "Doe",
  "email": "john.doe@email.com",
  "phone": "+1-555-0123",
  "address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zipCode": "10001",
    "country": "US"
  },
  "kycStatus": "VERIFIED",
  "accountIds": ["12345678901234567890", "09876543210987654321"]
}
```

#### Update Customer Information
```http
PUT /customers/{customerId}
```

### Notification Services

#### Get Notifications
```http
GET /customers/{customerId}/notifications
```

#### Mark Notification as Read
```http
PATCH /notifications/{notificationId}/read
```

## Error Responses
All errors follow RFC 7807 Problem Details standard:

```json
{
  "type": "https://api.bankingcorp.com/errors/insufficient-funds",
  "title": "Insufficient Funds",
  "status": 400,
  "detail": "Account balance is insufficient for the requested transaction",
  "instance": "/transactions/transfer",
  "traceId": "trace-123abc"
}
```

## Rate Limiting
- **Standard APIs**: 1000 requests per minute per client
- **Transaction APIs**: 100 requests per minute per client
- **Rate limit headers** included in all responses

## Security Considerations
- All requests must use HTTPS in production
- JWT tokens expire after 60 minutes
- Refresh tokens valid for 30 days
- Request/response logging for audit trails
- Input validation and sanitization
- OWASP security headers implementation

## Webhooks
The platform supports webhooks for real-time event notifications:

### Supported Events
- `transaction.completed`
- `transaction.failed`
- `account.created`
- `account.suspended`
- `fraud.detected`

### Webhook Payload Example
```json
{
  "eventId": "evt-123abc",
  "eventType": "transaction.completed",
  "timestamp": "2024-01-20T15:30:00Z",
  "data": {
    "transactionId": "txn-abc123def456",
    "accountId": "12345678901234567890",
    "amount": 500.00,
    "status": "COMPLETED"
  }
}
```

## SDK and Libraries
Official SDKs available for:
- JavaScript/TypeScript (npm: @bankingcorp/banking-sdk)
- Python (pip: bankingcorp-sdk)
- Java (Maven: com.bankingcorp:banking-sdk)
- Go (github.com/bankingcorp/banking-sdk-go)
