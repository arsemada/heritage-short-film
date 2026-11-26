"""Keyframe images through Cloudflare Workers AI.

The default still is FLUX.1 [schnell], ``@cf/black-forest-labs/flux-1-schnell``.
Its live REST schema accepts ``prompt`` and ``steps`` only. Sending ``seed``
returns HTTP 400. The storyboard seed stays in the cache fingerprint.

Shots that include ``young_brother`` use ``@cf/black-forest-labs/flux-2-klein-4b``.
That model is on Workers AI, takes multipart form data, and accepts up to four
reference images named ``input_image_0`` through ``input_image_3``. Each
reference must be smaller than 512 by 512. Other FLUX.2 models are refused.

Character descriptions from ``characters_present`` are prepended verbatim.
"""

from __future__ import annotations

import base64
import hashlib
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from pipeline.cache import AssetCache, fingerprint
from pipeline.config import Settings
from pipeline.errors import CredentialsError, PermanentProviderError, PipelineError, TransientProviderError
from pipeline.ffmpeg_lookup import find_ffmpeg
from pipeline.logger import log_event
from pipeline.validator import load_and_validate

PROMPT_LIMIT = 2048
TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
SCHNELL_MODEL = "@cf/black-forest-labs/flux-1-schnell"
KLEIN_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"
YOUNG_BROTHER_ID = "young_brother"
REFERENCE_EDGE = 480
REFERENCE_NOTE = (
    "The young_brother is image 0. Keep that face, short curly black hair, and outfit identical."
)


@dataclass(frozen=True)
class KeyframeResult:
    shot_id: str
    path: Path
    cached: bool
    fingerprint: str


def keyframe_path(directory: Path, shot_id: str) -> Path:
    return directory / f"shot_{shot_id}.jpg"


def character_descriptions(storyboard: dict, shot: dict) -> list[str]:
    """Return each present character's description exactly as stored."""
    characters = storyboard.get("characters", {})
    lines: list[str] = []
    for name in shot.get("characters_present", []):
        entry = characters.get(name)
        if isinstance(entry, dict) and isinstance(entry.get("description"), str):
            lines.append(entry["description"])
    return lines


def compose_keyframe_prompt(
    storyboard: dict,
    shot: dict,
    limit: int = PROMPT_LIMIT,
    reference_note: str = "",
) -> str:
    """Prepend locked character text, then the shot, the look, and the avoid-list.

    Descriptions are copied verbatim and are never shortened to fit the cap.
    """
    locked = "\n".join(character_descriptions(storyboard, shot))
    prefix = f"{locked}\n" if locked else ""
    style = storyboard.get("style_block", {})
    visual = style.get("visual_style") or style.get("look", "")
    image_prompt = shot.get("image_prompt", "")
    if isinstance(image_prompt, str) and "no cups" in image_prompt.lower():
        visual = visual.replace(
            "tall glass tumblers of cloudy amber-brown traditional Ethiopian drink, ",
            "",
        )
    tail = " ".join(
        part.strip()
        for part in (
            shot.get("image_prompt", ""),
            visual,
            style.get("framing", ""),
            style.get("safety", ""),
            reference_note,
        )
        if isinstance(part, str) and part.strip()
    )
    negative = str(style.get("negative_prompt", "")).strip()
    avoid = f" Avoid: {negative}." if negative else ""
    budget = limit - len(prefix)
    if budget <= 0:
        return locked
    if len(tail) + len(avoid) <= budget:
        return prefix + tail + avoid
    if len(tail) <= budget:
        room = budget - len(tail) - 1
        if room > 20 and avoid:
            return f"{prefix}{tail} {avoid.strip()[:room].rstrip()}"
        return prefix + tail
    return prefix + tail[:budget]


def keyframe_inputs(
    storyboard: dict,
    shot: dict,
    *,
    model: str,
    steps: int,
    reference_note: str = "",
    reference_sha: str | None = None,
) -> dict:
    payload = {
        "stage": "keyframes",
        "shot_id": shot["id"],
        "prompt": compose_keyframe_prompt(storyboard, shot, reference_note=reference_note),
        "model": model,
        "steps": steps,
        "seed": shot["seed"],
    }
    if reference_sha is not None:
        payload["reference_sha"] = reference_sha
    return payload


