from decimal import Decimal
from fastapi.testclient import TestClient


def test_transfer_money_success(client: TestClient):
    # Setup prompt example: Account A balance: 100, Account B balance: 50, Transfer: 30
    res_a = client.post("/accounts", json={"name": "Account A", "initial_balance": "100.00"})
    res_b = client.post("/accounts", json={"name": "Account B", "initial_balance": "50.00"})
    account_a_id = res_a.json()["id"]
    account_b_id = res_b.json()["id"]

    transfer_res = client.post(
        "/transfers",
        json={
            "source_account_id": account_a_id,
            "destination_account_id": account_b_id,
            "amount": "30.00",
            "reference_id": "transfer-example-1",
        },
    )
    assert transfer_res.status_code == 201
    transfer_data = transfer_res.json()
    assert transfer_data["status"] == "completed"
    assert Decimal(transfer_data["amount"]) == Decimal("30.00")
    assert transfer_data["source_transaction_id"] is not None
    assert transfer_data["destination_transaction_id"] is not None

    # Check balances: Account A should be 70, Account B should be 80
    check_a = client.get(f"/accounts/{account_a_id}")
    check_b = client.get(f"/accounts/{account_b_id}")
    assert Decimal(check_a.json()["balance"]) == Decimal("70.00")
    assert Decimal(check_b.json()["balance"]) == Decimal("80.00")


def test_transfer_insufficient_funds_rolls_back_atomically(client: TestClient):
    res_a = client.post("/accounts", json={"name": "Account A", "initial_balance": "20.00"})
    res_b = client.post("/accounts", json={"name": "Account B", "initial_balance": "50.00"})
    account_a_id = res_a.json()["id"]
    account_b_id = res_b.json()["id"]

    transfer_res = client.post(
        "/transfers",
        json={
            "source_account_id": account_a_id,
            "destination_account_id": account_b_id,
            "amount": "100.00",
            "reference_id": "transfer-fail-insufficient",
        },
    )
    assert transfer_res.status_code == 400
    assert transfer_res.json()["code"] == "INSUFFICIENT_BALANCE"

    # Verify neither account was touched
    check_a = client.get(f"/accounts/{account_a_id}")
    check_b = client.get(f"/accounts/{account_b_id}")
    assert Decimal(check_a.json()["balance"]) == Decimal("20.00")
    assert Decimal(check_b.json()["balance"]) == Decimal("50.00")


def test_transfer_source_account_not_found(client: TestClient):
    res_b = client.post("/accounts", json={"name": "Account B", "initial_balance": "50.00"})
    account_b_id = res_b.json()["id"]

    transfer_res = client.post(
        "/transfers",
        json={
            "source_account_id": 999999,
            "destination_account_id": account_b_id,
            "amount": "10.00",
            "reference_id": "transfer-source-404",
        },
    )
    assert transfer_res.status_code == 404
    assert transfer_res.json()["code"] == "ACCOUNT_NOT_FOUND"


def test_transfer_destination_account_not_found(client: TestClient):
    res_a = client.post("/accounts", json={"name": "Account A", "initial_balance": "50.00"})
    account_a_id = res_a.json()["id"]

    transfer_res = client.post(
        "/transfers",
        json={
            "source_account_id": account_a_id,
            "destination_account_id": 999999,
            "amount": "10.00",
            "reference_id": "transfer-dest-404",
        },
    )
    assert transfer_res.status_code == 404
    assert transfer_res.json()["code"] == "ACCOUNT_NOT_FOUND"


def test_transfer_same_account_rejected(client: TestClient):
    res = client.post("/accounts", json={"name": "Self Account", "initial_balance": "100.00"})
    account_id = res.json()["id"]

    transfer_res = client.post(
        "/transfers",
        json={
            "source_account_id": account_id,
            "destination_account_id": account_id,
            "amount": "10.00",
            "reference_id": "transfer-self",
        },
    )
    assert transfer_res.status_code == 422
    assert transfer_res.json()["code"] == "VALIDATION_ERROR"


def test_transfer_duplicate_reference_id(client: TestClient):
    res_a = client.post("/accounts", json={"name": "Account A", "initial_balance": "100.00"})
    res_b = client.post("/accounts", json={"name": "Account B", "initial_balance": "100.00"})
    account_a_id = res_a.json()["id"]
    account_b_id = res_b.json()["id"]

    first_res = client.post(
        "/transfers",
        json={
            "source_account_id": account_a_id,
            "destination_account_id": account_b_id,
            "amount": "20.00",
            "reference_id": "dup-transfer-ref",
        },
    )
    assert first_res.status_code == 201

    duplicate_res = client.post(
        "/transfers",
        json={
            "source_account_id": account_a_id,
            "destination_account_id": account_b_id,
            "amount": "20.00",
            "reference_id": "dup-transfer-ref",
        },
    )
    assert duplicate_res.status_code == 409
    assert duplicate_res.json()["code"] == "DUPLICATE_TRANSFER"

    # Balances must reflect only one successful transfer
    check_a = client.get(f"/accounts/{account_a_id}")
    check_b = client.get(f"/accounts/{account_b_id}")
    assert Decimal(check_a.json()["balance"]) == Decimal("80.00")
    assert Decimal(check_b.json()["balance"]) == Decimal("120.00")


def test_get_transfer_and_list(client: TestClient):
    res_a = client.post("/accounts", json={"name": "Account A", "initial_balance": "100.00"})
    res_b = client.post("/accounts", json={"name": "Account B", "initial_balance": "100.00"})
    account_a_id = res_a.json()["id"]
    account_b_id = res_b.json()["id"]

    transfer_res = client.post(
        "/transfers",
        json={
            "source_account_id": account_a_id,
            "destination_account_id": account_b_id,
            "amount": "15.00",
            "reference_id": "transfer-inspect-1",
        },
    )
    transfer_id = transfer_res.json()["id"]

    get_res = client.get(f"/transfers/{transfer_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == transfer_id

    list_res = client.get("/transfers?page=1&page_size=10")
    assert list_res.status_code == 200
    assert any(item["id"] == transfer_id for item in list_res.json()["items"])


def test_transfer_max_length_reference_id_success(client: TestClient):
    res_a = client.post("/accounts", json={"name": "Account A", "initial_balance": "100.00"})
    res_b = client.post("/accounts", json={"name": "Account B", "initial_balance": "100.00"})
    account_a_id = res_a.json()["id"]
    account_b_id = res_b.json()["id"]

    long_ref = "r" * 100
    transfer_res = client.post(
        "/transfers",
        json={
            "source_account_id": account_a_id,
            "destination_account_id": account_b_id,
            "amount": "10.00",
            "reference_id": long_ref,
        },
    )
    assert transfer_res.status_code == 201
    assert transfer_res.json()["reference_id"] == long_ref
