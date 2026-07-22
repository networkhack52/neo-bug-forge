"""Shared pytest fixtures and import-time setup for the Neo Bug Forge API tests.

Both ``api.py`` and ``bug_fixer.py`` read configuration from environment
variables at import time. We set harmless defaults here — before those modules
are imported by any test — so importing them never depends on the developer's
local shell environment.
"""

import os

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
os.environ.setdefault("API_SECRET_KEY", "test-secret")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

import httpx
import pytest


# ─── Factories for anthropic SDK exceptions ────────────────────────────────────
# The anthropic exception classes require a real httpx.Response/Request to
# construct. These helpers build throwaway ones so tests can simulate API errors.

def _fake_response(status_code: int = 429) -> httpx.Response:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return httpx.Response(status_code, request=request)


@pytest.fixture
def fake_response():
    return _fake_response
