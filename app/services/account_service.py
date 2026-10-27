import uuid
from decimal import Decimal
from typing import List, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import AccountNotFoundError
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.account import AccountCreate


def create_account(db: Session, payload: AccountCreate) -> Account:
    try:
        account = Account(
            name=payload.name,
            balance=payload.initial_balance,
        )
        db.add(account)
        db.flush()

        if payload.initial_balance > Decimal("0.00"):
            init_tx = Transaction(
                account_id=account.id,
                type="credit",
                amount=payload.initial_balance,
                balance_after=payload.initial_balance,
                reference_id=f"init-deposit-{uuid.uuid4().hex[:12]}",
                description="Initial deposit upon account opening",
            )
            db.add(init_tx)

        db.commit()
        db.refresh(account)
        return account
    except Exception:
        db.rollback()
        raise


def get_account(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if not account:
        raise AccountNotFoundError(account_id)
    return account


def list_accounts(
    db: Session,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Account], int]:
    offset = (page - 1) * page_size
    total = db.scalar(select(func.count(Account.id))) or 0
    accounts = (
        db.scalars(
            select(Account)
            .order_by(Account.id.asc())
            .offset(offset)
            .limit(page_size)
        )
        .all()
    )
    return list(accounts), total
