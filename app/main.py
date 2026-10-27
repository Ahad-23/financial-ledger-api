import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import accounts, health, transactions, transfers
from app.config import get_settings
from app.exceptions import BankingException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("banking_api")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up %s in %s mode...", settings.app_name, settings.app_env)
    yield
    logger.info("Shutting down %s...", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Atomic banking ledger API with transaction idempotency and deadlock-safe transfers.",
    lifespan=lifespan,
)

# Register route modules
app.include_router(health.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(transfers.router)


@app.exception_handler(BankingException)
def handle_banking_exception(request: Request, exc: BankingException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error.get("loc", []))
        errors.append(
            {
                "field": field_path,
                "message": error.get("msg"),
                "type": error.get("type"),
            }
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Invalid request data.",
            "detail": errors,
        },
    )


@app.exception_handler(HTTPException)
def handle_http_exception(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": "HTTP_ERROR",
            "message": exc.detail if isinstance(exc.detail, str) else "HTTP error",
            "detail": exc.detail if not isinstance(exc.detail, str) else None,
        },
    )


@app.exception_handler(Exception)
def handle_unexpected_exception(request: Request, exc: Exception):
    logger.exception("Unexpected error while handling request: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred.",
            "detail": None,
        },
    )
