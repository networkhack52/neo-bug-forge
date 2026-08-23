import os
import tempfile

# Point every test at a throwaway DB before app modules import config.
_tmp = tempfile.mkdtemp(prefix="attestly_test_")
os.environ["ATTESTLY_DATA_DIR"] = _tmp
os.environ["ATTESTLY_DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ.pop("ANTHROPIC_API_KEY", None)   # force offline drafting in tests
os.environ.pop("STRIPE_SECRET_KEY", None)
os.environ["ATTESTLY_RATE_LIMIT"] = "0"      # don't rate-limit the test suite's many signups

# Ensure the schema exists no matter which test file runs first (a file that
# never imports app.main — which inits at import — otherwise hits "no such table").
from app import db as _db  # noqa: E402

_db.init_db()

import pytest  # noqa: E402


@pytest.fixture
def client():
    """A TestClient bound to the app (no lifespan; the schema is inited above)."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
