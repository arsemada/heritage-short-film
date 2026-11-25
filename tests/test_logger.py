"""Log records stay useful and never keep a secret."""

from __future__ import annotations

import json

from pipeline.logger import log_event


def test_log_event_drops_secrets(tmp_path):
    secret = "AIzaSyA1234567890123456789012"
    path = tmp_path / "runs.jsonl"
    record = log_event(
        path,
        {
            "stage": "narration",
            "shot_id": "01",
            "model": "gemini-3.8-flash-tts",
            "params": {"voice": "Kore", "api_key": secret},
            "seed": 1001,
            "latency_sec": 0.2,
            "cached": False,
            "status": "error",
            "error": f"request failed for api_key={secret}",
        },
        [secret],
    )
    stored = path.read_text(encoding="utf-8")
    assert secret not in stored
    assert "api_key" not in stored
    parsed = json.loads(stored)
    assert parsed["status"] == "error"
    assert parsed["params"]["voice"] == "Kore"
    assert "[REDACTED]" in parsed["error"]
    assert record["shot_id"] == "01"
