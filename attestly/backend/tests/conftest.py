import os
import tempfile

# Point every test at a throwaway DB before app modules import config.
_tmp = tempfile.mkdtemp(prefix="attestly_test_")
os.environ["ATTESTLY_DATA_DIR"] = _tmp
os.environ["ATTESTLY_DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ.pop("ANTHROPIC_API_KEY", None)   # force offline drafting in tests
os.environ.pop("STRIPE_SECRET_KEY", None)
