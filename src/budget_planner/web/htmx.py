"""HTMX helpers: request detection + response trigger packing."""

from __future__ import annotations

import json
from collections.abc import Iterable

from fastapi import Request
from fastapi.responses import Response


def is_htmx(request: Request) -> bool:
    """Return True if the request is an HTMX swap (per the `HX-Request` header)."""
    return request.headers.get("HX-Request") == "true"


def trigger(response: Response, *events: str) -> None:
    """Set an HX-Trigger header carrying one or more event names.

    HTMX accepts either a bare event name or a JSON object mapping event
    names to payloads. We always emit the JSON form so stacked events
    survive the HTMX parser.
    """
    if not events:
        return
    payload = dict.fromkeys(events, True)
    response.headers["HX-Trigger"] = json.dumps(payload)


def trigger_from_iterable(response: Response, events: Iterable[str]) -> None:
    trigger(response, *tuple(events))
