# Banking API Reference

Interactive docs are available when the server is running:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

**Base URL**: `http://localhost:8000`

---

## 1. Health

### `GET /health`
Checks whether the API server is up and can reach the database.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

## 2. Accounts

### `POST /accounts`
Creates a new account. You can optionally provide an initial deposit.

**Request Body**:
```json
{
  "name": "Jane Doe",
  "initial_balance": "100.00"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | Yes | Account holder name. Cannot be blank or empty spaces. |
| `initial_balance` | decimal | No | Starting balance. Defaults to `0.00`. Max 2 decimal places. |

**Response `201 Created`**:
```json
{
  "id": 1,
  "name": "Jane Doe",
  "balance": "100.00",
  "created_at": "2026-10-27T10:30:00Z",
  "updated_at": "2026-10-27T10:30:00Z"
}
```

---

### `GET /accounts/{account_id}`
Returns details and the current balance of an account.

**Response `200 OK`**:
```json
{
  "id": 1,
  "name": "Jane Doe",
  "balance": "100.00",
  "created_at": "2026-10-27T10:30:00Z",
  "updated_at": "2026-10-27T10:30:00Z"
}
```

**Response `404 Not Found`**:
```json
{
  "code": "ACCOUNT_NOT_FOUND",
  "message": "Account with id 99 not found.",
  "detail": null
}
```

---

### `GET /accounts`
Lists all accounts with pagination.

**Query Parameters**:
- `page` (optional, default `1`): Page number (starts at 1).
- `page_size` (optional, default `20`): Items per page (between 1 and 100).

**Response `200 OK`**:
```json
{
  "items": [
    {
      "id": 1,
      "name": "Jane Doe",
      "balance": "100.00",
      "created_at": "2026-10-27T10:30:00Z",
      "updated_at": "2026-10-27T10:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

## 3. Transactions

### `POST /accounts/{account_id}/transactions`
Performs an atomic credit or debit transaction on an account. The balance update and transaction row are committed together.

**Request Body**:
```json
{
  "type": "debit",
  "amount": "25.50",
  "reference_id": "order-inv-1001",
  "description": "Coffee and sandwich"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `type` | string | Yes | Either `"credit"` or `"debit"`. |
| `amount` | decimal | Yes | Greater than `0.00`, max 2 decimal places. |
| `reference_id` | string | Yes | Unique reference per account to avoid duplicate charges. Max 120 chars. |
| `description` | string | No | Optional note (max 255 chars). |

**Response `201 Created`**:
```json
{
  "id": 10,
  "account_id": 1,
  "type": "debit",
  "amount": "25.50",
  "balance_after": "74.50",
  "reference_id": "order-inv-1001",
  "description": "Coffee and sandwich",
  "created_at": "2026-10-27T10:31:00Z"
}
```

**Response `400 Bad Request` (Insufficient Balance)**:
```json
{
  "code": "INSUFFICIENT_BALANCE",
  "message": "Insufficient balance. Current balance is 74.50, requested debit amount is 100.00.",
  "detail": {
    "current_balance": "74.50",
    "requested_amount": "100.00"
  }
}
```

**Response `409 Conflict` (Duplicate Reference ID)**:
```json
{
  "code": "DUPLICATE_TRANSACTION",
  "message": "A transaction with reference_id 'order-inv-1001' already exists for account 1.",
  "detail": {
    "account_id": 1,
    "reference_id": "order-inv-1001"
  }
}
```

---

### `GET /accounts/{account_id}/transactions`
Lists transactions for a single account, sorted newest first.

**Query Parameters**:
- `page` (default `1`)
- `page_size` (default `20`)

**Response `200 OK`**:
```json
{
  "items": [
    {
      "id": 10,
      "account_id": 1,
      "type": "debit",
      "amount": "25.50",
      "balance_after": "74.50",
      "reference_id": "order-inv-1001",
      "description": "Coffee and sandwich",
      "created_at": "2026-10-27T10:31:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

### `GET /transactions/{transaction_id}`
Returns details of a single transaction by ID.

**Response `200 OK`**:
```json
{
  "id": 10,
  "account_id": 1,
  "type": "debit",
  "amount": "25.50",
  "balance_after": "74.50",
  "reference_id": "order-inv-1001",
  "description": "Coffee and sandwich",
  "created_at": "2026-10-27T10:31:00Z"
}
```

---

## 4. Money Transfers

### `POST /transfers`
Transfers money from a source account to a destination account atomically.

- Both accounts must exist.
- Source account must have enough balance.
- Locks accounts in deterministic order to prevent deadlocks.
- Debits source, credits destination, and writes ledger entries in a single transaction.
- If anything fails, everything rolls back.

**Request Body**:
```json
{
  "source_account_id": 1,
  "destination_account_id": 2,
  "amount": "30.00",
  "reference_id": "transfer-ref-001"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `source_account_id` | int | Yes | Account to debit funds from. |
| `destination_account_id` | int | Yes | Account to credit funds to (must differ from source). |
| `amount` | decimal | Yes | Greater than `0.00`, max 2 decimal places. |
| `reference_id` | string | Yes | Unique idempotency key. Max 100 chars. |

**Response `201 Created`**:
```json
{
  "id": 5,
  "source_account_id": 1,
  "destination_account_id": 2,
  "amount": "30.00",
  "reference_id": "transfer-ref-001",
  "source_transaction_id": 14,
  "destination_transaction_id": 15,
  "status": "completed",
  "created_at": "2026-10-27T10:32:00Z"
}
```

**Response `400 Bad Request` (Insufficient Balance)**:
```json
{
  "code": "INSUFFICIENT_BALANCE",
  "message": "Insufficient balance. Current balance is 20.00, requested debit amount is 30.00.",
  "detail": {
    "current_balance": "20.00",
    "requested_amount": "30.00"
  }
}
```

**Response `409 Conflict` (Duplicate Transfer Reference)**:
```json
{
  "code": "DUPLICATE_TRANSFER",
  "message": "A transfer with reference_id 'transfer-ref-001' already exists.",
  "detail": {
    "reference_id": "transfer-ref-001"
  }
}
```

---

### `GET /transfers/{transfer_id}`
Returns details of a completed transfer.

**Response `200 OK`**:
```json
{
  "id": 5,
  "source_account_id": 1,
  "destination_account_id": 2,
  "amount": "30.00",
  "reference_id": "transfer-ref-001",
  "source_transaction_id": 14,
  "destination_transaction_id": 15,
  "status": "completed",
  "created_at": "2026-10-27T10:32:00Z"
}
```

---

### `GET /transfers`
Lists all transfers with pagination.

**Query Parameters**:
- `page` (default `1`)
- `page_size` (default `20`)

---

## 5. Error Responses

Every error returns a consistent JSON body:
```json
{
  "code": "ERROR_CODE",
  "message": "Plain explanation of the issue.",
  "detail": null
}
```

| Status | Code | Meaning |
|---|---|---|
| `400` | `INSUFFICIENT_BALANCE` | Account doesn't have enough money for this debit or transfer |
| `400` | `INVALID_PAGINATION` | `page < 1` or `page_size > 100` |
| `400` | `INVALID_TRANSFER` | Source and destination account IDs are the same |
| `404` | `ACCOUNT_NOT_FOUND` | Account ID does not exist |
| `404` | `TRANSACTION_NOT_FOUND` | Transaction ID does not exist |
| `404` | `TRANSFER_NOT_FOUND` | Transfer ID does not exist |
| `409` | `DUPLICATE_TRANSACTION` | That `reference_id` was already used for this account |
| `409` | `DUPLICATE_TRANSFER` | That `reference_id` was already used for a transfer |
| `422` | `VALIDATION_ERROR` | Missing field, negative amount, or invalid transaction type |
| `500` | `INTERNAL_SERVER_ERROR` | Unhandled server error |
