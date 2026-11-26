"""Keyframe prompts, shot commands, and assembly. No network and no FFmpeg process."""

from __future__ import annotations

import base64
import json

import pytest

from pipeline.assemble import (
    _end_card_command,
    build_export_command,
    build_mix_command,
    build_srt,
    render_film,
    write_ass,
)
from pipeline.cache import fingerprint
from pipeline.errors import CredentialsError, PermanentProviderError, PipelineError, TransientProviderError
from pipeline.keyframes import (
    CloudflareFluxProvider,
    compose_keyframe_prompt,
    keyframe_inputs,
    run_keyframes,
)
from pipeline.music import load_score
from pipeline.shots import build_shot_command, ken_burns_filter, run_shots, wan_input_path
from pipeline.validator import load_and_validate
from tests.conftest import silent_wav


def test_keyframe_prompt_prepends_the_locked_description(root):
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    shot = next(item for item in storyboard["shots"] if item["id"] == "07")
    description = storyboard["characters"]["young_brother"]["description"]
    prompt = compose_keyframe_prompt(storyboard, shot)
    assert len(prompt) <= 2048
    assert prompt.startswith(description + "\n")
    assert shot["image_prompt"] in prompt
    assert "navy-blue v-neck knit sweater" in prompt
    assert "Avoid:" in prompt
    assert "glamorous smoking" in prompt.split("Avoid:", 1)[1]
    assert "coughing" in prompt
    dusk = next(item for item in storyboard["shots"] if item["id"] == "05")
    dusk_prompt = compose_keyframe_prompt(storyboard, dusk)
    kept = next(item for item in storyboard["shots"] if item["id"] == "01")
    kept_prompt = compose_keyframe_prompt(storyboard, kept)
    assert "no cups" in dusk_prompt.lower()
    assert "tall glass tumblers" not in dusk_prompt
    assert "tall glass tumblers" in kept_prompt


def test_one_image_prompt_change_does_not_touch_other_shots(root):
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    before = [
        fingerprint(keyframe_inputs(storyboard, shot, model="m", steps=4))
        for shot in storyboard["shots"]
    ]
    storyboard["shots"][6]["image_prompt"] += " The wall paint is a flat warm beige."
    after = [
        fingerprint(keyframe_inputs(storyboard, shot, model="m", steps=4))
        for shot in storyboard["shots"]
    ]
    assert before[6] != after[6]
    assert before[:6] == after[:6]
    assert before[7:] == after[7:]


def test_cloudflare_request_shape_and_missing_credentials(settings):
    with pytest.raises(CredentialsError, match="No request was sent"):
        CloudflareFluxProvider(None, None)

    class Session:
        def __init__(self) -> None:
            self.calls = []

        def post(self, url, headers=None, json=None, timeout=None):
            self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})

            class Response:
                status_code = 200
                headers = {"Content-Type": "application/json"}
                content = b""

                def json(self):
                    return {"success": True, "result": {"image": base64.b64encode(b"\xff\xd8\xff").decode()}}

            return Response()

    session = Session()
    provider = CloudflareFluxProvider("account-1", "token-secret-value", session=session)
    image = provider.generate(prompt="a centered gate", model="@cf/black-forest-labs/flux-1-schnell", seed=7, steps=4)
    assert image.startswith(b"\xff\xd8")
    call = session.calls[0]
    assert call["url"].endswith("/accounts/account-1/ai/run/@cf/black-forest-labs/flux-1-schnell")
    assert call["headers"]["Authorization"] == "Bearer token-secret-value"
    assert call["json"] == {"prompt": "a centered gate", "steps": 4}
    with pytest.raises(PermanentProviderError, match="multipart"):
        provider.generate(prompt="x", model="@cf/black-forest-labs/flux-2-dev", seed=1, steps=4)
    assert len(session.calls) == 1


def test_klein_attaches_the_brother_reference_as_input_image_0():
    class Session:
        def __init__(self) -> None:
            self.calls = []

        def post(self, url, headers=None, json=None, files=None, timeout=None):
            self.calls.append({"url": url, "json": json, "files": files})

            class Response:
                status_code = 200
                headers = {"Content-Type": "application/json"}
                content = b""

                def json(self):
                    return {"success": True, "result": {"image": base64.b64encode(b"\xff\xd8\xff").decode()}}

            return Response()

    session = Session()
    provider = CloudflareFluxProvider("account-1", "token", session=session)
    png = b"\x89PNG\r\n\x1a\nfake"
    provider.generate(
        prompt="A 10-to-12-year-old Ethiopian boy.",
        model="@cf/black-forest-labs/flux-2-klein-4b",
        seed=3,
        steps=4,
        references=[("young_brother_ref.png", png)],
        width=1024,
        height=1024,
    )
    files = dict(session.calls[0]["files"])
    assert session.calls[0]["json"] is None
    assert files["prompt"] == (None, "A 10-to-12-year-old Ethiopian boy.")
    assert files["input_image_0"][1] == png
    assert "seed" not in files
    assert session.calls[0]["url"].endswith("/@cf/black-forest-labs/flux-2-klein-4b")


