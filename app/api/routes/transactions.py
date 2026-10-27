from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_pagination
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.transaction import TransactionCreate, TransactionResponse
from app.services import transaction_service

router = APIRouter(tags=["Transactions"])


@router.post(
    "/accounts/{account_id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a credit or debit transaction on an account",
)
def create_transaction(
    account_id: int,
    payload: TransactionCreate,
    db: Session = Depends(get_db),
):
    return transaction_service.create_transaction(db, account_id, payload)


@router.get(
    "/accounts/{account_id}/transactions",
    response_model=PaginatedResponse[TransactionResponse],
    summary="List transactions for a specific account",
)
def list_account_transactions(
    account_id: int,
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    items, total = transaction_service.list_account_transactions(
        db,
        account_id=account_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get transaction details by ID",
)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    return transaction_service.get_transaction(db, transaction_id)
