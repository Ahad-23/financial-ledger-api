from decimal import Decimal
from fastapi.testclient import TestClient


def test_create_account_default_balance(client: TestClient):
    response = client.post("/accounts", json={"name": "Alice"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice"
    assert Decimal(data["balance"]) == Decimal("0.00")
    assert "id" in data
    assert "created_at" in data


def test_create_account_with_initial_balance(client: TestClient):
    response = client.post(
        "/accounts",
        json={"name": "Bob", "initial_balance": "150.50"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Bob"
    assert Decimal(data["balance"]) == Decimal("150.50")


def test_create_account_invalid_name(client: TestClient):
    # Empty name
    response = client.post("/accounts", json={"name": ""})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"

    # Whitespace only name
    response = client.post("/accounts", json={"name": "   "})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_create_account_negative_balance(client: TestClient):
    response = client.post(
        "/accounts",
        json={"name": "Charlie", "initial_balance": "-10.00"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_create_account_invalid_decimal_precision(client: TestClient):
    response = client.post(
        "/accounts",
        json={"name": "Dave", "initial_balance": "10.555"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_get_account_success(client: TestClient):
    create_res = client.post("/accounts", json={"name": "Emma", "initial_balance": "200.00"})
    account_id = create_res.json()["id"]

    response = client.get(f"/accounts/{account_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == account_id
    assert data["name"] == "Emma"
    assert Decimal(data["balance"]) == Decimal("200.00")


def test_get_account_not_found(client: TestClient):
    response = client.get("/accounts/999999")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "ACCOUNT_NOT_FOUND"


def test_list_accounts_pagination(client: TestClient):
    for i in range(5):
        client.post("/accounts", json={"name": f"User {i}"})

    response = client.get("/accounts?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total"] >= 5


def test_list_accounts_invalid_pagination(client: TestClient):
    response = client.get("/accounts?page=0")
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_PAGINATION"

    response = client.get("/accounts?page_size=101")
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_PAGINATION"
