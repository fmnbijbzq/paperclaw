"""Pytest plugins & fixtures for the project."""
from __future__ import annotations

import pytest

from tests.api_client import TEST_API_KEY


@pytest.fixture(autouse=True)
def _seed_api_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auto-set ``API_KEY`` so ``AppSettings()`` exposes the test token.

    This pairs with ``ASGITestClient`` which sends ``Authorization: Bearer
    test-api-key`` by default. Tests that explicitly need to verify the
    "missing API key" path can use ``monkeypatch.delenv("API_KEY")`` inside
    the test body.
    """
    monkeypatch.setenv("API_KEY", TEST_API_KEY)
