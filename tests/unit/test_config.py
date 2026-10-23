from __future__ import annotations

import pytest

from budget_planner.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    get_settings.cache_clear()


def test_defaults_match_requirements() -> None:
    s = Settings(_env_file=None)
    assert s.base_currency == "PLN"
    assert s.display_timezone == "Europe/Warsaw"
    assert s.host == "127.0.0.1"
    assert s.port == 8000
    assert s.fx_api_url.startswith("https://")


def test_env_prefix_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUDGET_BASE_CURRENCY", "eur")
    monkeypatch.setenv("BUDGET_DISPLAY_TIMEZONE", "UTC")
    s = Settings(_env_file=None)
    assert s.base_currency == "EUR"
    assert s.display_timezone == "UTC"


def test_rejects_public_bind(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUDGET_HOST", "0.0.0.0")  # noqa: S104 — asserting rejection
    with pytest.raises(ValueError, match="loopback"):
        Settings(_env_file=None)


def test_rejects_bad_currency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUDGET_BASE_CURRENCY", "US1")
    with pytest.raises(ValueError, match="ISO 4217"):
        Settings(_env_file=None)


def test_rejects_unknown_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUDGET_DISPLAY_TIMEZONE", "Mars/Olympus")
    with pytest.raises(ValueError, match="unknown timezone"):
        Settings(_env_file=None)


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
