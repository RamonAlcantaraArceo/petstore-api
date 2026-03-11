"""Tests for pytest collection hooks."""

from __future__ import annotations

import pytest

from tests.conftest import pytest_collection_modifyitems


class DummyItem:
    """Minimal pytest item stub for collection hook tests."""

    def __init__(self, path: str) -> None:
        self.fspath = path
        self.keywords: dict[str, pytest.MarkDecorator] = {}

    def add_marker(self, marker: pytest.MarkDecorator) -> None:
        """Record markers by name like pytest does for keyword lookup."""
        self.keywords[marker.name] = marker


def test_collection_marks_windows_style_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """Collection hook marks Windows-style test paths consistently."""
    monkeypatch.delenv("TEST_BASE_URL", raising=False)
    monkeypatch.delenv("E2E_BASE_URL", raising=False)

    remote_item = DummyItem(r"C:\repo\tests\e2e\test_petstore_e2e.py")
    integration_item = DummyItem(r"C:\repo\tests\integration\test_petstore_integration.py")
    system_item = DummyItem(r"C:\repo\tests\system\test_petstore_system.py")

    pytest_collection_modifyitems([remote_item, integration_item, system_item])

    assert "remote_only" in remote_item.keywords
    assert "skip" in remote_item.keywords
    assert "memory_only" in integration_item.keywords
    assert "memory_only" in system_item.keywords
