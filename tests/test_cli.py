"""The validate command against the real repository files."""

from __future__ import annotations

import subprocess
import sys


def test_validate_command(root):
    completed = subprocess.run(
        [sys.executable, "-m", "pipeline", "validate"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Storyboard is valid: 10 shots" in completed.stdout
    assert "80.0 seconds" in completed.stdout
