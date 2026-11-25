"""Project paths and environment settings.

Secrets are read from the environment or a local ``.env`` file. They are not
written into settings dumps, logs, or error messages by the other modules.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_TTS_PROVIDER = "gemini"
DEFAULT_TTS_MODEL = "gemini-3.8-flash-tts"


@dataclass(frozen=True)
class Settings:
    """Paths and provider names for one pipeline run."""

    root: Path
    storyboard_path: Path
    schema_path: Path
    output_dir: Path
    log_path: Path
    cache_manifest_path: Path
    gemini_api_key: str | None
    cloudflare_account_id: str | None
    cloudflare_api_token: str | None
    tts_provider: str
    tts_model: str

    @property
    def narration_dir(self) -> Path:
        return self.output_dir / "narration"

    def secret_values(self) -> list[str]:
        """Non-empty secrets, used only to redact logs and errors."""
        values = [
            self.gemini_api_key,
            self.cloudflare_account_id,
            self.cloudflare_api_token,
        ]
        return [value for value in values if value]


def find_root(start: Path | None = None) -> Path:
    """Walk upward from ``start`` until ``storyboard.json`` is found."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "storyboard.json").is_file() and (candidate / "pipeline").is_dir():
            return candidate
    raise FileNotFoundError(
        "Could not find the project root. Run this command from a repository that contains storyboard.json and pipeline/."
    )


def load_settings(root: Path | None = None) -> Settings:
    """Load paths and credentials. Missing keys stay ``None`` so validation can run offline."""
    project_root = (root or find_root()).resolve()
    load_dotenv(project_root / ".env")
    output_dir = project_root / "outputs"
    return Settings(
        root=project_root,
        storyboard_path=project_root / "storyboard.json",
        schema_path=project_root / "schema" / "storyboard.schema.json",
        output_dir=output_dir,
        log_path=project_root / "logs" / "runs.jsonl",
        cache_manifest_path=output_dir / "cache" / "manifest.json",
        gemini_api_key=_blank_to_none(os.getenv("GEMINI_API_KEY")),
        cloudflare_account_id=_blank_to_none(os.getenv("CLOUDFLARE_ACCOUNT_ID")),
        cloudflare_api_token=_blank_to_none(os.getenv("CLOUDFLARE_API_TOKEN")),
        tts_provider=(os.getenv("TTS_PROVIDER") or DEFAULT_TTS_PROVIDER).strip(),
        tts_model=(os.getenv("TTS_MODEL") or DEFAULT_TTS_MODEL).strip(),
    )


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
