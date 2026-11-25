"""Load a storyboard and check it before any provider is called.

The checks are structural. They do not know which film this repository ships.
Exact narration text is the storyboard file's job, and this project's tests
compare the shipped ``storyboard.json`` with ``STORY.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from pipeline.errors import StoryboardError


def read_json(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise StoryboardError(f"Missing file: {path}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StoryboardError(f"{path.name} is not valid JSON: {exc.lineno}:{exc.colno} {exc.msg}") from exc
    if not isinstance(data, dict):
        raise StoryboardError(f"{path.name} must contain a JSON object.")
    return data


def schema_errors(storyboard: dict, schema: dict) -> list[str]:
    try:
        validator = Draft202012Validator(schema)
    except SchemaError as exc:
        raise StoryboardError(f"The storyboard schema is invalid: {exc.message}") from exc
    errors = sorted(validator.iter_errors(storyboard), key=_error_sort_key)
    return [_format_schema_error(error) for error in errors]


def structure_errors(storyboard: dict) -> list[str]:
    """Check ids, character references, and the planned runtime from ``meta``."""
    errors: list[str] = []
    shots = storyboard.get("shots")
    if not isinstance(shots, list):
        return ["shots: expected an array."]

    seen: set[str] = set()
    known_characters = set(storyboard.get("characters", {}))
    for index, shot in enumerate(shots):
        if not isinstance(shot, dict):
            errors.append(f"shots.{index}: expected an object.")
            continue
        shot_id = str(shot.get("id", index))
        if shot_id in seen:
            errors.append(f"shots.{shot_id}: duplicate shot id.")
        seen.add(shot_id)
        for name in shot.get("characters_present", []):
            if name not in known_characters:
                errors.append(f"shots.{shot_id}: unknown character '{name}'.")

    meta = storyboard.get("meta")
    if not isinstance(meta, dict):
        return errors + ["meta: expected an object."]
    try:
        low = float(meta["target_duration_min_sec"])
        high = float(meta["target_duration_max_sec"])
    except (KeyError, TypeError, ValueError):
        return errors + ["meta: target duration bounds are missing."]
    if high < low:
        errors.append("meta: target_duration_max_sec is below target_duration_min_sec.")
    if not errors:
        total = planned_runtime_sec(storyboard)
        if total < low or total > high:
            errors.append(
                f"Planned runtime is {total:.1f}s. It must stay between {low:g} and {high:g} seconds, including the end card."
            )
    return errors


def planned_runtime_sec(storyboard: dict) -> float:
    shot_total = sum(float(shot["duration_sec"]) for shot in storyboard["shots"])
    return shot_total + float(storyboard["end_card"]["duration_sec"])


def load_and_validate(storyboard_path: Path, schema_path: Path) -> dict:
    """Read the storyboard and raise ``StoryboardError`` when anything is wrong."""
    storyboard = read_json(storyboard_path)
    schema = read_json(schema_path)
    problems = schema_errors(storyboard, schema)
    problems.extend(structure_errors(storyboard))
    if problems:
        raise StoryboardError("\n".join(problems))
    return storyboard


def _error_sort_key(error: object) -> list[str]:
    path = getattr(error, "absolute_path", [])
    return [str(part) for part in path]


def _format_schema_error(error: object) -> str:
    path = ".".join(str(part) for part in getattr(error, "absolute_path", [])) or "<root>"
    return f"{path}: {getattr(error, 'message', 'invalid value')}"
