"""Turn a keyframe or a finished Wan clip into a shot video.

A Wan clip is used when one is already on disk, in this order:
``outputs/shots/wan/shot_XX.mp4``, then ``kaggle_outputs/shots/shot_XX.mp4``.
A clip shorter than the narration is looped. A longer clip is trimmed at
normal speed so the picture ends with the line. The whole frame is fitted
into the square master. Anything else is FFmpeg Ken Burns from the keyframe.
The pipeline does not download or run Wan.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from pipeline.cache import AssetCache, fingerprint
from pipeline.config import Settings
from pipeline.errors import PipelineError
from pipeline.ffmpeg_lookup import find_ffmpeg
from pipeline.keyframes import keyframe_path
from pipeline.logger import log_event
from pipeline.narration import wav_duration_seconds
from pipeline.radio_cut import narration_wav_path
from pipeline.validator import load_and_validate

MASTER_SIZE = 1080
FRAME_RATE = 25


@dataclass(frozen=True)
class ShotVideoResult:
    shot_id: str
    path: Path
    duration_sec: float
    source: str
    cached: bool


def shot_output_path(output_dir: Path, shot_id: str) -> Path:
    return output_dir / "shots" / f"shot_{shot_id}.mp4"


def wan_input_path(output_dir: Path, shot_id: str) -> Path:
    return output_dir / "shots" / "wan" / f"shot_{shot_id}.mp4"


def kaggle_wan_path(root: Path, shot_id: str) -> Path:
    return root / "kaggle_outputs" / "shots" / f"shot_{shot_id}.mp4"


def find_wan_clip(root: Path, output_dir: Path, shot_id: str) -> Path | None:
    """The first non-empty Wan file dropped by hand or downloaded from Kaggle."""
    for path in (wan_input_path(output_dir, shot_id), kaggle_wan_path(root, shot_id)):
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def ken_burns_filter(motion: dict, frames: int) -> str:
    """A zoompan chain. Expressions avoid commas so FFmpeg keeps each option intact."""
    frames = max(frames, 1)
    zoom = motion.get("zoom", "none")
    pan = motion.get("pan", "none")
    if zoom in {"in_slow", "zoom_in"}:
        z_expr = f"1.0+0.12*on/{frames}"
    elif zoom in {"out_slow", "zoom_out"}:
        z_expr = f"1.12-0.12*on/{frames}"
    else:
        z_expr = "1"
    x_still = "iw/2-(iw/zoom/2)"
    y_still = "ih/2-(ih/zoom/2)"
    if pan in {"left_slow", "pan_left"}:
        x_expr = f"(iw-iw/zoom)*(1-on/{frames})"
        y_expr = y_still
    elif pan in {"right_slow", "pan_right"}:
        x_expr = f"(iw-iw/zoom)*on/{frames}"
        y_expr = y_still
    elif pan in {"up_slow", "pan_up"}:
        x_expr = x_still
        y_expr = f"(ih-ih/zoom)*(1-on/{frames})"
    else:
        x_expr = x_still
        y_expr = y_still
    return (
        f"scale={MASTER_SIZE * 2}:-1,"
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={frames}:s={MASTER_SIZE}x{MASTER_SIZE}:fps={FRAME_RATE}"
    )


def build_shot_command(
    *,
    image: Path | None,
    wan: Path | None,
    output: Path,
    duration_sec: float,
    motion: dict,
    ffmpeg: str = "ffmpeg",
    source_duration: float | None = None,
) -> list[str]:
    frames = max(1, round(duration_sec * FRAME_RATE))
    if wan is not None:
        fit = (
            f"scale={MASTER_SIZE}:{MASTER_SIZE}:force_original_aspect_ratio=decrease,"
            f"pad={MASTER_SIZE}:{MASTER_SIZE}:(ow-iw)/2:(oh-ih)/2:black,fps={FRAME_RATE}"
        )
        loop = True
        if source_duration is not None and source_duration > duration_sec + 0.05:
            loop = False
        command = [ffmpeg, "-y"]
        if loop:
            command.extend(["-stream_loop", "-1"])
        command.extend(
            [
                "-i",
                str(wan),
                "-t",
                f"{duration_sec:.3f}",
                "-vf",
                fit,
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(output),
            ]
        )
        return command
    if image is None:
        raise PipelineError("A shot needs a keyframe image or a Wan clip.")
    return [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(image),
        "-vf",
        ken_burns_filter(motion, frames),
        "-frames:v",
        str(frames),
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output),
    ]


def run_shots(
    settings: Settings,
    *,
    scene: str | None = None,
    runner=None,
    ffmpeg: str | None = None,
    run_id: str | None = None,
) -> list[ShotVideoResult]:
    """Write one silent master video per shot, matched to that shot's WAV length."""
    storyboard = load_and_validate(settings.storyboard_path, settings.schema_path)
    selected = [shot for shot in storyboard["shots"] if scene is None or shot["id"] == scene]
    if scene is not None and not selected:
        known = ", ".join(shot["id"] for shot in storyboard["shots"])
        raise PipelineError(f"Unknown scene '{scene}'. Known shot ids: {known}.")
    binary = find_ffmpeg() if ffmpeg is None else ffmpeg
    if not binary:
        raise PipelineError(
            "FFmpeg was not found on PATH, so the shot videos were not written."
        )
    current_run = run_id or uuid.uuid4().hex
    cache = AssetCache(settings.cache_manifest_path, settings.root)
    results: list[ShotVideoResult] = []
    for shot in selected:
        wav = narration_wav_path(settings.narration_dir, shot["id"])
        if not wav.is_file():
            raise PipelineError(
                f"Shot {shot['id']} needs {wav.name}. Generate it with: "
                "python -m pipeline run --stage narration"
            )
        duration = wav_duration_seconds(wav)
        wan = find_wan_clip(settings.root, settings.output_dir, shot["id"])
        image = keyframe_path(settings.output_dir / "keyframes", shot["id"])
        source = "wan" if wan is not None else "kenburns"
        if source == "kenburns" and not image.is_file():
            expected = wan_input_path(settings.output_dir, shot["id"])
            raise PipelineError(
                f"Shot {shot['id']} has no Wan clip at {expected.relative_to(settings.root).as_posix()} "
                f"or {kaggle_wan_path(settings.root, shot['id']).relative_to(settings.root).as_posix()} "
                f"and no keyframe at {image.relative_to(settings.root).as_posix()}. "
                "Generate the keyframe or add the Wan file."
            )
        source_duration = _media_duration(wan, binary) if wan is not None else None
        payload = {
            "stage": "shots",
            "shot_id": shot["id"],
            "source": source,
            "duration_sec": round(duration, 3),
            "motion": shot.get("fallback_ken_burns", {}),
            "motion_prompt": shot.get("motion_prompt", ""),
            "seed": shot["seed"],
            "media_sha256": _sha256(wan if wan is not None else image),
            "conform": "loop-or-slow-trim" if source == "wan" else "kenburns",
        }
        digest = fingerprint(payload)
        key = f"shot:{shot['id']}"
        destination = shot_output_path(settings.output_dir, shot["id"])
        cached_path = cache.lookup(key, digest)
        started = time.perf_counter()
        if cached_path is not None:
            _log(settings, current_run, shot, source, digest, time.perf_counter() - started, True, "success", duration)
            results.append(ShotVideoResult(shot["id"], cached_path, duration, source, True))
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        command = build_shot_command(
            image=None if source == "wan" else image,
            wan=wan if source == "wan" else None,
            output=destination,
            duration_sec=duration,
            motion=shot.get("fallback_ken_burns", {}),
            ffmpeg=binary,
            source_duration=source_duration,
        )
        try:
            (runner or _run_ffmpeg)(command)
        except PipelineError as exc:
            _log(
                settings,
                current_run,
                shot,
                source,
                digest,
                time.perf_counter() - started,
                False,
                "error",
                duration,
                error=str(exc),
            )
            raise
        if runner is None and not destination.is_file():
            raise PipelineError(f"FFmpeg finished without writing {destination.name}.")
        cache.store(key, digest, destination)
        _log(settings, current_run, shot, source, digest, time.perf_counter() - started, False, "success", duration)
        results.append(ShotVideoResult(shot["id"], destination, duration, source, False))
    return results


