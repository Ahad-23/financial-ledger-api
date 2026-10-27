from decimal import Decimal
from fastapi.testclient import TestClient


def test_credit_transaction_success(client: TestClient):
    acc_res = client.post("/accounts", json={"name": "Alice", "initial_balance": "50.00"})
    account_id = acc_res.json()["id"]

    tx_res = client.post(
        f"/accounts/{account_id}/transactions",
        json={
            "type": "credit",
            "amount": "100.00",
            "reference_id": "tx-credit-1",
            "description": "Salary deposit",
        },
    )
    assert tx_res.status_code == 201
    tx_data = tx_res.json()
    assert tx_data["type"] == "credit"
    assert Decimal(tx_data["amount"]) == Decimal("100.00")
    assert Decimal(tx_data["balance_after"]) == Decimal("150.00")
    assert tx_data["reference_id"] == "tx-credit-1"

    # Verify account balance updated
    acc_check = client.get(f"/accounts/{account_id}")
    assert Decimal(acc_check.json()["balance"]) == Decimal("150.00")


def test_debit_transaction_success(client: TestClient):
    acc_res = client.post("/accounts", json={"name": "Bob", "initial_balance": "200.00"})
    account_id = acc_res.json()["id"]

    tx_res = client.post(
        f"/accounts/{account_id}/transactions",
        json={
            "type": "debit",
            "amount": "75.50",
            "reference_id": "tx-debit-1",
        },
    )
    assert tx_res.status_code == 201
    tx_data = tx_res.json()
    assert tx_data["type"] == "debit"
    assert Decimal(tx_data["amount"]) == Decimal("75.50")
    assert Decimal(tx_data["balance_after"]) == Decimal("124.50")

    # Verify account balance updated
    acc_check = client.get(f"/accounts/{account_id}")
    assert Decimal(acc_check.json()["balance"]) == Decimal("124.50")


def test_debit_transaction_insufficient_balance(client: TestClient):
    acc_res = client.post("/accounts", json={"name": "Charlie", "initial_balance": "50.00"})
    account_id = acc_res.json()["id"]

    tx_res = client.post(
        f"/accounts/{account_id}/transactions",
        json={
            "type": "debit",
            "amount": "100.00",
            "reference_id": "tx-debit-fail",
        },
    )
    assert tx_res.status_code == 400
    assert tx_res.json()["code"] == "INSUFFICIENT_BALANCE"

    # Verify account balance unchanged
    acc_check = client.get(f"/accounts/{account_id}")
    assert Decimal(acc_check.json()["balance"]) == Decimal("50.00")


def test_duplicate_reference_id_same_account(client: TestClient):
    acc_res = client.post("/accounts", json={"name": "Dave", "initial_balance": "100.00"})
    account_id = acc_res.json()["id"]

    first_res = client.post(
        f"/accounts/{account_id}/transactions",
        json={
            "type": "credit",
            "amount": "20.00",
            "reference_id": "dup-ref-123",
        },
    )
    assert first_res.status_code == 201

    duplicate_res = client.post(
        f"/accounts/{account_id}/transactions",
        json={
            "type": "credit",
            "amount": "30.00",
            "reference_id": "dup-ref-123",
        },
    )
    assert duplicate_res.status_code == 409
    assert duplicate_res.json()["code"] == "DUPLICATE_TRANSACTION"

    # Balance must only have added the first transaction (100 + 20 = 120)
    acc_check = client.get(f"/accounts/{account_id}")
    assert Decimal(acc_check.json()["balance"]) == Decimal("120.00")


def test_same_reference_id_different_accounts_allowed(client: TestClient):
    acc1_res = client.post("/accounts", json={"name": "User 1", "initial_balance": "10.00"})
    acc2_res = client.post("/accounts", json={"name": "User 2", "initial_balance": "10.00"})
    acc1_id = acc1_res.json()["id"]
    acc2_id = acc2_res.json()["id"]

    res1 = client.post(
        f"/accounts/{acc1_id}/transactions",
        json={"type": "credit", "amount": "5.00", "reference_id": "shared-ref"},
    )
    assert res1.status_code == 201

    res2 = client.post(
        f"/accounts/{acc2_id}/transactions",
        json={"type": "credit", "amount": "5.00", "reference_id": "shared-ref"},
    )
    assert res2.status_code == 201


def test_transaction_account_not_found(client: TestClient):
    res = client.post(
        "/accounts/999999/transactions",
        json={"type": "credit", "amount": "50.00", "reference_id": "ref-404"},
    )
    assert res.status_code == 404
    assert res.json()["code"] == "ACCOUNT_NOT_FOUND"


def test_transaction_invalid_amount(client: TestClient):
    acc_res = client.post("/accounts", json={"name": "Eva", "initial_balance": "100.00"})
    account_id = acc_res.json()["id"]

    # Zero amount
    res = client.post(
        f"/accounts/{account_id}/transactions",
        json={"type": "credit", "amount": "0.00", "reference_id": "ref-zero"},
    )
    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"

    # Negative amount
    res = client.post(
        f"/accounts/{account_id}/transactions",
        json={"type": "credit", "amount": "-50.00", "reference_id": "ref-neg"},
    )
    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_transaction_invalid_type(client: TestClient):
    acc_res = client.post("/accounts", json={"name": "Frank", "initial_balance": "100.00"})
    account_id = acc_res.json()["id"]

    res = client.post(
        f"/accounts/{account_id}/transactions",
        json={"type": "refund", "amount": "50.00", "reference_id": "ref-invalid-type"},
    )
    assert res.status_code == 422
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_list_account_transactions_and_get_single(client: TestClient):
    acc_res = client.post("/accounts", json={"name": "Grace", "initial_balance": "100.00"})
    account_id = acc_res.json()["id"]

    tx_res = client.post(
        f"/accounts/{account_id}/transactions",
        json={"type": "credit", "amount": "25.00", "reference_id": "tx-grace-1"},
    )
    tx_id = tx_res.json()["id"]

    list_res = client.get(f"/accounts/{account_id}/transactions")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] >= 2  # initial deposit + 1 transaction
    assert any(item["id"] == tx_id for item in data["items"])

    # Get single transaction
    get_res = client.get(f"/transactions/{tx_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == tx_id


def test_get_transaction_not_found(client: TestClient):
    res = client.get("/transactions/999999")
    assert res.status_code == 404
    assert res.json()["code"] == "TRANSACTION_NOT_FOUND"
