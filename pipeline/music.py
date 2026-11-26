"""Locate an original score, or plan a quiet underscore when none is on disk.

ACE-Step runs in ``notebooks/kaggle_acestep.py``. This module does not call it.
Drop the chosen take at ``outputs/music/score.wav`` (or ``music.path``).
Assembly uses that file. If it is missing, assembly generates a low drone so
the mix still has something to duck under the voice.
"""

from __future__ import annotations

from pathlib import Path

from pipeline.config import Settings


def score_path(settings: Settings, storyboard: dict | None = None) -> Path:
    """The score file the storyboard names, or the default drop path."""
    raw = None
    if storyboard is not None:
        raw = (storyboard.get("music") or {}).get("path")
    if isinstance(raw, str) and raw.strip():
        path = Path(raw)
        if not path.is_absolute():
            path = settings.root / path
        return path
    return settings.output_dir / "music" / "score.wav"


def underscore_path(settings: Settings) -> Path:
    return settings.output_dir / "music" / "underscore.wav"


def load_score(settings: Settings, storyboard: dict | None = None) -> Path | None:
    """Return the score when a non-empty file is already on disk."""
    path = score_path(settings, storyboard)
    if path.is_file() and path.stat().st_size > 0:
        return path
    fallback = underscore_path(settings)
    if path != fallback and fallback.is_file() and fallback.stat().st_size > 0:
        return fallback
    return None


def build_underscore_command(output: Path, duration_sec: float, *, ffmpeg: str = "ffmpeg") -> list[str]:
    """A quiet low drone long enough for the film. It is not an ACE-Step score."""
    duration = max(float(duration_sec), 1.0)
    fade_out_at = max(duration - 2.0, 0.0)
    graph = (
        f"sine=frequency=196:sample_rate=48000:duration={duration:.3f},"
        "volume=0.03,lowpass=f=700,"
        f"afade=t=in:st=0:d=1.5,afade=t=out:st={fade_out_at:.3f}:d=2"
    )
    return [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        graph,
        "-c:a",
        "pcm_s16le",
        str(output),
    ]


def prepare_score(
    settings: Settings,
    storyboard: dict | None,
    duration_sec: float,
    *,
    ffmpeg: str = "ffmpeg",
) -> tuple[Path, str | None, list[str] | None]:
    """Return the mix file, a warning when it is only the drone, and the command that writes it."""
    found = load_score(settings, storyboard)
    if found is not None:
        return found, None, None
    path = underscore_path(settings)
    warning = (
        f"No score at {score_path(settings, storyboard).as_posix()}. "
        "A quiet generated underscore will be ducked under the narration."
    )
    return path, warning, build_underscore_command(path, duration_sec, ffmpeg=ffmpeg)