def test_cloudflare_400_includes_the_model_message():
    class Session:
        def post(self, url, headers=None, json=None, timeout=None):
            class Response:
                status_code = 400
                headers = {"Content-Type": "application/json"}
                content = b""
                text = ""

                def json(self):
                    return {
                        "success": False,
                        "errors": [{"message": "Additional or unevaluated properties '/seed'"}],
                    }

            return Response()

    provider = CloudflareFluxProvider("account-1", "token", session=Session())
    with pytest.raises(PermanentProviderError, match="'/seed'"):
        provider.generate(
            prompt="a painted wall",
            model="@cf/black-forest-labs/flux-1-schnell",
            seed=1001,
            steps=4,
        )


def test_keyframe_cache_and_retry(settings):
    storyboard = load_and_validate(settings.storyboard_path, settings.schema_path)
    delays: list[float] = []

    class Flaky:
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, **_kwargs) -> bytes:
            self.calls += 1
            if self.calls < 3:
                raise TransientProviderError("rate limited")
            return b"\xff\xd8\xff"

    flaky = Flaky()
    first = run_keyframes(settings, scene="01", provider=flaky, sleeper=delays.append)
    assert flaky.calls == 3
    assert delays == [1.0, 2.0]
    assert first[0].cached is False
    second = run_keyframes(settings, scene="01", provider=flaky, sleeper=delays.append)
    assert flaky.calls == 3
    assert second[0].cached is True
    log_text = settings.log_path.read_text(encoding="utf-8")
    assert "token" not in log_text.lower() or "fingerprint" in log_text
    assert storyboard["shots"][0]["id"] == "01"


def test_shot_command_uses_wan_when_present_and_ken_burns_otherwise(settings):
    storyboard = load_and_validate(settings.storyboard_path, settings.schema_path)
    shot = storyboard["shots"][0]
    wav = settings.narration_dir / "shot_01.wav"
    wav.parent.mkdir(parents=True)
    wav.write_bytes(silent_wav(0.5))
    image = settings.output_dir / "keyframes" / "shot_01.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"jpeg")
    seen: list[list[str]] = []
    run_shots(settings, scene="01", runner=seen.append, ffmpeg="ffmpeg")
    assert "zoompan" in seen[0][seen[0].index("-vf") + 1]
    assert str(image) in seen[0]

    wan = wan_input_path(settings.output_dir, shot["id"])
    wan.parent.mkdir(parents=True)
    wan.write_bytes(b"wan-clip")
    run_shots(settings, scene="01", runner=seen.append, ffmpeg="ffmpeg")
    assert "-stream_loop" in seen[1]
    assert str(wan) in seen[1]
    assert "zoompan" not in seen[1]
    assert "pad=1080:1080" in seen[1][seen[1].index("-vf") + 1]

    kaggle = settings.root / "kaggle_outputs" / "shots" / "shot_01.mp4"
    wan.unlink()
    kaggle.parent.mkdir(parents=True)
    kaggle.write_bytes(b"kaggle-wan")
    run_shots(settings, scene="01", runner=seen.append, ffmpeg="ffmpeg")
    assert str(kaggle) in seen[2]
    assert "-stream_loop" in seen[2]

    slow = build_shot_command(
        image=None, wan=wan, output=settings.output_dir / "shots" / "shot_01.mp4",
        duration_sec=2.0, motion={}, source_duration=2.4, ffmpeg="ffmpeg",
    )
    assert "-stream_loop" not in slow
    assert "setpts=" not in slow[slow.index("-vf") + 1]
    assert "-t" in slow
    held = build_shot_command(
        image=None, wan=wan, output=settings.output_dir / "shots" / "shot_01.mp4",
        duration_sec=2.0, motion={}, source_duration=8.0, ffmpeg="ffmpeg",
    )
    assert "-stream_loop" not in held
    assert "setpts=" not in held[held.index("-vf") + 1]
    zoom_in = ken_burns_filter({"zoom": "zoom_in", "pan": "pan_left"}, 25)
    assert "1.0+0.12*on/25" in zoom_in
    assert "1-on/25" in zoom_in


