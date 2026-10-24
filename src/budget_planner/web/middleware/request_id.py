"""Per-request correlation id middleware.

Attaches a short random id to `request.state.request_id` and echoes it in the
`X-Request-Id` response header. The id is grep-able in logs and surfaced on
the 500 error page so a user can report it.
"""

from __future__ import annotations

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_HEADER = "X-Request-Id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Generate (or respect) a per-request id. Idempotent — never mutates
    request state once set."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        existing = request.headers.get(_HEADER)
        rid = existing if existing else uuid4().hex[:12]
        request.state.request_id = rid
        response = await call_next(request)
        response.headers[_HEADER] = rid
        return response
