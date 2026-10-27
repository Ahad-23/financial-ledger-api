# Banking Ledger API

A straightforward, reliable banking API built with **FastAPI**, **PostgreSQL**, **SQLAlchemy**, and **uv**.

It supports creating accounts, posting credit/debit transactions, checking balances, and transferring money between accounts. All balance updates are atomic, race-condition safe, and protected against deadlocks and duplicate requests.

---

## Tech Stack

- **Python 3.12** + **FastAPI**
- **PostgreSQL 16** (via Docker)
- **SQLAlchemy 2.0** + **Alembic** (migrations)
- **uv** (package management)
- **Pytest** + **HTTPX** (automated tests)

---

## Project Structure

```
├── alembic/                # Database migrations
│   └── versions/           # Migration history
├── app/
│   ├── api/
│   │   ├── deps.py         # DB session & pagination helpers
│   │   └── routes/         # Endpoint handlers (accounts, transactions, transfers, health)
│   ├── models/             # SQLAlchemy tables with DB constraints
│   ├── schemas/            # Pydantic models for request/response validation
│   ├── services/           # Business logic & locking (where the real work happens)
│   ├── config.py           # App settings (database URLs, environment)
│   ├── database.py         # Engine & connection pool setup
│   ├── exceptions.py       # Custom errors with HTTP status mapping
│   └── main.py             # FastAPI app & centralized error handlers
├── tests/                  # 30 unit, integration, and concurrency tests
├── docker-compose.yml      # Runs Postgres and the API
├── Dockerfile              # API container image
├── API_DOCUMENTATION.md    # Endpoint reference & JSON examples
└── ASSUMPTIONS.md          # Design decisions & tradeoff notes
```

---

## Quickstart

### Option 1: Run everything with Docker (Easiest)

1. Start the database and API:
   ```bash
   docker compose up --build -d
   ```

2. Check health:
   ```bash
   curl http://localhost:8000/health
   ```
   Should return:
   ```json
   {"status": "healthy", "database": "connected"}
   ```

3. Interactive API docs are ready at:
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

4. Stop when done:
   ```bash
   docker compose down
   ```

---

### Option 2: Run Postgres in Docker, run the API locally

If you want to run or debug the Python app locally:

1. Start just Postgres:
   ```bash
   docker compose up -d db
   ```
   *(Exposed on port `5434` to avoid collisions with any local Postgres you already have).*

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Run migrations:
   ```bash
   uv run alembic upgrade head
   ```

4. Start the app:
   ```bash
   uv run uvicorn app.main:app --reload --port 8000
   ```

---

## Running Tests

Tests run against a dedicated test database (`confluencr_bank_test`) to verify real database constraints, row locks, and concurrency behavior.

1. Make sure Postgres is running:
   ```bash
   docker compose up -d db
   ```

2. Run the test suite:
   ```bash
   uv run pytest -v
   ```

3. Run with test coverage:
   ```bash
   uv run pytest --cov=app --cov-report=term-missing
   ```

---

## How It Works (Design Notes)

- **Safe Money Handling**: Never use `float` for money. We use `Decimal` in Python and `NUMERIC(14, 2)` in Postgres so cents never get rounded or lost.
- **Race Condition Prevention**: When updating an account's balance, we lock the row with `SELECT ... FOR UPDATE`. If 5 debit requests arrive at the exact same millisecond, they run one at a time. The account cannot go negative.
- **Deadlock-Free Transfers**: When moving money from Account A to Account B, we always lock the lower account ID first. Even if A sends to B while B sends to A simultaneously, the two requests acquire locks in the same order, so they never deadlock.
- **Duplicate Protection**: Every transaction requires a `reference_id`. The database enforces uniqueness per account (`UNIQUE (account_id, reference_id)`). If a network glitch causes a client to retry, the second attempt gets an HTTP 409 conflict instead of double-charging.
- **Database Safety Net**: On top of application checks, Postgres has constraints: `CHECK (balance >= 0)` and `CHECK (amount > 0)`.

---

## More Details

- See [API_DOCUMENTATION.md](file:///c:/Users/Ahad/Documents/repos/confluencr-assignment/API_DOCUMENTATION.md) for endpoint inputs, responses, and error examples.
- See [ASSUMPTIONS.md](file:///c:/Users/Ahad/Documents/repos/confluencr-assignment/ASSUMPTIONS.md) for why things were built this way.
