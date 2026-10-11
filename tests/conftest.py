"""Test session setup: every test uses a throwaway SQLite file, never .runtime/sentinel.db.

Some API tests drop and recreate all tables; pointing them at the developer database
erased persisted runs (and broke a running demo server).
"""

import os
import tempfile
from pathlib import Path

_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="sentinel-tests-"))
os.environ["SENTINEL_DATABASE_URL"] = f"sqlite:///{_TEST_DB_DIR / 'sentinel-test.db'}"
