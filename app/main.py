"""FastAPI app factory: middleware, error handlers, routers, health."""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, bookings, centres, payments, tests, users, webhooks
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import RequestIDMiddleware

settings = get_settings()

app = FastAPI(
    title="EVE Healthcare Backend",
    version="0.1.0",
    description="Diagnostic bookings with simulated payments and idempotent webhooks.",
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    from app.core.logging import log_event

    log_event("error", "unhandled", error=str(exc)[:300])
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/health", tags=["health"], summary="Health check")
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(centres.router)
app.include_router(tests.router)
app.include_router(bookings.router)
app.include_router(payments.router)
app.include_router(webhooks.router)
