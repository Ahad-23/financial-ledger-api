from decimal import Decimal
from sqlalchemy import CheckConstraint, Column, DateTime, Integer, Numeric, String, func

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    balance = Column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_account_balance_non_negative"),
    )
