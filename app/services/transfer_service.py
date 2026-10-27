from typing import List, Tuple
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import (
    AccountNotFoundError,
    DuplicateTransferError,
    InsufficientBalanceError,
    InvalidTransferError,
    TransferNotFoundError,
)
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.schemas.transfer import TransferCreate


def execute_transfer(db: Session, payload: TransferCreate) -> Transfer:
    if payload.source_account_id == payload.destination_account_id:
        raise InvalidTransferError("Source and destination accounts must be different.")

    try:
        # Check transfer reference idempotency
        existing_transfer = db.execute(
            select(Transfer).where(Transfer.reference_id == payload.reference_id)
        ).scalar_one_or_none()

        if existing_transfer:
            raise DuplicateTransferError(payload.reference_id)

        # Deadlock prevention: sort account IDs so locks are always acquired in deterministic order
        first_id, second_id = sorted(
            [payload.source_account_id, payload.destination_account_id]
        )

        acc_first = db.execute(
            select(Account).where(Account.id == first_id).with_for_update()
        ).scalar_one_or_none()

        acc_second = db.execute(
            select(Account).where(Account.id == second_id).with_for_update()
        ).scalar_one_or_none()

        # Validate existence of both accounts
        accounts = {acc.id: acc for acc in (acc_first, acc_second) if acc}
        if payload.source_account_id not in accounts:
            raise AccountNotFoundError(payload.source_account_id)
        if payload.destination_account_id not in accounts:
            raise AccountNotFoundError(payload.destination_account_id)

        source_acc = accounts[payload.source_account_id]
        dest_acc = accounts[payload.destination_account_id]

        # Validate sufficient balance
        if source_acc.balance < payload.amount:
            raise InsufficientBalanceError(
                current_balance=source_acc.balance,
                requested_amount=payload.amount,
            )

        # Update balances atomically
        source_acc.balance -= payload.amount
        dest_acc.balance += payload.amount

        # Record debit transaction on source account
        source_tx = Transaction(
            account_id=source_acc.id,
            type="debit",
            amount=payload.amount,
            balance_after=source_acc.balance,
            reference_id=f"tx-transfer-out-{payload.reference_id}",
            description=f"Transfer to account {dest_acc.id}",
        )
        db.add(source_tx)
        db.flush()

        # Record credit transaction on destination account
        dest_tx = Transaction(
            account_id=dest_acc.id,
            type="credit",
            amount=payload.amount,
            balance_after=dest_acc.balance,
            reference_id=f"tx-transfer-in-{payload.reference_id}",
            description=f"Transfer from account {source_acc.id}",
        )
        db.add(dest_tx)
        db.flush()

        # Create transfer record linking both transactions
        transfer = Transfer(
            source_account_id=source_acc.id,
            destination_account_id=dest_acc.id,
            amount=payload.amount,
            reference_id=payload.reference_id,
            source_transaction_id=source_tx.id,
            destination_transaction_id=dest_tx.id,
            status="completed",
        )
        db.add(transfer)

        db.commit()
        db.refresh(transfer)
        return transfer

    except IntegrityError as exc:
        db.rollback()
        if "reference_id" in str(exc).lower():
            raise DuplicateTransferError(payload.reference_id) from exc
        raise
    except Exception:
        db.rollback()
        raise


def get_transfer(db: Session, transfer_id: int) -> Transfer:
    transfer = db.get(Transfer, transfer_id)
    if not transfer:
        raise TransferNotFoundError(transfer_id)
    return transfer


def list_transfers(
    db: Session,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Transfer], int]:
    offset = (page - 1) * page_size
    total = db.scalar(select(func.count(Transfer.id))) or 0
    transfers = (
        db.scalars(
            select(Transfer)
            .order_by(Transfer.created_at.desc(), Transfer.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        .all()
    )
    return list(transfers), total
