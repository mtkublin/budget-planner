"""Shared fixtures for web integration tests (TestClient on a temp DB)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from budget_planner.config import Settings
from budget_planner.db.connection import get_connection
from budget_planner.db.migrate import apply_migrations
from budget_planner.web.app import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    db_url = f"sqlite:///{(tmp_path / 'web.sqlite').as_posix()}"
    return Settings(_env_file=None, database_url=db_url)


@pytest.fixture
def _migrated(settings: Settings) -> Iterator[Settings]:
    conn = get_connection(settings)
    try:
        apply_migrations(conn)
    finally:
        conn.close()
    yield settings


@pytest.fixture
def client(_migrated: Settings) -> Iterator[TestClient]:
    app = create_app(settings=_migrated)
    with TestClient(app) as c:
        yield c
