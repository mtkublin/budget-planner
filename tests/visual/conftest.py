"""Shared fixtures for visual-regression tests (ADR-0027 §4).

The suite is opt-in: it is excluded from the default `pytest` run via the
`-m "not visual"` default marker expression and from CI unless
`CI_VISUAL=1`. The `just test-visual` recipe runs it; `just test-visual-update`
regenerates baselines after an intentional design change.
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Browser, sync_playwright

VISUAL_ROOT = Path(__file__).parent
BASELINES = VISUAL_ROOT / "baselines"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def live_server() -> Iterator[str]:
    """Boot uvicorn against the dev DB for the duration of the session.

    Routes the server at `127.0.0.1:<free-port>`. Blocks until `/` returns
    200 or raises after a 10 s timeout.
    """
    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    cmd = [
        "uv",
        "run",
        "uvicorn",
        "budget_planner.web.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    with subprocess.Popen(cmd, env=env) as proc:  # noqa: S603 — fixed args, local loopback port
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    if httpx.get(f"{base}/", timeout=1).status_code == 200:
                        break
                except httpx.HTTPError:
                    time.sleep(0.2)
            else:
                raise RuntimeError(f"uvicorn did not come up on {base}")
            yield base
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    with sync_playwright() as p:
        b = p.chromium.launch()
        try:
            yield b
        finally:
            b.close()


@pytest.fixture()
def update_baseline() -> bool:
    return bool(os.environ.get("VISUAL_UPDATE"))


@pytest.fixture()
def baselines_dir() -> Path:
    return BASELINES
