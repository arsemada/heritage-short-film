"""Deterministic fingerprints and a small manifest of generated assets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def fingerprint(payload: dict) -> str:
    """SHA-256 of a canonical JSON payload.

    Key order and whitespace do not change the hash. Unicode text is hashed
    as UTF-8, so an Amharic line is part of the fingerprint.
    """
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AssetCache:
    """Remember which inputs produced which file, and skip work when they still match."""

    def __init__(self, manifest_path: Path, root: Path) -> None:
        self.manifest_path = manifest_path
        self.root = root
        self._assets: dict[str, dict[str, str]] = {}
        self._load()

    def lookup(self, key: str, expected: str) -> Path | None:
        entry = self._assets.get(key)
        if entry is None or entry.get("fingerprint") != expected:
            return None
        asset = self.root / entry["path"]
        if asset.is_file() and asset.stat().st_size > 0:
            return asset
        return None

    def store(self, key: str, expected: str, asset: Path) -> None:
        relative = asset.resolve().relative_to(self.root.resolve()).as_posix()
        self._assets[key] = {"fingerprint": expected, "path": relative}
        self._save()

    def _load(self) -> None:
        if not self.manifest_path.is_file():
            return
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        assets = data.get("assets")
        if isinstance(assets, dict):
            self._assets = assets

    def _save(self) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"assets": self._assets}, ensure_ascii=False, indent=2, sort_keys=True)
        temporary = self.manifest_path.with_suffix(".json.tmp")
        temporary.write_text(payload + "\n", encoding="utf-8")
        temporary.replace(self.manifest_path)