class CloudflareFluxProvider:
    """POST a prompt to the documented Workers AI run URL. No call is made without both credentials."""

    name = "cloudflare-flux"

    def __init__(
        self,
        account_id: str | None,
        api_token: str | None,
        session: object | None = None,
    ) -> None:
        if session is None and (not account_id or not api_token):
            raise CredentialsError(
                "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required. No request was sent."
            )
        self._account_id = account_id or ""
        self._api_token = api_token or ""
        self._session = session

    def generate(
        self,
        *,
        prompt: str,
        model: str,
        seed: int,
        steps: int,
        references: list[tuple[str, bytes]] | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes:
        del seed  # Cache identity only. Schnell rejects it, and Klein shots omit it too.
        if not model.startswith("@cf/"):
            raise PermanentProviderError(
                f"Image model '{model}' is not a Cloudflare Workers AI model id. "
                f"Implemented models are {SCHNELL_MODEL} and {KLEIN_MODEL}."
            )
        if model != KLEIN_MODEL and "flux-2" in model:
            raise PermanentProviderError(
                "This FLUX.2 model is not enabled. Character references use "
                f"{KLEIN_MODEL}, which accepts multipart input_image_0. "
                "FLUX.2 [dev] is a different licence and is not called."
            )
        session = self._session if self._session is not None else self._build_session()
        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{self._account_id}/ai/run/{model}"
        )
        try:
            if model == KLEIN_MODEL:
                response = session.post(
                    url,
                    headers={"Authorization": f"Bearer {self._api_token}"},
                    files=_klein_form(prompt, references or [], width, height),
                    timeout=180,
                )
            else:
                response = session.post(
                    url,
                    headers={"Authorization": f"Bearer {self._api_token}"},
                    json={"prompt": prompt, "steps": steps},
                    timeout=180,
                )
        except Exception as exc:
            raise TransientProviderError(f"Cloudflare image request failed before a response: {exc}") from exc
        return _decode_image(response)

    def _build_session(self) -> object:
        try:
            import requests
        except ImportError as exc:
            raise PermanentProviderError(
                "requests is not installed. Run: python -m pip install -r requirements.txt"
            ) from exc
        return requests.Session()