def test_exports_keep_the_whole_square_and_size_the_captions(tmp_path):
    picture = tmp_path / "picture.mp4"
    audio = tmp_path / "mixed.wav"
    shots = [{"subtitle_en": "People came again and again to buy a drink and to talk."}]
    vertical_ass = tmp_path / "film_9x16.ass"
    horizontal_ass = tmp_path / "film_16x9.ass"
    tall = write_ass(shots, [4.0], vertical_ass, width=1080, height=1920)
    wide = write_ass(shots, [4.0], horizontal_ass, width=1920, height=1080)
    vertical = " ".join(
        build_export_command(
            picture, audio, vertical_ass, tmp_path / "v.mp4",
            width=1080, height=1920, title="t", ffmpeg="ffmpeg",
        )
    )
    horizontal = " ".join(
        build_export_command(
            picture, audio, horizontal_ass, tmp_path / "h.mp4",
            width=1920, height=1080, title="t", ffmpeg="ffmpeg",
        )
    )
    assert "force_original_aspect_ratio=decrease" in vertical
    assert "pad=1080:1920" in vertical
    assert "crop=" not in vertical
    assert "pad=1920:1080" in horizontal
    assert "PlayResX: 1080" in tall and "PlayResY: 1920" in tall
    assert "PlayResX: 1920" in wide and "PlayResY: 1080" in wide
    assert "Style: Default,Arial,36," in tall
    assert "Style: Default,Arial,32," in wide
    assert ",2,64,64,120,1" in tall
    assert ",2,280,280,22,1" in wide


def test_end_card_escapes_a_windows_drive_colon(tmp_path):
    text = tmp_path / "end_card.txt"
    text.write_text("This film was made with artificial intelligence.", encoding="utf-8")
    command = _end_card_command(text, tmp_path / "end.mp4", 3, ffmpeg="ffmpeg")
    draw = command[command.index("-vf") + 1]
    assert "textfile='C:" not in draw
    assert r"\:/" in draw


def test_mix_ducks_music_and_normalizes_loudness(tmp_path):
    narration = tmp_path / "narration.wav"
    music = tmp_path / "score.wav"
    output = tmp_path / "mixed.wav"
    silent = build_mix_command(narration, None, output, ffmpeg="ffmpeg")
    ducked = build_mix_command(narration, music, output, ffmpeg="ffmpeg")
    silent_text = " ".join(silent)
    ducked_text = " ".join(ducked)
    assert "sidechaincompress" not in silent_text
    assert "loudnorm=I=-14" in silent_text
    assert "sidechaincompress" in ducked_text
    assert "loudnorm=I=-14" in ducked_text


def test_srt_timing_and_assembly_commands(settings):
    cues = build_srt(
        [{"subtitle_en": "First line.\n\nSecond sentence."}, {"subtitle_en": "Next."}],
        [1.5, 2.0],
    )
    assert "00:00:00,000 --> 00:00:01,500" in cues
    assert "00:00:01,500 --> 00:00:03,500" in cues
    assert "\n\nSecond" not in cues
    assert "First line.\nSecond sentence." in cues

    storyboard = load_and_validate(settings.storyboard_path, settings.schema_path)
    for shot in storyboard["shots"]:
        wav = settings.narration_dir / f"shot_{shot['id']}.wav"
        wav.parent.mkdir(parents=True, exist_ok=True)
        wav.write_bytes(silent_wav(0.4))
        video = settings.output_dir / "shots" / f"shot_{shot['id']}.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(b"video")
    seen: list[list[str]] = []
    result = render_film(settings, runner=seen.append, ffmpeg="ffmpeg")
    joined = "\n".join(" ".join(command) for command in seen)
    assert "sine=frequency=196" in joined
    assert "sidechaincompress" in joined
    assert "-stream_loop" in joined
    assert "assemble/timed/shot_01.mp4" in joined.replace("\\", "/")
    assert "loudnorm=I=-14" in joined
    assert "final_9x16.mp4" in joined
    assert "final_16x9.mp4" in joined
    assert result.subtitle_path.is_file()
    assert result.warning is not None
    assert "underscore" in result.warning
    assert load_score(settings, storyboard) is None

    score = settings.output_dir / "music" / "score.wav"
    score.parent.mkdir(parents=True, exist_ok=True)
    score.write_bytes(silent_wav(1.0))
    seen.clear()
    # The first render stored a cache entry for files the fake runner never wrote.
    # A real score changes the fingerprint, so this call plans a ducked mix.
    render_film(settings, runner=seen.append, ffmpeg="ffmpeg")
    ducked = "\n".join(" ".join(command) for command in seen)
    assert "sidechaincompress" in ducked
    assert "sine=frequency=196" not in ducked


def test_assembly_names_missing_shots(settings):
    with pytest.raises(PipelineError, match="shot_01.mp4"):
        render_film(settings, runner=lambda _command: None, ffmpeg="ffmpeg")
