"""Append-only JSONL logs. API keys are removed before anything is written."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

SECRET_FIELD_NAMES = {"api_key", "apikey", "authorization", "token", "secret", "password"}
_KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z\-_]{20,}")
_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|authorization|password)\b\s*[:=]\s*\S+"
)


def redact(value: str, secrets: list[str] | None = None) -> str:
    """Replace known secret values and common key patterns."""
    redacted = value
    for secret in secrets or []:
        if len(secret) >= 6:
            redacted = redacted.replace(secret, "[REDACTED]")
    redacted = _KEY_PATTERN.sub("[REDACTED]", redacted)
    redacted = _ASSIGNMENT_PATTERN.sub("[REDACTED]", redacted)
    return redacted


def log_event(path: Path, event: dict, secrets: list[str] | None = None) -> dict:
    """Write one JSON object as a single line and return the record that was stored."""
    record = _clean(event, secrets or [])
    record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def _clean(value: object, secrets: list[str]) -> object:
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if str(key).lower().replace("-", "_") in SECRET_FIELD_NAMES:
                continue
            cleaned[key] = _clean(item, secrets)
        return cleaned
    if isinstance(value, list):
        return [_clean(item, secrets) for item in value]
    if isinstance(value, str):
        return redact(value, secrets)
    return value
