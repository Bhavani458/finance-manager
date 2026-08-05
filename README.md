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

## Deployment (Supabase + Render)

The repo ships with `render.yaml` (web service) and `.github/workflows/scheduled-jobs.yml`
(daily jobs). Roughly one hour end-to-end, ~$0/mo on free tiers.

**Supabase Postgres**
1. Create a project at [supabase.com](https://supabase.com); region Mumbai (`ap-south-1`).
2. **Project Settings → Database → Connection string → URI (Transaction pooler, port 6543)**.
3. Change prefix from `postgresql://` to `postgresql+asyncpg://` — that's your `DATABASE_URL`.

**Render web service**
1. Render dashboard → **New → Blueprint** → connect this repo. It reads `render.yaml`.
2. In the created service's **Environment** tab, set:
   - `DATABASE_URL` — the Supabase URI above
   - `OPENAI_API_KEY` — your OpenAI key
   - `CORS_ORIGINS` — comma-separated frontend origins (e.g. `https://your-app.vercel.app`)
3. Deploy is triggered automatically. `preDeployCommand` runs `alembic upgrade head` +
   `python -m app.seed` before the new version boots.
4. Free plan sleeps after 15 min inactivity (30s cold start on first request). Upgrade to
   Starter ($7/mo) for always-on.

**Scheduled jobs (GitHub Actions cron)**
1. Add `DATABASE_URL` to **GitHub → Settings → Secrets and variables → Actions → New secret**.
2. `.github/workflows/scheduled-jobs.yml` runs the three daily jobs (`refresh_valuations`,
   `process_sips`, `rollup_net_worth`) at IST times.
3. Manual runs: **Actions → Scheduled jobs → Run workflow → pick a job**.

**Auto-deploy**
Every push to `main` builds a new image and rolls it out with a zero-downtime deploy. Migrations
run automatically in the pre-deploy step.

**Custom domain (optional)** — one click in Render's dashboard; provisions the TLS cert.
