"""Common pytest fixtures."""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()
