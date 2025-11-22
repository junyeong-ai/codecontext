# API Design Principles

## Overview

This document outlines the REST API design principles used across all e-commerce services, including naming conventions, error handling, and versioning strategies.

## REST API Guidelines

### Resource Naming

**Use plural nouns for resources:**
- `/api/v1/orders` - Order collection
- `/api/v1/products` - Product collection
- `/api/v1/customers` - Customer collection

**Use hierarchical URLs for relationships:**
- `/api/v1/orders/{orderId}/items` - Order items
- `/api/v1/customers/{customerId}/orders` - Customer's orders

### HTTP Methods

- `GET` - Retrieve resource(s)
- `POST` - Create new resource
- `PUT` - Update entire resource
- `PATCH` - Partial resource update
- `DELETE` - Remove resource

### Status Codes

**Success Codes:**
- `200 OK` - Request succeeded
- `201 Created` - Resource created
- `204 No Content` - Success with no body

**Error Codes:**
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict
- `500 Internal Server Error` - Server error

## API Examples

### Order Service API (`OrderController.java`)

#### Create Order
```http
POST /api/v1/orders
Content-Type: application/json
Authorization: Bearer {token}

{
  "customerId": "uuid",
  "items": [
    {
      "productId": "uuid",
      "quantity": 2,
      "price": 29.99
    }
  ],
  "shippingAddressId": "uuid",
  "paymentMethodId": "uuid"
}
```

**Response:**
```json
{
  "orderId": "uuid",
  "status": "PENDING",
  "totalAmount": 59.98,
  "createdAt": "2025-01-10T10:30:00Z"
}
```

**Implementation:** `OrderController.createOrder()` delegates to `OrderService.processOrder()`

#### Get Order
```http
GET /api/v1/orders/{orderId}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "orderId": "uuid",
  "customerId": "uuid",
  "status": "CONFIRMED",
  "items": [...],
  "totalAmount": 59.98,
  "createdAt": "2025-01-10T10:30:00Z",
  "updatedAt": "2025-01-10T10:31:00Z"
}
```

### Payment Service API (`payment_service.py`)

#### Process Payment
```http
POST /api/v1/payments
Content-Type: application/json
Authorization: Bearer {token}

{
  "orderId": "uuid",
  "amount": 59.98,
  "paymentMethod": "CREDIT_CARD",
  "cardToken": "tok_xxx"
}
```

**Implementation:** `PaymentService.processPayment()` calls `PaymentGateway.charge()`

### Customer Service API (`CustomerService.kt`)

#### Get Customer Profile
```http
GET /api/v1/customers/{customerId}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "customerId": "uuid",
  "email": "customer@example.com",
  "tier": "GOLD",
  "totalOrders": 15,
  "lifetimeValue": 1250.00
}
```

**Implementation:** `CustomerService.getCustomerProfile()` retrieves from `CustomerRepository`

## Authentication

### JWT Token Structure
```json
{
  "sub": "customerId",
  "email": "customer@example.com",
  "role": "CUSTOMER",
  "exp": 1704888000,
  "iat": 1704884400
}
```

**Validation:** `AuthService.validateToken()` and `TokenService.verifyToken()`

### Token Endpoints
```http
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
```

## Error Response Format

```json
{
  "error": {
    "code": "ORDER_NOT_FOUND",
    "message": "Order with ID abc123 not found",
    "timestamp": "2025-01-10T10:30:00Z",
    "path": "/api/v1/orders/abc123"
  }
}
```

## Pagination

```http
GET /api/v1/orders?page=1&size=20&sort=createdAt,desc
```

**Response Headers:**
```
X-Total-Count: 150
X-Page-Number: 1
X-Page-Size: 20
X-Total-Pages: 8
```

## Rate Limiting

- 100 requests per minute per user
- 1000 requests per minute per IP

**Response Header:**
```
X-Rate-Limit-Remaining: 95
X-Rate-Limit-Reset: 1704884460
```

## Versioning

Use URL versioning: `/api/v1/...`, `/api/v2/...`

**Deprecation Process:**
1. Announce deprecation 6 months in advance
2. Add `X-API-Deprecated: true` header
3. Document migration path
4. Remove after 12 months

## CORS Configuration

```javascript
// api.config.js
{
  allowOrigins: ['https://ecommerce.example.com'],
  allowMethods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
  allowHeaders: ['Authorization', 'Content-Type'],
  maxAge: 3600
}
```

## Request/Response Logging

All API requests logged via `Logger.py` with:
- Request ID
- HTTP method and path
- Response status
- Duration
- User ID (if authenticated)

## Related Documentation

- `system-architecture.md` - Overall system design
- Authentication implementation: `AuthService.java`
- Configuration management: `api.config.js`
