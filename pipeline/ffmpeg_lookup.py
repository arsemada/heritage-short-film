"""Find the FFmpeg binary, including a WinGet install this process has not inherited."""

from __future__ import annotations

import shutil
from pathlib import Path


def find_ffmpeg() -> str | None:
    """Return an ffmpeg executable path, or None when none is installed."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    shim = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe"
    if shim.is_file():
        return str(shim)
    return None