def _media_duration(path: Path, ffmpeg: str) -> float | None:
    """Seconds in a real media file. A placeholder or a missing probe returns None."""
    import subprocess

    ffprobe = str(Path(ffmpeg).with_name("ffprobe"))
    if Path(ffprobe).name == "ffprobe" and not Path(ffprobe).is_file():
        ffprobe = "ffprobe"
    try:
        completed = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        return float(completed.stdout.strip())
    except ValueError:
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_ffmpeg(command: list[str]) -> None:
    import subprocess

    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "FFmpeg failed.").strip()
        raise PipelineError(f"FFmpeg failed while building a shot.\n{detail[-1200:]}")


def _log(
    settings: Settings,
    run_id: str,
    shot: dict,
    source: str,
    digest: str,
    latency: float,
    cached: bool,
    status: str,
    duration: float,
    error: str | None = None,
) -> None:
    log_event(
        settings.log_path,
        {
            "run_id": run_id,
            "stage": "shots",
            "shot_id": shot["id"],
            "model": "wan-2.2" if source == "wan" else "ffmpeg-ken-burns",
            "params": {
                "source": source,
                "fingerprint": digest,
                "duration_sec": round(duration, 3),
            },
            "seed": shot["seed"],
            "latency_sec": round(latency, 3),
            "cached": cached,
            "status": status,
            "error": error,
        },
        settings.secret_values(),
    )
