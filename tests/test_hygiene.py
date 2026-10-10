"""Regression tests for scripts/verify_hygiene.py scanning scope."""

import subprocess
import sys

from sentinel.config import settings

SCRIPT = settings.base_dir / "scripts" / "verify_hygiene.py"


def test_gitignored_raw_data_cache_is_exempt_from_forbidden_file_scan():
    """Files in the data/raw download cache are never committed, so they must not fail hygiene."""
    probe = settings.base_dir / "data" / "raw" / "_hygiene_probe.db"
    probe.parent.mkdir(parents=True, exist_ok=True)
    try:
        probe.write_text("probe")
        res = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        assert res.returncode == 0, res.stderr
        assert "_hygiene_probe.db" not in res.stderr
    finally:
        probe.unlink(missing_ok=True)
