# E-Commerce System Architecture

## Overview

This document describes the overall architecture of the e-commerce platform, including service boundaries, communication patterns, and technology choices.

## System Components

### Core Services

#### Order Service (`OrderService.java`)
Manages the complete order lifecycle from creation to fulfillment. Coordinates with Payment and Shipping services to ensure successful order completion.

**Key Classes:**
- `Order.java` - Order domain entity with OrderItem collection
- `OrderService.java` - Business logic for order processing
- `OrderController.java` - REST API endpoints for order operations
- `OrderRepository.java` - Data persistence layer

**Dependencies:**
- Payment Service for payment processing
- Shipping Service for delivery coordination
- Inventory Service for stock validation

#### Payment Service (`payment_service.py`)
Handles all payment-related operations including transaction processing, refunds, and payment method management.

**Key Components:**
- `payment_service.py` - Payment orchestration
- `payment_gateway.py` - Gateway abstraction layer
- `Payment` model - Payment transaction data
- `Transaction` model - Transaction history

**Integration:**
- Stripe Gateway for credit card payments
- PayPal Gateway for PayPal payments
- Bank transfer integration

#### Customer Service (`CustomerService.kt`)
Manages customer accounts, profiles, and tier management.

**Key Classes:**
- `Customer.kt` - Customer domain entity
- `CustomerService.kt` - Customer business logic
- `CustomerTier.kt` - Customer tier enum (BRONZE, SILVER, GOLD, PLATINUM)

### Supporting Services

#### Inventory Service (`inventory_service.py`)
Tracks product inventory across warehouses, handles stock updates, and manages warehouse operations.

#### Shipping Service (`shipping_service.py`)
Coordinates shipping operations, calculates shipping costs, and tracks deliveries.

#### Review Service (`ReviewService.kt`)
Manages product reviews and ratings from customers.

### Frontend Application

#### Web Components (`OrderList.tsx`, `CheckoutFlow.tsx`)
React-based frontend with TypeScript providing:
- Product browsing and search
- Shopping cart management
- Checkout flow with payment integration
- Order tracking and history

**Key Components:**
- `OrderList.tsx` - Display customer orders
- `ProductCard.tsx` - Product display component
- `CheckoutFlow.tsx` - Multi-step checkout process
- `Cart.tsx` - Shopping cart functionality

### Shared Libraries

#### Authentication (`AuthService.java`)
JWT-based authentication with token management and refresh tokens.

#### Configuration (`api.config.js`)
Centralized configuration management for API endpoints and feature flags.

## Communication Patterns

### Synchronous Communication
- REST APIs for service-to-service communication
- JSON for request/response payloads

### Data Flow

**Order Creation Flow:**
1. Frontend calls `OrderController.createOrder()`
2. `OrderService` validates inventory via `InventoryService`
3. `PaymentService` processes payment via `PaymentGateway`
4. `ShippingService` creates shipping label
5. Order status updated to CONFIRMED

**Payment Processing:**
1. `PaymentService.processPayment()` called by OrderService
2. `PaymentGateway` abstraction routes to appropriate provider
3. Transaction recorded in Payment model
4. Callback to OrderService on completion

## Database Design

### Order Domain Schema
```sql
orders (
  id UUID PRIMARY KEY,
  customer_id UUID REFERENCES customers(id),
  status VARCHAR(50),
  total_amount DECIMAL(10,2),
  created_at TIMESTAMP
)

order_items (
  id UUID PRIMARY KEY,
  order_id UUID REFERENCES orders(id),
  product_id UUID,
  quantity INTEGER,
  price DECIMAL(10,2)
)
```

### Payment Domain Schema
```sql
payments (
  id UUID PRIMARY KEY,
  order_id UUID REFERENCES orders(id),
  amount DECIMAL(10,2),
  payment_method VARCHAR(50),
  status VARCHAR(50),
  transaction_id VARCHAR(255)
)
```

## Security Considerations

### Authentication Flow
- JWT tokens with 1-hour expiration
- Refresh tokens with 7-day expiration
- Token validation via `TokenService.validateToken()`

### Authorization
- Role-based access control (RBAC)
- Customer-level permissions
- Admin-level operations restricted

## Technology Stack

### Backend
- Java 17 with Spring Boot (Order Service)
- Python 3.11 with FastAPI (Payment, Inventory, Shipping)
- Kotlin with Spring Boot (Customer, Review)

### Frontend
- React 18 with TypeScript
- Redux for state management
- React Router for navigation

### Database
- PostgreSQL for transactional data
- Redis for caching

### Infrastructure
- Docker containers
- Kubernetes for orchestration
- Nginx for load balancing

## Monitoring and Logging

### Logging (`Logger.py`)
Centralized logging with structured JSON format for all services.

### Metrics
- Order completion rate
- Payment success rate
- Average shipping time
- Customer satisfaction score

## Deployment

See `deployment-guide.md` for detailed deployment instructions.

## API Documentation

See `api-design.md` for REST API specifications.
