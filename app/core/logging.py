"""Structured JSON logging + request-ID middleware. Never log secrets."""
import json
import logging
import sys
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

REQUEST_ID_HEADER = "X-Request-ID"

_logger = logging.getLogger("eve")
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
_logger.addHandler(_handler)
_logger.setLevel(logging.INFO)
_logger.propagate = False


def log_event(level: str, msg: str, **fields: object) -> None:
    # Strip anything that looks like a secret before emitting.
    fields.pop("password", None)
    fields.pop("token", None)
    fields.pop("JWT_SECRET", None)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "msg": msg,
        **{k: str(v) for k, v in fields.items()},
    }
    getattr(_logger, level, _logger.info)(json.dumps(record))


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        log_event(
            "info",
            "request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        )
        return response
