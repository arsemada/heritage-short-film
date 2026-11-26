"""Stitch narration WAVs onto a black 9:16 frame for the radio-cut listening test."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from pipeline.errors import MissingFFmpegError, PipelineError
from pipeline.ffmpeg_lookup import find_ffmpeg
from pipeline.narration import duration_warning, wav_duration_seconds

RADIO_WIDTH = 1080
RADIO_HEIGHT = 1920
RADIO_FRAME_RATE = 25


def disclosure_comment(voice: str) -> str:
    """Metadata comment. The voice name comes from the storyboard, not from this module."""
    return (
        "AI-generated narration. "
        f"Voice: prebuilt TTS voice {voice}. No cloned voice. "
        "Characters are fictionalized."
    )


@dataclass(frozen=True)
class RadioCutResult:
    spoken_duration_sec: float
    output_path: Path
    command: list[str]
    warning: str | None


def narration_wav_path(narration_dir: Path, shot_id: str) -> Path:
    return narration_dir / f"shot_{shot_id}.wav"


def build_ffmpeg_radio_command(
    concat_list: Path,
    output_path: Path,
    *,
    title: str,
    voice: str,
    ffmpeg: str = "ffmpeg",
) -> list[str]:
    """Black 9:16 picture, narration audio, and an AI-disclosure comment."""
    color = f"color=c=black:s={RADIO_WIDTH}x{RADIO_HEIGHT}:r={RADIO_FRAME_RATE}"
    return [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        color,
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list),
        "-shortest",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-metadata",
        f"comment={disclosure_comment(voice)}",
        "-metadata",
        f"title={title}",
        str(output_path),
    ]


def render_radio_cut(
    *,
    shots: list[dict],
    narration_dir: Path,
    output_path: Path,
    title: str,
    voice: str,
    minimum_sec: float,
    maximum_sec: float,
    work_dir: Path,
    runner=None,
    ffmpeg: str | None = None,
) -> RadioCutResult:
    """Combine every shot WAV. Missing audio or a missing FFmpeg binary is an error."""
    wavs = [narration_wav_path(narration_dir, shot["id"]) for shot in shots]
    missing = [path.name for path in wavs if not path.is_file()]
    if missing:
        names = ", ".join(missing)
        raise PipelineError(
            f"Radio cut needs every narration file. Missing: {names}. "
            "Generate them with: python -m pipeline run --stage narration"
        )

    total = sum(wav_duration_seconds(path) for path in wavs)
    binary = find_ffmpeg() if ffmpeg is None else ffmpeg
    if not binary:
        raise MissingFFmpegError(total)

    work_dir.mkdir(parents=True, exist_ok=True)
    concat_list = work_dir / "radio_cut_concat.txt"
    lines = [f"file '{_concat_path(path)}'" for path in wavs]
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_radio_command(
        concat_list, output_path, title=title, voice=voice, ffmpeg=binary
    )
    execute = runner or _run_ffmpeg
    execute(command)
    if runner is None and not output_path.is_file():
        raise PipelineError("FFmpeg finished without writing the radio cut.")
    return RadioCutResult(
        spoken_duration_sec=total,
        output_path=output_path,
        command=command,
        warning=duration_warning(total, minimum_sec, maximum_sec),
    )


def _run_ffmpeg(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "FFmpeg failed.").strip()
        tail = detail[-1200:]
        raise PipelineError(f"FFmpeg failed while building the radio cut.\n{tail}")


def _concat_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", r"'\''")
