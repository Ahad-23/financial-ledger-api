from typing import List, Tuple
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import (
    AccountNotFoundError,
    DuplicateTransactionError,
    InsufficientBalanceError,
    TransactionNotFoundError,
)
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate


def create_transaction(
    db: Session,
    account_id: int,
    payload: TransactionCreate,
) -> Transaction:
    try:
        # Acquire row-level exclusive lock on the account to prevent concurrent race conditions
        account = db.execute(
            select(Account).where(Account.id == account_id).with_for_update()
        ).scalar_one_or_none()

        if not account:
            raise AccountNotFoundError(account_id)

        # Idempotency check: duplicate reference_id for this account
        existing_tx = db.execute(
            select(Transaction).where(
                Transaction.account_id == account_id,
                Transaction.reference_id == payload.reference_id,
            )
        ).scalar_one_or_none()

        if existing_tx:
            raise DuplicateTransactionError(account_id, payload.reference_id)

        if payload.type == "debit":
            if account.balance < payload.amount:
                raise InsufficientBalanceError(
                    current_balance=account.balance,
                    requested_amount=payload.amount,
                )
            new_balance = account.balance - payload.amount
        else:
            new_balance = account.balance + payload.amount

        # Update balance and record transaction atomically
        account.balance = new_balance

        tx = Transaction(
            account_id=account.id,
            type=payload.type,
            amount=payload.amount,
            balance_after=new_balance,
            reference_id=payload.reference_id,
            description=payload.description,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    except IntegrityError as exc:
        db.rollback()
        # Handle database-level unique constraint violation fallback
        if "uq_account_reference_id" in str(exc).lower():
            raise DuplicateTransactionError(account_id, payload.reference_id) from exc
        raise
    except Exception:
        db.rollback()
        raise


def get_transaction(db: Session, transaction_id: int) -> Transaction:
    tx = db.get(Transaction, transaction_id)
    if not tx:
        raise TransactionNotFoundError(transaction_id)
    return tx


def list_account_transactions(
    db: Session,
    account_id: int,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Transaction], int]:
    # Ensure account exists
    account = db.get(Account, account_id)
    if not account:
        raise AccountNotFoundError(account_id)

    offset = (page - 1) * page_size
    total = (
        db.scalar(
            select(func.count(Transaction.id)).where(
                Transaction.account_id == account_id
            )
        )
        or 0
    )

    transactions = (
        db.scalars(
            select(Transaction)
            .where(Transaction.account_id == account_id)
            .order_by(Transaction.created_at.desc(), Transaction.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        .all()
    )
    return list(transactions), total