def run_keyframes(
    settings: Settings,
    *,
    scene: str | None = None,
    provider=None,
    sleeper=time.sleep,
    max_attempts: int = MAX_ATTEMPTS,
    run_id: str | None = None,
) -> list[KeyframeResult]:
    """Generate missing keyframes. A matching cached JPEG is not requested again."""
    storyboard = load_and_validate(settings.storyboard_path, settings.schema_path)
    selected = _select(storyboard, scene)
    current_run = run_id or uuid.uuid4().hex
    try:
        active = provider if provider is not None else CloudflareFluxProvider(
            settings.cloudflare_account_id,
            settings.cloudflare_api_token,
        )
    except PipelineError as exc:
        _log(
            settings,
            run_id=current_run,
            shot_id=None,
            model=settings.image_model,
            seed=None,
            digest=None,
            latency=0,
            cached=False,
            status="error",
            retry_count=0,
            error=str(exc),
        )
        raise
    cache = AssetCache(settings.cache_manifest_path, settings.root)
    directory = settings.output_dir / "keyframes"
    results: list[KeyframeResult] = []
    brother_png: bytes | None = None
    brother_sha: str | None = None
    if any(YOUNG_BROTHER_ID in shot.get("characters_present", []) for shot in selected):
        reference = ensure_young_brother_reference(
            settings,
            storyboard,
            provider=active,
            sleeper=sleeper,
            max_attempts=max_attempts,
            run_id=current_run,
        )
        brother_png = reference.read_bytes()
        brother_sha = hashlib.sha256(brother_png).hexdigest()
    for shot in selected:
        uses_reference = brother_png is not None and YOUNG_BROTHER_ID in shot.get("characters_present", [])
        # One model for the whole film when the brother lock exists, so the drink house does not change style between shots.
        model = KLEIN_MODEL if YOUNG_BROTHER_ID in storyboard.get("characters", {}) else settings.image_model
        payload = keyframe_inputs(
            storyboard,
            shot,
            model=model,
            steps=settings.image_steps,
            reference_note=REFERENCE_NOTE if uses_reference else "",
            reference_sha=brother_sha if uses_reference else None,
        )
        digest = fingerprint(payload)
        key = f"keyframe:{shot['id']}"
        cached_path = cache.lookup(key, digest)
        started = time.perf_counter()
        if cached_path is not None:
            _log(
                settings,
                run_id=current_run,
                shot_id=shot["id"],
                model=payload["model"],
                seed=shot["seed"],
                digest=digest,
                latency=time.perf_counter() - started,
                cached=True,
                status="success",
                retry_count=0,
            )
            results.append(KeyframeResult(shot["id"], cached_path, True, digest))
            continue
        destination = keyframe_path(directory, shot["id"])
        try:
            image, attempts = _generate_with_retries(
                provider=active,
                prompt=payload["prompt"],
                model=payload["model"],
                seed=payload["seed"],
                steps=payload["steps"],
                sleeper=sleeper,
                max_attempts=max_attempts,
                references=[("young_brother_ref.png", brother_png)] if uses_reference else None,
                width=1024 if model == KLEIN_MODEL else None,
                height=1024 if model == KLEIN_MODEL else None,
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(image)
        except PipelineError as exc:
            _log(
                settings,
                run_id=current_run,
                shot_id=shot["id"],
                model=payload["model"],
                seed=shot["seed"],
                digest=digest,
                latency=time.perf_counter() - started,
                cached=False,
                status="error",
                retry_count=getattr(exc, "attempts", max_attempts) - 1,
                error=str(exc),
            )
            raise
        cache.store(key, digest, destination)
        _log(
            settings,
            run_id=current_run,
            shot_id=shot["id"],
            model=payload["model"],
            seed=shot["seed"],
            digest=digest,
            latency=time.perf_counter() - started,
            cached=False,
            status="success",
            retry_count=attempts - 1,
        )
        results.append(KeyframeResult(shot["id"], destination, False, digest))
    return results


def ensure_young_brother_reference(
    settings: Settings,
    storyboard: dict,
    *,
    provider,
    sleeper,
    max_attempts: int,
    run_id: str,
) -> Path:
    """Create the generated brother lock if this description is not already cached.

    The file is an AI picture of the fictional character. It is not a family photograph.
    """
    characters = storyboard.get("characters", {})
    entry = characters.get(YOUNG_BROTHER_ID)
    if not isinstance(entry, dict) or not isinstance(entry.get("description"), str):
        raise PipelineError(
            "storyboard.json has no young_brother description, so no reference image was requested."
        )
    description = entry["description"]
    prompt = (
        f"{description}\n"
        "Full-length centered portrait, facing the camera, plain worn plaster wall, "
        "even daylight, no other people, no text."
    )
    payload = {
        "stage": "reference",
        "character": YOUNG_BROTHER_ID,
        "prompt": prompt,
        "model": KLEIN_MODEL,
        "width": REFERENCE_EDGE,
        "height": REFERENCE_EDGE,
    }
    digest = fingerprint(payload)
    cache = AssetCache(settings.cache_manifest_path, settings.root)
    destination = settings.output_dir / "references" / "young_brother_ref.png"
    cached = cache.lookup("reference:young_brother", digest)
    if cached is not None:
        print(f"reference  young_brother  cached  {cached}", flush=True)
        return cached
    print("reference  young_brother  requesting...", flush=True)
    image, _attempts = _generate_with_retries(
        provider=provider,
        prompt=prompt,
        model=KLEIN_MODEL,
        seed=0,
        steps=4,
        sleeper=sleeper,
        max_attempts=max_attempts,
        width=REFERENCE_EDGE,
        height=REFERENCE_EDGE,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_reference_png(destination, image)
    cache.store("reference:young_brother", digest, destination)
    _log(
        settings,
        run_id=run_id,
        shot_id=None,
        model=KLEIN_MODEL,
        seed=None,
        digest=digest,
        latency=0,
        cached=False,
        status="success",
        retry_count=0,
    )
    print(f"reference  young_brother  generated  {destination}", flush=True)
    return destination


def _klein_form(
    prompt: str,
    references: list[tuple[str, bytes]],
    width: int | None,
    height: int | None,
) -> list[tuple[str, tuple]]:
    fields: list[tuple[str, tuple]] = [("prompt", (None, prompt))]
    if width is not None:
        fields.append(("width", (None, str(width))))
    if height is not None:
        fields.append(("height", (None, str(height))))
    for index, (name, blob) in enumerate(references[:4]):
        fields.append((f"input_image_{index}", (name, blob, "image/png")))
    return fields


def _write_reference_png(destination: Path, image: bytes) -> None:
    if image.startswith(b"\x89PNG") and _png_edge(image) < 512:
        destination.write_bytes(image)
        return
    source = destination.with_suffix(".source.jpg")
    source.write_bytes(image)
    command = [
        _ffmpeg_binary(),
        "-y",
        "-i",
        str(source),
        "-vf",
        f"scale={REFERENCE_EDGE}:{REFERENCE_EDGE}:force_original_aspect_ratio=decrease",
        "-frames:v",
        "1",
        str(destination),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise PermanentProviderError(
            "FFmpeg was not found, so the brother reference PNG was not written."
        ) from exc
    source.unlink(missing_ok=True)
    if completed.returncode != 0 or not destination.is_file():
        detail = (completed.stderr or "").strip().splitlines()
        reason = detail[-1] if detail else "FFmpeg did not write the PNG."
        raise PermanentProviderError(
            f"The brother reference could not be saved under 512 pixels. {reason}"
        )


def _ffmpeg_binary() -> str:
    found = find_ffmpeg()
    if found:
        return found
    raise PermanentProviderError(
        "FFmpeg was not found, so the brother reference PNG was not written."
    )


def _png_edge(image: bytes) -> int:
    if len(image) < 24:
        return 512
    width = int.from_bytes(image[16:20], "big")
    height = int.from_bytes(image[20:24], "big")
    return max(width, height)


def _generate_with_retries(
    *,
    provider,
    prompt,
    model,
    seed,
    steps,
    sleeper,
    max_attempts,
    references=None,
    width=None,
    height=None,
):
    last_error: TransientProviderError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            image = provider.generate(
                prompt=prompt,
                model=model,
                seed=seed,
                steps=steps,
                references=references,
                width=width,
                height=height,
            )
            return image, attempt
        except TransientProviderError as exc:
            last_error = exc
            last_error.attempts = attempt
            if attempt == max_attempts:
                break
            sleeper(min(8.0, 2 ** (attempt - 1)))
        except PipelineError as exc:
            exc.attempts = attempt
            raise
    assert last_error is not None
    raise last_error


def _decode_image(response: object) -> bytes:
    status = int(getattr(response, "status_code", 0) or 0)
    content_type = ""
    headers = getattr(response, "headers", {}) or {}
    if hasattr(headers, "get"):
        content_type = str(headers.get("Content-Type", "") or headers.get("content-type", ""))
    raw = getattr(response, "content", b"") or b""
    if status >= 400:
        detail = _error_detail(response)
        message = f"Cloudflare image request returned HTTP {status}."
        if detail:
            message = f"{message} {detail}"
        if status in TRANSIENT_STATUS_CODES:
            raise TransientProviderError(message)
        raise PermanentProviderError(message)
    if content_type.startswith("image/") and raw:
        return bytes(raw)
    payload = response.json() if hasattr(response, "json") else None
    if not isinstance(payload, dict):
        raise PermanentProviderError("Cloudflare image response was not JSON or an image.")
    if payload.get("success") is False:
        errors = payload.get("errors") or []
        message = errors[0].get("message") if errors and isinstance(errors[0], dict) else "request failed"
        raise PermanentProviderError(f"Cloudflare image request failed: {message}")
    result = payload.get("result", payload)
    image = result.get("image") if isinstance(result, dict) else result
    if not isinstance(image, str) or not image.strip():
        raise PermanentProviderError("Cloudflare image response did not include an image.")
    encoded = image.split(",", 1)[1] if image.startswith("data:") else image
    try:
        decoded = base64.b64decode(encoded)
    except (ValueError, TypeError) as exc:
        raise PermanentProviderError("Cloudflare image data was not valid base64.") from exc
    if not decoded:
        raise PermanentProviderError("Cloudflare returned an empty image.")
    return decoded


def _error_detail(response: object) -> str:
    payload = None
    if hasattr(response, "json"):
        try:
            payload = response.json()
        except (TypeError, ValueError):
            payload = None
    if isinstance(payload, dict):
        errors = payload.get("errors") or []
        if errors and isinstance(errors[0], dict):
            message = str(errors[0].get("message") or "").strip()
            if message:
                return message[:500]
    text = getattr(response, "text", "")
    if isinstance(text, str) and text.strip():
        return text.strip()[:500]
    return ""


def _select(storyboard: dict, scene: str | None) -> list[dict]:
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
    shot_id: str | None,
    model: str | None,
    seed: int | None,
    digest: str | None,
    latency: float,
    cached: bool,
    status: str,
    retry_count: int,
    error: str | None = None,
) -> None:
    params: dict[str, object] = {"retry_count": retry_count}
    if digest is not None:
        params["fingerprint"] = digest
    log_event(
        settings.log_path,
        {
            "run_id": run_id,
            "stage": "keyframes",
            "shot_id": shot_id,
            "model": model,
            "params": params,
            "seed": seed,
            "latency_sec": round(latency, 3),
            "cached": cached,
            "status": status,
            "error": error,
        },
        settings.secret_values(),
    )
