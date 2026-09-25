"""Centralized API error types. Handlers are registered in main.py."""
from fastapi import status


class AppError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


class NotFound(AppError):
    status_code = status.HTTP_404_NOT_FOUND


class Conflict(AppError):
    status_code = status.HTTP_409_CONFLICT


class Forbidden(AppError):
    status_code = status.HTTP_403_FORBIDDEN


class BadRequest(AppError):
    status_code = status.HTTP_400_BAD_REQUEST


class Unauthorized(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
