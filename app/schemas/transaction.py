from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

TransactionType = Literal["credit", "debit"]


class TransactionCreate(BaseModel):
    type: TransactionType = Field(
        ...,
        description="Transaction type: 'credit' or 'debit'",
    )
    amount: Decimal = Field(
        ...,
        gt=0,
        description="Transaction amount, must be greater than 0",
    )
    reference_id: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Unique reference identifier for idempotency",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional transaction note",
    )

    @field_validator("reference_id")
    @classmethod
    def validate_reference_id(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("reference_id cannot be empty or whitespace only.")
        return trimmed

    @field_validator("amount")
    @classmethod
    def validate_amount_precision(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Amount must be greater than 0.")
        if value.as_tuple().exponent < -2:
            raise ValueError("Amount cannot have more than 2 decimal places.")
        return value


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    type: str
    amount: Decimal
    balance_after: Decimal
    reference_id: str
    description: Optional[str] = None
    created_at: datetime
