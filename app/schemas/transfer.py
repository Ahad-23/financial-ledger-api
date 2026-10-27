from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TransferCreate(BaseModel):
    source_account_id: int = Field(
        ...,
        gt=0,
        description="ID of the account to debit funds from",
    )
    destination_account_id: int = Field(
        ...,
        gt=0,
        description="ID of the account to credit funds to",
    )
    amount: Decimal = Field(
        ...,
        gt=0,
        description="Amount to transfer, must be greater than 0",
    )
    reference_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique transfer reference identifier for idempotency",
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

    @model_validator(mode="after")
    def validate_different_accounts(self) -> "TransferCreate":
        if self.source_account_id == self.destination_account_id:
            raise ValueError("Source and destination accounts must be different.")
        return self


class TransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_account_id: int
    destination_account_id: int
    amount: Decimal
    reference_id: str
    source_transaction_id: Optional[int] = None
    destination_transaction_id: Optional[int] = None
    status: str
    created_at: datetime
