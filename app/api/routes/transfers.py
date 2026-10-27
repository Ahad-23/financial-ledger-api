from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_pagination
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.transfer import TransferCreate, TransferResponse
from app.services import transfer_service

router = APIRouter(prefix="/transfers", tags=["Transfers"])


@router.post(
    "",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Transfer money between two accounts atomically",
)
def create_transfer(
    payload: TransferCreate,
    db: Session = Depends(get_db),
):
    return transfer_service.execute_transfer(db, payload)


@router.get(
    "",
    response_model=PaginatedResponse[TransferResponse],
    summary="List transfers with pagination",
)
def list_transfers(
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
):
    items, total = transfer_service.list_transfers(
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
    "/{transfer_id}",
    response_model=TransferResponse,
    summary="Get transfer details by ID",
)
def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
):
    return transfer_service.get_transfer(db, transfer_id)
