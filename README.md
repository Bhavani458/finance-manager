# finance-manager

Personal finance backend. FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16.

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/) for dependency management
- Docker + Docker Compose (optional, easiest local path)

## Local run (Docker)

```bash
cp .env.example .env
docker compose up --build
```

The API is served at http://localhost:8000, with interactive docs at http://localhost:8000/docs.
The startup command runs `alembic upgrade head`, seeds the DB, and launches uvicorn.

## Local run (without Docker)

```bash
uv sync
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/finance
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --reload
```

## Migrations

```bash
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "your message"
```

## Seed

Seeds 11 system categories + 6 system InvestmentType rows (idempotent).

```bash
uv run python -m app.seed
```

## Jobs

Each job has a self-contained `main()` and CLI entry point:

```bash
uv run python -m app.jobs.refresh_valuations
uv run python -m app.jobs.process_sips
uv run python -m app.jobs.rollup_net_worth
```

## Tests

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/finance_test
uv run pytest
```

## Auth model

Two-mode JWT validation:

- **Dev/test** (default): HS256 with `JWT_SECRET`. Use `POST /api/v1/auth/dev-login` to mint a
  token against an upserted user. This endpoint is gated by `ENV in ("dev", "test")`.
- **Production**: set `CLERK_JWKS_URL` and Clerk-issued RS256 tokens are validated via JWKS. The
  `sub` claim is treated as `User.auth_provider_id`.

## Env vars

| Variable | Default | Notes |
| --- | --- | --- |
| `ENV` | `dev` | Enables `/auth/dev-login` when `dev` or `test`. |
| `DATABASE_URL` | postgres asyncpg URL | Required. |
| `TEST_DATABASE_URL` | unset | Used by pytest conftest when set. |
| `JWT_SECRET` | placeholder | HS256 signing key for dev-login tokens. |
| `JWT_ALGORITHM` | `HS256` | Dev mode only. |
| `CLERK_JWKS_URL` | unset | If set, switches to RS256 JWKS validation. |
| `AMFI_BASE_URL` | `https://api.mfapi.in` | mfapi.in base URL for NAV lookups. |

## Design invariants

- `Investment.invested_amount` and `Investment.current_value` are real Numeric columns — every
  investment has them regardless of `valuation_method`. `current_value` is denormalized by the
  valuation job on write for fast reads.
- `InvestmentType.field_schema` (JSONB) is the single source of truth for what fields an
  investment of that type has. Data types: `text`, `number`, `date`, `percent`, `enum`.
- `PATCH /investment-types/{id}` is additive-only: removing or renaming an existing field returns
  409. Appending new fields is fine; existing rows keep working with the new key absent.
- `/reports/investment-allocation` totals equal `sum(/investments.current_value)` (invariant test
  in `test_reports.py`).
- Attribute validation lives in `app.services.schema_validation.validate_attributes` — reused by
  create + update, never scattered.

## API surface

All routes under `/api/v1`. Bare-object responses (no envelope). Pagination via `?limit=&offset=`.
See `/docs` for the full OpenAPI schema.
