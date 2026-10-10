"""Verify one-command demo script and Makefile targets."""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_demo_script_exists_and_executable():
    demo_sh = REPO_ROOT / "scripts" / "dev" / "demo.sh"
    assert demo_sh.exists(), "scripts/dev/demo.sh must exist"
    assert os.access(demo_sh, os.X_OK), "scripts/dev/demo.sh must be executable"
    content = demo_sh.read_text()
    assert "uv run uvicorn sentinel.api.app:app" in content
    assert "trap cleanup EXIT" in content
    assert "/api/health" in content


def test_makefile_has_required_targets():
    makefile = REPO_ROOT / "Makefile"
    assert makefile.exists(), "Makefile must exist"
    content = makefile.read_text()
    for target in ["setup:", "demo:", "api:", "frontend:", "record:", "test:", "eval:"]:
        assert target in content, f"Makefile missing target {target}"
