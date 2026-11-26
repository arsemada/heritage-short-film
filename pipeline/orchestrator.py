"""Run one pipeline stage, retrying transient failures and skipping cached assets."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from pipeline.cache import AssetCache, fingerprint
from pipeline.config import Settings
from pipeline.errors import PipelineError, TransientProviderError
from pipeline.logger import log_event
from pipeline.narration import (
    create_tts_provider,
    duration_warning,
    narration_inputs,
    save_audio_bytes,
    spoken_text,
    wav_duration_seconds,
)
from pipeline.radio_cut import RadioCutResult, narration_wav_path, render_radio_cut
from pipeline.validator import load_and_validate, planned_runtime_sec

MAX_ATTEMPTS = 6
REQUEST_GAP_SEC = 12.0
RATE_LIMIT_WAITS = (15.0, 20.0, 30.0, 45.0, 60.0)


@dataclass(frozen=True)
class ShotResult:
    shot_id: str
    path: Path
    duration_sec: float
    cached: bool
    fingerprint: str


@dataclass(frozen=True)
class NarrationReport:
    shots: list[ShotResult]
    total_duration_sec: float
    warning: str | None
    run_id: str


def validate_project(settings: Settings) -> dict:
    return load_and_validate(settings.storyboard_path, settings.schema_path)


def run_narration(
    settings: Settings,
    *,
    scene: str | None = None,
    provider=None,
    sleeper=time.sleep,
    max_attempts: int = MAX_ATTEMPTS,
    run_id: str | None = None,
    clock=time.monotonic,
) -> NarrationReport:
    """Generate missing narration WAVs. A cache hit does not call the provider."""
    storyboard = validate_project(settings)
    selected = _select_shots(storyboard, scene)
    current_run = run_id or uuid.uuid4().hex
    try:
        active_provider = provider if provider is not None else create_tts_provider(
            settings.tts_provider,
            settings.gemini_api_key,
        )
    except PipelineError as exc:
        _log_stage_error(settings, current_run, str(exc))
        raise
    cache = AssetCache(settings.cache_manifest_path, settings.root)
    results: list[ShotResult] = []
    last_request_at: float | None = None

    for shot in selected:
        payload = narration_inputs(storyboard, shot)
        asset_key = f"narration:{shot['id']}"
        digest = fingerprint(payload)
        cached_path = cache.lookup(asset_key, digest)
        started = time.perf_counter()
        if cached_path is not None:
            duration = wav_duration_seconds(cached_path)
            print(
                f"shot {shot['id']}  cached  {cached_path}  ({duration:.2f}s)",
                flush=True,
            )
            _log(
                settings,
                run_id=current_run,
                shot=shot,
                model=payload["model"],
                digest=digest,
                latency=time.perf_counter() - started,
                cached=True,
                status="success",
                retry_count=0,
                duration=duration,
                voice=payload["voice"],
            )
            results.append(
                ShotResult(shot["id"], cached_path, duration, True, digest)
            )
            continue

        if last_request_at is not None:
            gap = REQUEST_GAP_SEC - (clock() - last_request_at)
            if gap > 0:
                print(
                    f"shot {shot['id']}  waiting {gap:.0f}s before the next Gemini request.",
                    flush=True,
                )
                sleeper(gap)
        print(f"shot {shot['id']}  requesting...", flush=True)
        try:
            audio, attempts = _synthesize_with_retries(
                provider=active_provider,
                text=spoken_text(shot),
                style=payload["style"],
                voice=payload["voice"],
                model=payload["model"],
                shot_id=shot["id"],
                sleeper=sleeper,
                max_attempts=max_attempts,
            )
        except PipelineError as exc:
            _log(
                settings,
                run_id=current_run,
                shot=shot,
                model=payload["model"],
                digest=digest,
                latency=time.perf_counter() - started,
                cached=False,
                status="error",
                retry_count=getattr(exc, "attempts", max_attempts) - 1,
                error=str(exc),
                voice=payload["voice"],
            )
            raise
        destination = narration_wav_path(settings.narration_dir, shot["id"])
        try:
            save_audio_bytes(destination, audio)
            duration = wav_duration_seconds(destination)
        except PipelineError as exc:
            _log(
                settings,
                run_id=current_run,
                shot=shot,
                model=payload["model"],
                digest=digest,
                latency=time.perf_counter() - started,
                cached=False,
                status="error",
                retry_count=attempts - 1,
                error=str(exc),
                voice=payload["voice"],
            )
            raise
        cache.store(asset_key, digest, destination)
        _log(
            settings,
            run_id=current_run,
            shot=shot,
            model=payload["model"],
            digest=digest,
            latency=time.perf_counter() - started,
            cached=False,
            status="success",
            retry_count=attempts - 1,
            duration=duration,
            voice=payload["voice"],
        )
        print(
            f"shot {shot['id']}  generated  {destination}  ({duration:.2f}s)",
            flush=True,
        )
        last_request_at = clock()
        results.append(ShotResult(shot["id"], destination, duration, False, digest))

    total = sum(item.duration_sec for item in results)
    warning = None
    if scene is None:
        meta = storyboard["meta"]
        warning = duration_warning(
            total,
            float(meta["target_duration_min_sec"]),
            float(meta["target_duration_max_sec"]),
        )
    return NarrationReport(results, total, warning, current_run)


def run_radio_cut(settings: Settings, *, run_id: str | None = None) -> RadioCutResult:
    storyboard = validate_project(settings)
    current_run = run_id or uuid.uuid4().hex
    output = settings.output_dir / "radio_cut.mp4"
    started = time.perf_counter()
    try:
        meta = storyboard["meta"]
        result = render_radio_cut(
            shots=storyboard["shots"],
            narration_dir=settings.narration_dir,
            output_path=output,
            title=meta["title"],
            voice=meta["tts_voice"],
            minimum_sec=float(meta["target_duration_min_sec"]),
            maximum_sec=float(meta["target_duration_max_sec"]),
            work_dir=settings.output_dir,
        )
    except PipelineError as exc:
        _log_radio(settings, current_run, time.perf_counter() - started, "error", error=str(exc))
        raise
    _log_radio(
        settings,
        current_run,
        time.perf_counter() - started,
        "success",
        duration=result.spoken_duration_sec,
    )
    return result


def planned_seconds(storyboard: dict) -> float:
    return planned_runtime_sec(storyboard)


def _synthesize_with_retries(
    *,
    provider,
    text: str,
    style: str,
    voice: str,
    model: str,
    shot_id: str,
    sleeper,
    max_attempts: int,
) -> tuple[bytes, int]:
    last_error: TransientProviderError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            audio = provider.synthesize(text=text, style=style, voice=voice, model=model)
            return audio, attempt
        except TransientProviderError as exc:
            last_error = exc
            last_error.attempts = attempt
            if attempt == max_attempts:
                break
            delay = _retry_delay(exc, attempt)
            print(
                f"shot {shot_id}  {exc} Waiting {delay:.0f}s, "
                f"attempt {attempt + 1} of {max_attempts}.",
                flush=True,
            )
            sleeper(delay)
        except PipelineError as exc:
            exc.attempts = attempt
            raise
    assert last_error is not None
    if _is_rate_limit(last_error):
        failure = TransientProviderError(
            f"{last_error} Shot {shot_id} was not saved. "
            "Wait a minute and run the same command. Finished shots are cached.",
            retry_after_sec=last_error.retry_after_sec,
        )
        failure.attempts = last_error.attempts
        raise failure
    raise last_error


def _retry_delay(exc: TransientProviderError, attempt: int) -> float:
    if _is_rate_limit(exc):
        index = min(attempt - 1, len(RATE_LIMIT_WAITS) - 1)
        delay = RATE_LIMIT_WAITS[index]
        hinted = exc.retry_after_sec
        if hinted is not None and hinted > delay:
            return min(60.0, float(hinted))
        return delay
    return min(8.0, float(2 ** (attempt - 1)))


def _is_rate_limit(exc: TransientProviderError) -> bool:
    text = str(exc).lower()
    return "429" in text or "too many requests" in text


def _select_shots(storyboard: dict, scene: str | None) -> list[dict]:
    shots = list(storyboard["shots"])
    if scene is None:
        return shots
    matches = [shot for shot in shots if shot["id"] == scene]
    if not matches:
        known = ", ".join(shot["id"] for shot in shots)
        raise PipelineError(f"Unknown scene '{scene}'. Known shot ids: {known}.")
    return matches


def _log(
    settings: Settings,
    *,
    run_id: str,
    shot: dict,
    model: str,
    digest: str,
    latency: float,
    cached: bool,
    status: str,
    retry_count: int,
    voice: str,
    duration: float | None = None,
    error: str | None = None,
) -> None:
    params: dict[str, object] = {
        "voice": voice,
        "fingerprint": digest,
        "retry_count": retry_count,
    }
    if duration is not None:
        params["duration_sec"] = round(duration, 3)
    event = {
        "run_id": run_id,
        "stage": "narration",
        "shot_id": shot["id"],
        "model": model,
        "params": params,
        "seed": shot["seed"],
        "latency_sec": round(latency, 3),
        "cached": cached,
        "status": status,
        "error": error,
    }
    log_event(settings.log_path, event, settings.secret_values())


def _log_stage_error(settings: Settings, run_id: str, error: str) -> None:
    log_event(
        settings.log_path,
        {
            "run_id": run_id,
            "stage": "narration",
            "shot_id": None,
            "model": None,
            "params": {},
            "seed": None,
            "latency_sec": 0,
            "cached": False,
            "status": "error",
            "error": error,
        },
        settings.secret_values(),
    )


def _log_radio(
    settings: Settings,
    run_id: str,
    latency: float,
    status: str,
    duration: float | None = None,
    error: str | None = None,
) -> None:
    params: dict[str, object] = {"output": "outputs/radio_cut.mp4"}
    if duration is not None:
        params["spoken_duration_sec"] = round(duration, 3)
    log_event(
        settings.log_path,
        {
            "run_id": run_id,
            "stage": "radio-cut",
            "shot_id": None,
            "model": None,
            "params": params,
            "seed": None,
            "latency_sec": round(latency, 3),
            "cached": False,
            "status": status,
            "error": error,
        },
        settings.secret_values(),
    )
