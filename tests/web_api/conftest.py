from typing import Any

import pytest


@pytest.fixture(autouse=True)
def auto_mock_rest_fixture(mock_rest: Any) -> None:
    """Auto use the mock rest fixture for all tests in this package."""
