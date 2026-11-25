"""Schema checks, structural checks, and the shipped film's exact Amharic."""

from __future__ import annotations

import copy
import json
import re

import pytest

from pipeline.errors import StoryboardError
from pipeline.validator import load_and_validate, planned_runtime_sec, schema_errors, structure_errors

LINE_RE = re.compile(r"^\*\*(\d{2}):\*\*\s*(.+)$", re.MULTILINE)
PROVERB_RE = re.compile(r"^\*\*(«[^»]+»)\*\*\s*$", re.MULTILINE)


def _approved_narration(story_text: str) -> tuple[dict[str, str], str]:
    normalized = story_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = {shot_id: text.strip() for shot_id, text in LINE_RE.findall(normalized)}
    proverbs = {match.strip() for match in PROVERB_RE.findall(normalized)}
    assert len(lines) == 10
    assert proverbs == {"«ሳይቃጠል በቅጠል።»"}
    return lines, proverbs.pop()


def test_storyboard_matches_schema(root):
    storyboard = load_and_validate(
        root / "storyboard.json",
        root / "schema" / "storyboard.schema.json",
    )
    assert len(storyboard["shots"]) == 10
    assert storyboard["meta"]["language"] == "am"
    assert storyboard["meta"]["tts_voice"] == "Kore"
    assert planned_runtime_sec(storyboard) == 82
    for shot in storyboard["shots"]:
        assert "centered" in shot["image_prompt"].lower()


def test_amharic_lines_and_proverb_are_exact(root):
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    lines, proverb = _approved_narration((root / "STORY.md").read_text(encoding="utf-8"))
    assert set(lines) == {shot["id"] for shot in storyboard["shots"]}
    for shot in storyboard["shots"]:
        assert shot["narration_am"] == lines[shot["id"]]
    assert storyboard["shots"][-1]["proverb_am"] == proverb
    assert proverb == "«ሳይቃጠል በቅጠል።»"


def test_schema_rejects_a_shot_missing_narration(root):
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    schema = json.loads((root / "schema" / "storyboard.schema.json").read_text(encoding="utf-8"))
    del storyboard["shots"][0]["narration_am"]
    errors = schema_errors(storyboard, schema)
    assert any("narration_am" in error for error in errors)


def _changed_line_ids(storyboard: dict, lines: dict[str, str]) -> list[str]:
    return [shot["id"] for shot in storyboard["shots"] if shot["narration_am"] != lines.get(shot["id"])]


def test_exact_line_check_rejects_a_rewrite(root):
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    lines, _proverb = _approved_narration((root / "STORY.md").read_text(encoding="utf-8"))
    assert _changed_line_ids(storyboard, lines) == []
    broken = copy.deepcopy(storyboard)
    broken["shots"][3]["narration_am"] = "ይህ የተቀየረ ጽሑፍ ነው።"
    assert _changed_line_ids(broken, lines) == ["04"]


def test_smoking_shot_is_not_instructional(root):
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    shot = next(item for item in storyboard["shots"] if item["id"] == "07")
    prompt = shot["image_prompt"].lower()
    assert "coughing" in prompt
    assert "no lighter" in prompt
    assert "subject centered" in prompt
    assert "how to smoke" not in prompt


def test_setting_is_an_urban_neighbourhood(root):
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    negative = storyboard["style_block"]["negative_prompt"].lower()
    assert "mud hut" in negative
    assert "urban" in storyboard["style_block"]["look"].lower()
    for shot in storyboard["shots"]:
        prompt = shot["image_prompt"].lower()
        assert "mud-plaster" not in prompt
        assert "netela" not in prompt
        assert "mud hut" not in prompt


def test_validate_rejects_an_out_of_range_plan(root):
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    schema = json.loads((root / "schema" / "storyboard.schema.json").read_text(encoding="utf-8"))
    storyboard["shots"][0]["duration_sec"] = 20
    storyboard["shots"][1]["duration_sec"] = 20
    assert schema_errors(storyboard, schema) == []
    errors = structure_errors(storyboard)
    assert any("Planned runtime" in error for error in errors)


def test_load_and_validate_raises_for_broken_json(tmp_path, root):
    broken = tmp_path / "storyboard.json"
    broken.write_text("{", encoding="utf-8")
    with pytest.raises(StoryboardError, match="not valid JSON"):
        load_and_validate(broken, root / "schema" / "storyboard.schema.json")
