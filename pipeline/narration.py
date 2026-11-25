"""Narration providers and audio helpers.

``GeminiTTSProvider`` is the default. Another provider can be registered and
selected with ``TTS_PROVIDER`` without changing the orchestrator.
"""

from __future__ import annotations

import base64
import wave
from pathlib import Path
from typing import NoReturn, Protocol

from pipeline.errors import CredentialsError, PermanentProviderError, PipelineError, TransientProviderError

TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}

PROVIDERS: dict[str, type] = {}


class TTSProvider(Protocol):
    """Something that turns an exact transcript into audio bytes."""

    name: str

    def synthesize(self, *, text: str, style: str, voice: str, model: str) -> bytes:
        """Return WAV bytes, or raw 16-bit mono PCM if the provider has no header."""


def register_tts_provider(name: str, provider_cls: type) -> None:
    """Make a provider available to ``TTS_PROVIDER``."""
    PROVIDERS[name] = provider_cls


def spoken_text(shot: dict) -> str:
    """Approved narration, plus the proverb on the shot that carries it.

    The proverb is appended as its own line. The stored ``narration_am`` value
    is not rewritten.
    """
    narration = shot["narration_am"]
    proverb = shot.get("proverb_am")
    if not proverb:
        return narration
    return f"{narration}\n{proverb}"


def narration_inputs(storyboard: dict, shot: dict) -> dict:
    """The exact inputs that change the narration asset."""
    meta = storyboard["meta"]
    return {
        "stage": "narration",
        "shot_id": shot["id"],
        "text": spoken_text(shot),
        "model": meta["tts_model"],
        "voice": meta["tts_voice"],
        "style": meta["tts_style_instruction"],
        "seed": shot["seed"],
        "response_format": "audio/wav",
    }


def duration_warning(total_sec: float, minimum_sec: float, maximum_sec: float) -> str | None:
    """Return a warning when measured speech is outside the storyboard's length."""
    if minimum_sec <= total_sec <= maximum_sec:
        return None
    return (
        f"Spoken narration is {total_sec:.2f}s, outside the {minimum_sec:g}–{maximum_sec:g} second target. "
        "The storyboard narration was not edited."
    )


def save_audio_bytes(path: Path, audio: bytes, sample_rate: int = 24000) -> None:
    """Write a WAV file. Raw PCM is wrapped. A RIFF payload is saved unchanged."""
    if not audio:
        raise PipelineError(f"No audio bytes to write for {path.name}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    if audio[:4] == b"RIFF":
        path.write_bytes(audio)
        return
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(audio)


def wav_duration_seconds(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            rate = handle.getframerate()
            frames = handle.getnframes()
    except wave.Error as exc:
        raise PipelineError(f"Invalid WAV file: {path.name}") from exc
    if rate <= 0 or frames <= 0:
        raise PipelineError(f"WAV file has no audio: {path.name}")
    return frames / float(rate)


class GeminiTTSProvider:
    """Gemini 3.8 Flash TTS through the documented interactions API.

    The transcript is sent as ``text``. Pace and tone go in ``speech_metadata.style``.
    The two are never joined into one script.
    """

    name = "gemini"

    def __init__(self, api_key: str | None, client: object | None = None) -> None:
        if client is None and not api_key:
            raise CredentialsError(
                "GEMINI_API_KEY is missing. Add it to .env. No request was sent."
            )
        self._api_key = api_key
        self._client = client

    def synthesize(self, *, text: str, style: str, voice: str, model: str) -> bytes:
        client = self._client if self._client is not None else self._build_client()
        try:
            interaction = client.interactions.create(
                model=model,
                input=[
                    {
                        "type": "user_input",
                        "content": [
                            {
                                "type": "text",
                                "text": text,
                                "annotations": [
                                    {
                                        "type": "speech_metadata",
                                        "style": style,
                                    }
                                ],
                            }
                        ],
                    }
                ],
                response_format={"type": "audio"},
                generation_config={"speech_config": [{"voice": voice}]},
            )
            payload = interaction.output_audio.data
        except (CredentialsError, PermanentProviderError, TransientProviderError):
            raise
        except Exception as exc:
            _raise_classified(exc)

        if isinstance(payload, str):
            try:
                audio = base64.b64decode(payload)
            except (ValueError, TypeError) as exc:
                raise PermanentProviderError("Gemini TTS returned audio that is not valid base64.") from exc
        elif isinstance(payload, (bytes, bytearray)):
            audio = bytes(payload)
        else:
            raise PermanentProviderError("Gemini TTS returned audio in an unexpected format.")
        if not audio:
            raise PermanentProviderError("Gemini TTS returned empty audio.")
        return audio

    def _build_client(self) -> object:
        try:
            from google import genai
        except ImportError as exc:
            raise PermanentProviderError(
                "google-genai is not installed. Run: python -m pip install -r requirements.txt"
            ) from exc
        return genai.Client(api_key=self._api_key, http_options={"api_version": "v1beta"})


def create_tts_provider(provider_name: str, api_key: str | None) -> TTSProvider:
    provider_cls = PROVIDERS.get(provider_name)
    if provider_cls is None:
        known = ", ".join(sorted(PROVIDERS)) or "(none)"
        raise PermanentProviderError(
            f"TTS provider '{provider_name}' is not implemented. Available providers: {known}."
        )
    return provider_cls(api_key)


def _raise_classified(exc: Exception) -> NoReturn:
    code = getattr(exc, "status_code", None)
    if code is None:
        code = getattr(exc, "code", None)
    name = type(exc).__name__.lower()
    message = str(exc) or type(exc).__name__
    if isinstance(code, int) and code in TRANSIENT_STATUS_CODES:
        raise TransientProviderError(message) from exc
    if "timeout" in name or "unavailable" in name or "connection" in name:
        raise TransientProviderError(message) from exc
    if isinstance(exc, AttributeError):
        if "interactions" in message:
            raise PermanentProviderError(
                "This google-genai install has no interactions.create. "
                "Upgrade with: python -m pip install 'google-genai>=2.25.0'."
            ) from exc
        raise PermanentProviderError("Gemini TTS response did not include audio.") from exc
    raise PermanentProviderError(message) from exc


register_tts_provider("gemini", GeminiTTSProvider)
