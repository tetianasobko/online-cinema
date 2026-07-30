# Online Cinema API

A RESTful API for browsing, purchasing, and managing movies online. Users can
interact with the movie catalog, create orders, and pay through Stripe, while
moderators and administrators manage catalog and user data.

## Features

- **Accounts** — Email registration, account activation, JWT authentication,
  logout, password change, and password reset
- **Movies** — Paginated catalog with search, filtering, sorting, and detailed
  movie information
- **Interactions** — Favorites, likes, dislikes, 10-point ratings, comments,
  replies, and notifications
- **Shopping cart** — Add, remove, and validate movies before purchase
- **Orders** — Order placement, history, cancellation, and price revalidation
- **Payments** — Stripe Checkout, signed webhooks, payment history, and refunds
- **Management** — Role-based catalog and user administration
- **Swagger UI** — Interactive API documentation with protected access

## Deployed Project

- API: [Online Cinema API](https://52-209-95-128.sslip.io/)
- Swagger UI: [API documentation](https://52-209-95-128.sslip.io/docs)

Use these demo credentials to access the documentation:

```text
Username: cinema_docs
Password: V7mQ2xL9pR4kT8wN5cH1sF6dJ3bY0aZ
```

## Tech Stack

- Python / FastAPI / Pydantic
- SQLAlchemy / Alembic / PostgreSQL
- JWT authentication
- Stripe
- Redis / Celery / Celery Beat
- Docker / Docker Compose
- Poetry
- pytest / Flake8

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Stripe CLI for local webhook testing

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/tetianasobko/online-cinema.git
   cd online-cinema
   ```

2. Copy the environment file:

   ```bash
   cp .env.sample .env
   ```

3. Replace the placeholder values in `.env`.

   Generate secure JWT secrets with:

   ```bash
   openssl rand -hex 32
   ```

4. Build and start the application:

   ```bash
   docker compose up --build
   ```

The API will be available at `http://localhost:8000`.

### Running without Docker

Install dependencies:

```bash
poetry install
```

Start PostgreSQL, Redis, and MailHog, then run:

```bash
PYTHONPATH=src poetry run alembic upgrade head
PYTHONPATH=src poetry run uvicorn main:app --reload --env-file .env
```

## API Endpoints

All application routes use the `/api/v1` prefix.

### Accounts — `/api/v1/accounts`

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/register` | Register a user | No |
| GET | `/activate` | Activate an account | No |
| POST | `/activation/resend` | Request a new activation link | No |
| POST | `/login` | Obtain access and refresh tokens | No |
| POST | `/refresh` | Refresh the access token | No |
| POST | `/logout` | Revoke the refresh token | No |
| POST | `/password/change` | Change a remembered password | User |
| POST | `/password/reset/request` | Request a password-reset link | No |
| POST | `/password/reset/complete` | Complete password reset | No |
| PATCH | `/admin/users/{user_id}/group` | Change a user role | Admin |
| POST | `/admin/users/{user_id}/activate` | Activate a user manually | Admin |

### Movies and Genres

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/movies/` | Search, filter, sort, and paginate movies | No |
| GET | `/api/v1/movies/{movie_uuid}` | Get movie details | No |
| GET | `/api/v1/genres/` | List genres with movie counts | No |
| GET | `/api/v1/genres/{genre_id}/movies` | List movies by genre | No |

### Movie Interactions

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET/POST/DELETE | `/api/v1/favorites/` | View and manage favorites | User |
| GET/PUT/DELETE | `/api/v1/movies/{movie_uuid}/reaction` | Manage like or dislike | User |
| GET/PUT/DELETE | `/api/v1/movies/{movie_uuid}/rating` | Manage a movie rating | User |
| GET/POST | `/api/v1/movies/{movie_uuid}/comments` | View or create comments | Mixed |
| POST | `/api/v1/comments/{comment_id}/replies` | Reply to a comment | User |
| POST/DELETE | `/api/v1/comments/{comment_id}/likes` | Like or unlike a comment | User |
| GET/PATCH | `/api/v1/notifications/` | View and update notifications | User |

### Cart and Orders

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/cart/` | View the shopping cart | User |
| POST | `/api/v1/cart/{movie_uuid}` | Add a movie | User |
| DELETE | `/api/v1/cart/{movie_uuid}` | Remove a movie | User |
| DELETE | `/api/v1/cart/` | Clear the cart | User |
| GET | `/api/v1/orders/` | View order history | User |
| POST | `/api/v1/orders/` | Place an order | User |
| POST | `/api/v1/orders/{order_id}/cancel` | Cancel a pending order | User |

### Payments

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/payments/` | View payment history | User |
| POST | `/api/v1/payments/checkout` | Create a Stripe Checkout Session | User |
| POST | `/api/v1/payments/cancel` | Cancel an open Checkout Session | User |
| POST | `/api/v1/payments/{payment_id}/refund` | Request a refund | User |
| POST | `/api/v1/payments/webhook` | Process a signed Stripe event | Stripe |
| GET | `/api/v1/payments/success` | View successful payment result | No |
| GET | `/api/v1/payments/cancel` | View canceled checkout result | No |

### Moderator and Admin

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| CRUD | `/api/v1/admin/movies/` | Manage movies | Moderator |
| CRUD | `/api/v1/admin/genres/` | Manage genres | Moderator |
| CRUD | `/api/v1/admin/actors/` | Manage actors | Moderator |
| CRUD | `/api/v1/admin/directors/` | Manage directors | Moderator |
| GET | `/api/v1/admin/users/{user_id}/cart` | Inspect a user cart | Admin |
| GET | `/api/v1/admin/payments` | Filter and inspect payments | Admin |

### API Docs

| Endpoint | Description |
|---|---|
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |
| `/openapi.json` | OpenAPI schema |

Documentation endpoints require the credentials configured through
`DOCS_USERNAME` and `DOCS_PASSWORD`.

## Authentication

The API uses access and refresh JWT tokens.

1. Register with `POST /api/v1/accounts/register`.
2. Activate the account using the emailed link.
3. Log in through `POST /api/v1/accounts/login`.
4. Add the access token to authenticated requests:

   ```text
   Authorization: Bearer <access_token>
   ```

5. Use the refresh token at `POST /api/v1/accounts/refresh` when the access
   token expires.

## Stripe Webhooks

Forward Stripe test events to the local API:

```bash
stripe login
stripe listen \
  --forward-to http://127.0.0.1:8000/api/v1/payments/webhook
```

Copy the generated webhook secret into `STRIPE_WEBHOOK_SECRET` and restart the
application.

## Running Tests

Run code-quality checks:

```bash
poetry run flake8 src
```

Run all tests with coverage:

```bash
poetry run pytest
```

Run a specific test group:

```bash
poetry run pytest -m unit
poetry run pytest -m integration
poetry run pytest -m functional
```
