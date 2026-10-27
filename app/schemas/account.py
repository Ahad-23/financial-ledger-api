from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AccountCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the account holder",
    )
    initial_balance: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="Optional initial balance, must be non-negative",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Account name must not be empty or whitespace only.")
        return trimmed

    @field_validator("initial_balance")
    @classmethod
    def validate_initial_balance_precision(cls, value: Decimal) -> Decimal:
        if value.as_tuple().exponent < -2:
            raise ValueError("Initial balance cannot have more than 2 decimal places.")
        return value


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    balance: Decimal
    created_at: datetime
    updated_at: datetime
