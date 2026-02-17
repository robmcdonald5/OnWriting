"""Shared test fixtures."""

import pytest

from ai_writer.config import Settings


@pytest.fixture
def test_settings():
    """Settings with fake keys for unit testing."""
    return Settings(
        google_api_key="fake-key-for-testing",
        langchain_tracing_v2=False,
        langchain_api_key="",
    )
