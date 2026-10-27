from typing import Any, Optional


class BankingException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        detail: Optional[Any] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


class AccountNotFoundError(BankingException):
    def __init__(self, account_id: int):
        super().__init__(
            code="ACCOUNT_NOT_FOUND",
            message=f"Account with id {account_id} not found.",
            status_code=404,
        )


class TransactionNotFoundError(BankingException):
    def __init__(self, transaction_id: int):
        super().__init__(
            code="TRANSACTION_NOT_FOUND",
            message=f"Transaction with id {transaction_id} not found.",
            status_code=404,
        )


class TransferNotFoundError(BankingException):
    def __init__(self, transfer_id: int):
        super().__init__(
            code="TRANSFER_NOT_FOUND",
            message=f"Transfer with id {transfer_id} not found.",
            status_code=404,
        )


class InsufficientBalanceError(BankingException):
    def __init__(self, current_balance: Any, requested_amount: Any):
        super().__init__(
            code="INSUFFICIENT_BALANCE",
            message=(
                f"Insufficient balance. Current balance is {current_balance}, "
                f"requested debit amount is {requested_amount}."
            ),
            status_code=400,
            detail={"current_balance": str(current_balance), "requested_amount": str(requested_amount)},
        )


class DuplicateTransactionError(BankingException):
    def __init__(self, account_id: int, reference_id: str):
        super().__init__(
            code="DUPLICATE_TRANSACTION",
            message=(
                f"A transaction with reference_id '{reference_id}' already exists "
                f"for account {account_id}."
            ),
            status_code=409,
            detail={"account_id": account_id, "reference_id": reference_id},
        )


class DuplicateTransferError(BankingException):
    def __init__(self, reference_id: str):
        super().__init__(
            code="DUPLICATE_TRANSFER",
            message=f"A transfer with reference_id '{reference_id}' already exists.",
            status_code=409,
            detail={"reference_id": reference_id},
        )


class InvalidTransferError(BankingException):
    def __init__(self, message: str):
        super().__init__(
            code="INVALID_TRANSFER",
            message=message,
            status_code=400,
        )


class InvalidPaginationError(BankingException):
    def __init__(self, message: str):
        super().__init__(
            code="INVALID_PAGINATION",
            message=message,
            status_code=400,
        )
