from typing import Generator
from fastapi import Query
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.exceptions import InvalidPaginationError
from app.schemas.common import PaginationParams


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_pagination(
    page: int = Query(1, description="Page number, must be at least 1"),
    page_size: int = Query(
        20,
        description="Number of items per page, must be between 1 and 100",
    ),
) -> PaginationParams:
    if page < 1:
        raise InvalidPaginationError("Page parameter must be greater than or equal to 1.")
    if page_size < 1 or page_size > 100:
        raise InvalidPaginationError(
            "Page size parameter must be between 1 and 100."
        )
    return PaginationParams(page=page, page_size=page_size)
