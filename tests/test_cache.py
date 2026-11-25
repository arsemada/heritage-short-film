"""Fingerprint and cache behaviour."""

from __future__ import annotations

import copy
import json

from pipeline.cache import fingerprint
from pipeline.narration import narration_inputs


def test_fingerprint_is_stable_and_changes_with_one_shot(root):
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    original = fingerprint(narration_inputs(storyboard, storyboard["shots"][6]))
    assert original == fingerprint(narration_inputs(storyboard, storyboard["shots"][6]))
    assert len(original) == 64

    changed = copy.deepcopy(storyboard)
    changed["shots"][6]["narration_am"] = changed["shots"][6]["narration_am"] + "።"
    assert fingerprint(narration_inputs(changed, changed["shots"][6])) != original

    untouched = storyboard["shots"][0]
    assert fingerprint(narration_inputs(storyboard, untouched)) == fingerprint(
        narration_inputs(changed, changed["shots"][0])
    )


def test_style_and_voice_are_part_of_the_fingerprint(root):
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    shot = storyboard["shots"][0]
    baseline = fingerprint(narration_inputs(storyboard, shot))

    different_voice = copy.deepcopy(storyboard)
    different_voice["meta"]["tts_voice"] = "Puck"
    assert fingerprint(narration_inputs(different_voice, different_voice["shots"][0])) != baseline

    different_model = copy.deepcopy(storyboard)
    different_model["meta"]["tts_model"] = "gemini-3.8-flash-lite-tts"
    assert fingerprint(narration_inputs(different_model, different_model["shots"][0])) != baseline
