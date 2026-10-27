import concurrent.futures
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.account import Account
from app.schemas.transaction import TransactionCreate
from app.schemas.transfer import TransferCreate
from app.services import account_service, transaction_service, transfer_service
from tests.conftest import TestingSessionLocal


def test_concurrent_debit_prevents_negative_balance():
    # Setup account with 100.00 balance
    with TestingSessionLocal() as db:
        acc = Account(name="Concurrent Account", balance=Decimal("100.00"))
        db.add(acc)
        db.commit()
        db.refresh(acc)
        account_id = acc.id

    # 5 concurrent threads attempting to debit 40.00 each (Total 200.00)
    # Exactly 2 should succeed, 3 should fail
    results = []

    def perform_debit(index: int):
        with TestingSessionLocal() as db:
            try:
                tx = transaction_service.create_transaction(
                    db=db,
                    account_id=account_id,
                    payload=TransactionCreate(
                        type="debit",
                        amount=Decimal("40.00"),
                        reference_id=f"concurrent-debit-{index}",
                    ),
                )
                return ("success", tx.id)
            except Exception as exc:
                return ("error", type(exc).__name__)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(perform_debit, i) for i in range(5)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    successes = [r for r in results if r[0] == "success"]
    errors = [r for r in results if r[0] == "error"]

    assert len(successes) == 2
    assert len(errors) == 3
    for err in errors:
        assert err[1] == "InsufficientBalanceError"

    # Verify final balance is 20.00
    with TestingSessionLocal() as db:
        final_acc = db.get(Account, account_id)
        assert final_acc.balance == Decimal("20.00")


def test_concurrent_bidirectional_transfers_no_deadlock():
    # Setup Account A with 500.00 and Account B with 500.00
    with TestingSessionLocal() as db:
        acc_a = Account(name="Account A", balance=Decimal("500.00"))
        acc_b = Account(name="Account B", balance=Decimal("500.00"))
        db.add_all([acc_a, acc_b])
        db.commit()
        db.refresh(acc_a)
        db.refresh(acc_b)
        id_a, id_b = acc_a.id, acc_b.id

    # 10 transfers A -> B ($10 each) and 10 transfers B -> A ($10 each) concurrently
    results = []

    def transfer_worker(task_id: int):
        with TestingSessionLocal() as db:
            try:
                if task_id % 2 == 0:
                    transfer = transfer_service.execute_transfer(
                        db=db,
                        payload=TransferCreate(
                            source_account_id=id_a,
                            destination_account_id=id_b,
                            amount=Decimal("10.00"),
                            reference_id=f"concurrent-transfer-{task_id}",
                        ),
                    )
                else:
                    transfer = transfer_service.execute_transfer(
                        db=db,
                        payload=TransferCreate(
                            source_account_id=id_b,
                            destination_account_id=id_a,
                            amount=Decimal("10.00"),
                            reference_id=f"concurrent-transfer-{task_id}",
                        ),
                    )
                return ("success", transfer.id)
            except Exception as exc:
                return ("error", str(exc))

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(transfer_worker, i) for i in range(20)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    successes = [r for r in results if r[0] == "success"]
    assert len(successes) == 20

    # Verify balances remained balanced (500 each)
    with TestingSessionLocal() as db:
        refreshed_a = db.get(Account, id_a)
        refreshed_b = db.get(Account, id_b)
        assert refreshed_a.balance == Decimal("500.00")
        assert refreshed_b.balance == Decimal("500.00")
