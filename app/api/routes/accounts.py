from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_pagination
from app.schemas.account import AccountCreate, AccountResponse
from app.schemas.common import PaginatedResponse, PaginationParams
from app.services import account_service

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
):
    return account_service.create_account(db, payload)


@router.get(
    "",
    response_model=PaginatedResponse[AccountResponse],
    summary="List accounts with pagination",
)
def list_accounts(
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    items, total = account_service.list_accounts(
        db,
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
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get account details by ID",
)
def get_account(
    account_id: int,
    db: Session = Depends(get_db),
):
    return account_service.get_account(db, account_id)
