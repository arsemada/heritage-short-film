"""Narration stage, Gemini request shape, and the radio cut. No network calls."""

from __future__ import annotations

import base64
import json

import pytest

from pipeline.errors import CredentialsError, MissingFFmpegError, PermanentProviderError, TransientProviderError
from pipeline.narration import GeminiTTSProvider, duration_warning, spoken_text
from pipeline.orchestrator import run_narration
from pipeline.radio_cut import narration_wav_path, render_radio_cut
from pipeline.validator import load_and_validate
from tests.conftest import silent_wav


class RecordingProvider:
    def __init__(self, seconds: float = 0.2) -> None:
        self.calls: list[dict] = []
        self.seconds = seconds

    def synthesize(self, *, text: str, style: str, voice: str, model: str) -> bytes:
        self.calls.append({"text": text, "style": style, "voice": voice, "model": model})
        return silent_wav(self.seconds)


def test_spoken_text_keeps_each_approved_line(settings):
    storyboard = load_and_validate(settings.storyboard_path, settings.schema_path)
    for shot in storyboard["shots"][:-1]:
        assert spoken_text(shot) == shot["narration_am"]
    closing = storyboard["shots"][-1]
    assert spoken_text(closing) == closing["narration_am"] + "\n" + closing["proverb_am"]
    assert storyboard["meta"]["tts_style_instruction"] not in spoken_text(closing)


def test_generate_then_cache_then_regenerate_only_the_changed_shot(settings):
    provider = RecordingProvider()
    first = run_narration(settings, provider=provider, sleeper=lambda _delay: None)
    assert len(provider.calls) == 10
    assert all(not shot.cached for shot in first.shots)
    assert first.warning is not None

    second = run_narration(settings, provider=provider, sleeper=lambda _delay: None)
    assert len(provider.calls) == 10
    assert all(shot.cached for shot in second.shots)

    storyboard = json.loads(settings.storyboard_path.read_text(encoding="utf-8"))
    storyboard["shots"][0]["seed"] = 4242
    settings.storyboard_path.write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    third = run_narration(settings, provider=provider, sleeper=lambda _delay: None)
    assert len(provider.calls) == 11
    assert third.shots[0].cached is False
    assert all(shot.cached for shot in third.shots[1:])
    assert provider.calls[-1]["text"] == storyboard["shots"][0]["narration_am"]
    assert provider.calls[-1]["style"] == storyboard["meta"]["tts_style_instruction"]
    assert provider.calls[-1]["voice"] == "Kore"
    assert provider.calls[-1]["model"] == "gemini-3.8-flash-tts"


def test_transient_failures_are_retried_and_permanent_failures_are_not(settings):
    delays: list[float] = []

    class Flaky:
        def __init__(self) -> None:
            self.calls = 0

        def synthesize(self, **_kwargs) -> bytes:
            self.calls += 1
            if self.calls < 3:
                raise TransientProviderError("rate limited")
            return silent_wav(0.2)

    flaky = Flaky()
    report = run_narration(
        settings,
        scene="01",
        provider=flaky,
        sleeper=delays.append,
        max_attempts=3,
    )
    assert flaky.calls == 3
    assert delays == [1.0, 2.0]
    assert report.shots[0].cached is False
    assert report.warning is None

    class Bad:
        def __init__(self) -> None:
            self.calls = 0

        def synthesize(self, **_kwargs) -> bytes:
            self.calls += 1
            raise PermanentProviderError("bad request")

    bad = Bad()
    with pytest.raises(PermanentProviderError):
        run_narration(settings, scene="02", provider=bad, sleeper=delays.append)
    assert bad.calls == 1


def test_missing_api_key_does_not_call_the_provider(settings):
    with pytest.raises(CredentialsError, match="No request was sent"):
        GeminiTTSProvider(api_key=None)
    with pytest.raises(CredentialsError):
        run_narration(settings, scene="01")
    log_text = settings.log_path.read_text(encoding="utf-8")
    assert "GEMINI_API_KEY" in log_text
    assert "AIza" not in log_text


def test_gemini_request_keeps_style_out_of_the_transcript():
    class FakeInteractions:
        def __init__(self) -> None:
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs

            class Output:
                data = base64.b64encode(silent_wav(0.1)).decode("ascii")

            class Interaction:
                output_audio = Output()

            return Interaction()

    fake = FakeInteractions()

    class FakeClient:
        interactions = fake

    provider = GeminiTTSProvider(api_key=None, client=FakeClient())
    audio = provider.synthesize(
        text="ከታናሽ ወንድሜ ጋር።",
        style="Warm, unhurried Ethiopian storytelling.",
        voice="Kore",
        model="gemini-3.8-flash-tts",
    )
    sent = fake.kwargs
    content = sent["input"][0]["content"][0]
    assert content["text"] == "ከታናሽ ወንድሜ ጋር።"
    assert content["annotations"] == [
        {"type": "speech_metadata", "style": "Warm, unhurried Ethiopian storytelling."}
    ]
    assert "Warm" not in content["text"]
    assert sent["model"] == "gemini-3.8-flash-tts"
    assert sent["generation_config"]["speech_config"] == [{"voice": "Kore"}]
    assert audio[:4] == b"RIFF"


def test_duration_warning_bounds():
    assert duration_warning(60, 60, 90) is None
    assert duration_warning(90, 60, 90) is None
    assert duration_warning(59.99, 60, 90) is not None
    assert duration_warning(90.01, 60, 90) is not None


def test_radio_cut_builds_a_black_frame_command(settings):
    storyboard = load_and_validate(settings.storyboard_path, settings.schema_path)
    for shot in storyboard["shots"]:
        path = narration_wav_path(settings.narration_dir, shot["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(silent_wav(0.5))

    seen: dict[str, list[str]] = {}

    def runner(command: list[str]) -> None:
        seen["command"] = command

    result = render_radio_cut(
        shots=storyboard["shots"],
        narration_dir=settings.narration_dir,
        output_path=settings.output_dir / "radio_cut.mp4",
        title=storyboard["meta"]["title"],
        voice=storyboard["meta"]["tts_voice"],
        minimum_sec=60,
        maximum_sec=90,
        work_dir=settings.output_dir,
        runner=runner,
        ffmpeg="ffmpeg",
    )
    assert result.spoken_duration_sec == pytest.approx(5.0)
    command = seen["command"]
    assert command[0] == "ffmpeg"
    assert "color=c=black:s=1080x1920:r=25" in command
    assert "libx264" in command
    assert any(part.startswith("comment=") and "Kore" in part for part in command)
    concat = (settings.output_dir / "radio_cut_concat.txt").read_text(encoding="utf-8")
    assert "shot_01.wav" in concat
    assert "shot_10.wav" in concat
    assert result.warning is not None


def test_radio_cut_reports_duration_when_ffmpeg_is_missing(settings):
    storyboard = load_and_validate(settings.storyboard_path, settings.schema_path)
    for shot in storyboard["shots"]:
        path = narration_wav_path(settings.narration_dir, shot["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(silent_wav(0.5))
    with pytest.raises(MissingFFmpegError) as caught:
        render_radio_cut(
            shots=storyboard["shots"],
            narration_dir=settings.narration_dir,
            output_path=settings.output_dir / "radio_cut.mp4",
            title=storyboard["meta"]["title"],
            voice=storyboard["meta"]["tts_voice"],
            minimum_sec=60,
            maximum_sec=90,
            work_dir=settings.output_dir,
            ffmpeg="",
        )
    assert caught.value.spoken_duration_sec == pytest.approx(5.0)
