"""Tests for well-known target roots resolution."""

from pathlib import Path

import pytest

from viper_health.collectors import target_roots
from viper_health.collectors.target_roots import (
    ALL_CATEGORIES,
    CATEGORY_BROWSER_CACHE,
    CATEGORY_CLOUD_SYNC,
    TargetRoot,
    get_all_targets,
    get_targets_for_category,
)


def test_all_categories_defined():
    assert CATEGORY_CLOUD_SYNC in ALL_CATEGORIES
    assert CATEGORY_BROWSER_CACHE in ALL_CATEGORIES
    assert len(ALL_CATEGORIES) == 4


def test_unknown_category_raises():
    with pytest.raises(ValueError, match="Unknown category"):
        get_targets_for_category("not_a_category")


def test_include_missing_returns_entries():
    # With include_missing, at least some templated roots should resolve
    roots = get_targets_for_category(CATEGORY_BROWSER_CACHE, include_missing=True)
    assert len(roots) > 0
    assert all(isinstance(r, TargetRoot) for r in roots)
    assert all(r.category == CATEGORY_BROWSER_CACHE for r in roots)


def test_existing_only_are_marked_exists():
    roots = get_targets_for_category(CATEGORY_CLOUD_SYNC, include_missing=False)
    # Every returned root (existing-only mode) must report exists=True
    assert all(r.exists for r in roots)


def test_get_all_targets_spans_categories():
    roots = get_all_targets(include_missing=True)
    categories = {r.category for r in roots}
    assert categories == set(ALL_CATEGORIES)


def test_paths_are_expanded(monkeypatch, tmp_path: Path):
    # Point a known env var at a temp dir and confirm expansion occurs
    fake = tmp_path / "FakeTemp"
    fake.mkdir()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    roots = get_targets_for_category(
        CATEGORY_BROWSER_CACHE, include_missing=True
    )
    # All resolved paths should be absolute and not contain % placeholders
    assert all("%" not in str(r.path) for r in roots)
