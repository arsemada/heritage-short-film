"""Shared fixtures. Tests copy the storyboard into a temp project so they never write logs or audio into the repository."""

from __future__ import annotations

import io
import shutil
import wave
from pathlib import Path

import pytest

from pipeline.config import Settings

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def root() -> Path:
    return ROOT


@pytest.fixture
def settings(tmp_path: Path, root: Path) -> Settings:
    project = tmp_path / "project"
    schema_dir = project / "schema"
    schema_dir.mkdir(parents=True)
    shutil.copy(root / "storyboard.json", project / "storyboard.json")
    shutil.copy(root / "schema" / "storyboard.schema.json", schema_dir / "storyboard.schema.json")
    return Settings(
        root=project,
        storyboard_path=project / "storyboard.json",
        schema_path=schema_dir / "storyboard.schema.json",
        output_dir=project / "outputs",
        log_path=project / "logs" / "runs.jsonl",
        cache_manifest_path=project / "outputs" / "cache" / "manifest.json",
        gemini_api_key=None,
        cloudflare_account_id=None,
        cloudflare_api_token=None,
        tts_provider="gemini",
        tts_model="gemini-3.8-flash-tts",
        image_model="@cf/black-forest-labs/flux-1-schnell",
        image_steps=4,
    )


def silent_wav(seconds: float, sample_rate: int = 8000) -> bytes:
    """A valid silent WAV, small enough to use in tests."""
    frame_count = max(1, int(seconds * sample_rate))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frame_count)
    return buffer.getvalue()
