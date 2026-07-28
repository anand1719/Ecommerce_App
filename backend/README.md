# Ecommerce Authentication API

A FastAPI authentication service for an ecommerce application. It includes customer registration, login, JWT access tokens, refresh-token rotation, logout, current-user lookup, and password change support.

## Features

- Email/password registration
- Secure password hashing with bcrypt
- JWT access and refresh tokens
- Persisted refresh tokens with rotation and revocation
- Protected `/me` and password-change endpoints
- Product catalog CRUD APIs
- Sales order APIs with line items, totals, stock checks, and cancellation
- Admin-only product mutations and sale status updates
- Optional Kafka producer integration for product and sale events
- SQLite by default, configurable through environment variables
- Pytest coverage for core authentication flows

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Before production use, set a strong `SECRET_KEY` in `.env`.

For PostgreSQL, use a connection string like:

```text
DATABASE_URL=postgresql+psycopg://postgres:your-password@localhost:5432/Ecommerce
```

If your password contains `@`, write it as `%40` inside the connection string.

## Run

```powershell
uvicorn app.main:app --reload
```

Open the API docs at:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/kafka/status` | Kafka producer status and topic names |
| `POST` | `/api/v1/auth/register` | Create an account and return tokens |
| `POST` | `/api/v1/auth/login` | Login and return tokens |
| `POST` | `/api/v1/auth/refresh` | Rotate a refresh token and return new tokens |
| `POST` | `/api/v1/auth/logout` | Revoke a refresh token |
| `GET` | `/api/v1/auth/me` | Return the current authenticated user |
| `POST` | `/api/v1/auth/change-password` | Change password and revoke active refresh tokens |
| `GET` | `/api/v1/products` | List active products, JWT required |
| `GET` | `/api/v1/products/{product_id}` | Get product details, JWT required |
| `POST` | `/api/v1/products` | Create product, admin only |
| `PATCH` | `/api/v1/products/{product_id}` | Update product, admin only |
| `DELETE` | `/api/v1/products/{product_id}` | Deactivate product, admin only |
| `GET` | `/api/v1/sales` | List current user's sales, or all sales for admins |
| `GET` | `/api/v1/sales/{sale_id}` | Get sale details |
| `POST` | `/api/v1/sales` | Create a sale for the current user |
| `PATCH` | `/api/v1/sales/{sale_id}/status` | Update sale status, admin only |
| `DELETE` | `/api/v1/sales/{sale_id}` | Cancel a sale and restore stock |

## Kafka Events

Start Kafka and Kafka UI:

```powershell
docker compose up -d
```

Open Kafka UI:

```text
http://localhost:8080
```

Use the `ecommerce-local` cluster in Kafka UI, then open the `ecommerce.products` or `ecommerce.sales` topic and view messages.

Enable Kafka publishing in `.env`:

```text
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CLIENT_ID=ecommerce-api
KAFKA_PRODUCTS_TOPIC=ecommerce.products
KAFKA_SALES_TOPIC=ecommerce.sales
KAFKA_FAIL_FAST=false
```

Published event types:

| Topic | Event Type |
| --- | --- |
| `ecommerce.products` | `product.created` |
| `ecommerce.products` | `product.updated` |
| `ecommerce.products` | `product.deactivated` |
| `ecommerce.sales` | `sale.created` |
| `ecommerce.sales` | `sale.status_updated` |
| `ecommerce.sales` | `sale.cancelled` |

Each Kafka message uses this envelope:

```json
{
  "event_id": "uuid",
  "event_type": "product.created",
  "source": "ecommerce-api",
  "occurred_at": "2026-07-21T00:00:00+00:00",
  "payload": {}
}
```

Create the default topics with:

```powershell
.\scripts\kafka-topics.ps1
```

When using `docker-compose.yml`, the topics are created automatically by the `kafka-init` service.

## Example Register Request

```json
{
  "email": "customer@example.com",
  "password": "StrongPass123",
  "full_name": "Sample Customer"
}
```

Use the returned `access_token` as:

```text
Authorization: Bearer <access_token>
```

## Example Product Request

Admin token required:

```json
{
  "sku": "SKU-100",
  "name": "Wireless Mouse",
  "description": "Ergonomic ecommerce sample product",
  "price": "25.50",
  "stock_quantity": 10,
  "is_active": true
}
```

## Example Sale Request

Customer token required:

```json
{
  "items": [
    {
      "product_id": "product-uuid",
      "quantity": 2
    }
  ],
  "tax_amount": "2.00",
  "discount_amount": "1.00"
}
```

## Database Scripts

The related table creation script is available at:

```text
scripts/schema.sql
```

## Test

```powershell
pytest
```
