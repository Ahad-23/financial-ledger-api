# Assumptions & Design Tradeoffs

Here are the key decisions made while building this service and why they were chosen.

---

## 1. Representing Money

- **No floats**: Floating-point numbers (`float` in Python or `REAL` in Postgres) can introduce tiny rounding errors like `$0.10 + $0.20 = $0.30000000000000004`. That is unacceptable in financial ledgers.
- **Fixed-point numbers**: We use Python's `Decimal` and PostgreSQL's `NUMERIC(14, 2)`. This guarantees exact math down to two decimal places (e.g. cents) with room for balances up to hundreds of billions.
- **Validation**: All amounts must be strictly positive (`> 0.00`) and cannot have more than 2 decimal digits.

---

## 2. Balance Storage & The Ledger

- **Hybrid approach**:
  - We store a live `balance` column on the `accounts` table. This keeps balance checks fast (`O(1)`) without having to calculate `SUM(amount)` over thousands of historical rows every time someone buys a coffee.
  - We write every deposit, withdrawal, and transfer into the `transactions` table, storing `amount` and `balance_after`. This keeps a full audit trail of how the account got to its current balance.
- **Database constraints**: Even though the application code checks `balance >= requested_amount`, the database also has a hard constraint: `CHECK (balance >= 0)`. A balance can never drop below zero, even under unexpected conditions.

---

## 3. Concurrency & Atomicity

- **Row-level locking (`FOR UPDATE`)**:
  - When balance updates happen, we select the account row using SQLAlchemy's `.with_for_update()`.
  - In PostgreSQL, this places an exclusive row lock until the transaction commits or rolls back. Parallel requests for the same account wait their turn, preventing double-spending.
- **Deadlock prevention during transfers**:
  - A classic problem: User 1 transfers from A to B while User 2 transfers from B to A at the exact same moment. If User 1 locks A and waits for B, while User 2 locks B and waits for A, PostgreSQL detects a deadlock and kills one of them.
  - **The fix**: We sort the account IDs and lock them in ascending order (`min(id_a, id_b)` first, then `max(id_a, id_b)`). Both requests now request locks in the same order, completely eliminating deadlocks.
- **All-or-nothing rollback**:
  - A transfer touches two balances and writes two ledger records plus a transfer record. All five actions run in a single database transaction. If anything fails (insufficient funds, network timeout, constraint error), `db.rollback()` executes, leaving both accounts exactly as they started.

---

## 4. Idempotency & Retries

- **Transactions**: Each credit or debit includes a `reference_id` (like an order ID or payment intent ID). The database enforces `UNIQUE (account_id, reference_id)`. If a mobile client loses connection and retries the same request, the second attempt returns HTTP 409 (`DUPLICATE_TRANSACTION`), avoiding duplicate charges.
- **Transfers**: Transfers have their own unique `reference_id` (`UNIQUE (reference_id)`). Re-sending the same transfer reference also returns HTTP 409 (`DUPLICATE_TRANSFER`).

---

## 5. Input Validation & Error Format

- Requests are validated at the door using Pydantic v2 schemas:
  - Account names cannot be blank or only spaces.
  - Amounts must be positive numbers with at most two decimal places.
  - Transaction types must be `"credit"` or `"debit"`.
- Every error returns the same predictable JSON shape:
  ```json
  {
    "code": "ERROR_CODE",
    "message": "Plain explanation of the issue.",
    "detail": null
  }
  ```
- Standard HTTP codes are used throughout:
  - `200 OK` for reads.
  - `201 Created` for new accounts, transactions, and transfers.
  - `400 Bad Request` for business logic rejections (insufficient funds, bad pagination).
  - `404 Not Found` when an account, transaction, or transfer ID doesn't exist.
  - `409 Conflict` for duplicate reference IDs.
  - `422 Unprocessable Content` for malformed input fields.
  - `500 Internal Server Error` for unexpected server crashes.

---

## 6. Pagination

- Listing endpoints (`/accounts`, `/accounts/{id}/transactions`, `/transfers`) use 1-based page numbers (`page >= 1`) and a customizable `page_size` (1 to 100, default 20).
- Responses include pagination metadata: `items`, `total`, `page`, `page_size`, and `total_pages`.
