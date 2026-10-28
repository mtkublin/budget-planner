"""ADR-0048 — domain-level colour helpers + PatchCategory semantics."""

from __future__ import annotations

import pytest

from budget_planner.domain.categories import PatchCategory, normalise_color


def test_normalise_color_lowercases() -> None:
    assert normalise_color("#AABBCC") == "#aabbcc"


def test_normalise_color_strips_whitespace() -> None:
    assert normalise_color("  #a1b2c3  ") == "#a1b2c3"


def test_normalise_color_none_passes_through() -> None:
    assert normalise_color(None) is None


def test_normalise_color_blank_becomes_none() -> None:
    assert normalise_color("") is None
    assert normalise_color("   ") is None


@pytest.mark.parametrize(
    "bad",
    [
        "not-a-color",
        "#abc",  # shorthand not allowed
        "#ggghhh",
        "aabbcc",  # missing hash
        "#aabbccdd",  # alpha not allowed
    ],
)
def test_normalise_color_rejects_invalid(bad: str) -> None:
    with pytest.raises(ValueError):
        normalise_color(bad)


def test_patch_no_change() -> None:
    assert PatchCategory().as_dict() == {}


def test_patch_sets_name() -> None:
    assert PatchCategory(name="Food").as_dict() == {"name": "Food"}


def test_patch_sets_color() -> None:
    assert PatchCategory(color="#112233").as_dict() == {"color": "#112233"}


def test_patch_clear_color_overrides_color() -> None:
    """ADR-0048 — clear_color is the explicit reset sentinel."""
    assert PatchCategory(color="#112233", clear_color=True).as_dict() == {"color": None}


def test_patch_combines_name_and_clear_color() -> None:
    assert PatchCategory(name="Food", clear_color=True).as_dict() == {
        "name": "Food",
        "color": None,
    }
