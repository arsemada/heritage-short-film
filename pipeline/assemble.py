"""Join shots, narration, optional music, subtitles, and the end card.

The square master is fitted whole into 9:16 and 16:9, with black bars
where the frame is taller or wider. Loudness is normalized to -14 LUFS on
the final audio. A score, or a quiet generated underscore when no score is
on disk, is ducked under the voice with sidechaincompress.
"""

from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from pipeline.cache import AssetCache, fingerprint
from pipeline.config import Settings
from pipeline.errors import PipelineError
from pipeline.ffmpeg_lookup import find_ffmpeg
from pipeline.logger import log_event
from pipeline.music import load_score, prepare_score, score_path
from pipeline.narration import wav_duration_seconds
from pipeline.radio_cut import narration_wav_path
from pipeline.shots import MASTER_SIZE, _media_duration, build_shot_command, shot_output_path
from pipeline.validator import load_and_validate

VERTICAL = (1080, 1920)
HORIZONTAL = (1920, 1080)
LOUDNORM = "loudnorm=I=-14:TP=-1.5:LRA=11"


@dataclass(frozen=True)
class AssemblyResult:
    vertical_path: Path
    horizontal_path: Path
    subtitle_path: Path
    spoken_duration_sec: float
    music_path: Path | None
    warning: str | None


def build_srt(shots: list[dict], durations: list[float]) -> str:
    """One cue per shot. Blank lines inside a cue are removed so the SRT stays valid."""
    cursor = 0.0
    blocks: list[str] = []
    for index, (shot, duration) in enumerate(zip(shots, durations), start=1):
        start = cursor
        cursor += duration
        text = "\n".join(line.strip() for line in str(shot["subtitle_en"]).splitlines() if line.strip())
        blocks.append(f"{index}\n{_timestamp(start)} --> {_timestamp(cursor)}\n{text}\n")
    return "\n".join(blocks)


def build_mix_command(
    narration: Path,
    music: Path | None,
    output: Path,
    *,
    ffmpeg: str = "ffmpeg",
) -> list[str]:
    if music is None:
        return [
            ffmpeg,
            "-y",
            "-i",
            str(narration),
            "-af",
            LOUDNORM,
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    return [
        ffmpeg,
        "-y",
        "-i",
        str(narration),
        "-stream_loop",
        "-1",
        "-i",
        str(music),
        "-filter_complex",
        (
            "[1:a]aresample=24000,aformat=channel_layouts=mono,volume=0.35[mus];"
            "[0:a]aresample=24000,aformat=channel_layouts=mono[nar];"
            "[mus][nar]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=300[ducked];"
            "[nar][ducked]amix=inputs=2:duration=first:normalize=0[mix];"
            f"[mix]{LOUDNORM}[aout]"
        ),
        "-map",
        "[aout]",
        "-c:a",
        "pcm_s16le",
        str(output),
    ]


def build_export_command(
    picture: Path,
    audio: Path,
    subtitles: Path,
    output: Path,
    *,
    width: int,
    height: int,
    title: str,
    ffmpeg: str = "ffmpeg",
) -> list[str]:
    subtitle_arg = _subtitle_filter(subtitles)
    return [
        ffmpeg,
        "-y",
        "-i",
        str(picture),
        "-i",
        str(audio),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-vf",
        f"{_fit_frame(width, height)},{subtitle_arg}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-metadata",
        "comment=AI-generated film. Characters are fictionalized. Narration voice is a prebuilt TTS voice.",
        "-metadata",
        f"title={title}",
        str(output),
    ]


def render_film(
    settings: Settings,
    *,
    runner=None,
    ffmpeg: str | None = None,
    run_id: str | None = None,
) -> AssemblyResult:
    """Build both MP4s from cached shots and narration. Missing shots are an error."""
    storyboard = load_and_validate(settings.storyboard_path, settings.schema_path)
    binary = find_ffmpeg() if ffmpeg is None else ffmpeg
    if not binary:
        raise PipelineError("FFmpeg was not found on PATH, so the final films were not written.")
    shots = list(storyboard["shots"])
    video_paths = [shot_output_path(settings.output_dir, shot["id"]) for shot in shots]
    wav_paths = [narration_wav_path(settings.narration_dir, shot["id"]) for shot in shots]
    missing_video = [path.name for path in video_paths if not path.is_file()]
    missing_audio = [path.name for path in wav_paths if not path.is_file()]
    if missing_video or missing_audio:
        parts = []
        if missing_video:
            parts.append("shots: " + ", ".join(missing_video))
        if missing_audio:
            parts.append("narration: " + ", ".join(missing_audio))
        raise PipelineError(
            "Assembly is missing " + "; ".join(parts) + ". "
            "Run the narration and shots stages first."
        )
    durations = [wav_duration_seconds(path) for path in wav_paths]
    spoken = sum(durations)
    end_card = storyboard["end_card"]
    music, warning, underscore_command = prepare_score(
        settings,
        storyboard,
        spoken + float(end_card["duration_sec"]),
        ffmpeg=binary,
    )
    real_score = load_score(settings, storyboard)
    named_score = score_path(settings, storyboard)
    if real_score is not None and real_score.resolve() == named_score.resolve():
        music_token = _sha_name(real_score)
    else:
        music_token = "fallback-underscore-v1"
    payload = {
        "stage": "assemble",
        "videos": [_sha_name(path) for path in video_paths],
        "audio": [_sha_name(path) for path in wav_paths],
        "music": music_token,
        "end_card": end_card,
        "subtitles": [shot["subtitle_en"] for shot in shots],
        "layout": "fit-square-captions-v5-loop-to-wav",
    }
    digest = fingerprint(payload)
    vertical = settings.output_dir / "final_9x16.mp4"
    horizontal = settings.output_dir / "final_16x9.mp4"
    cache = AssetCache(settings.cache_manifest_path, settings.root)
    cached_vertical = cache.lookup("assemble:9x16", digest)
    cached_horizontal = cache.lookup("assemble:16x9", digest)
    current_run = run_id or uuid.uuid4().hex
    if cached_vertical is not None and cached_horizontal is not None:
        _log(settings, current_run, digest, True, "success", spoken, music is not None, warning)
        return AssemblyResult(
            cached_vertical,
            cached_horizontal,
            settings.output_dir / "subtitles" / "film.srt",
            spoken,
            music,
            warning,
        )

    work = settings.output_dir / "assemble"
    work.mkdir(parents=True, exist_ok=True)
    subtitle_path = settings.output_dir / "subtitles" / "film.srt"
    subtitle_path.parent.mkdir(parents=True, exist_ok=True)
    subtitle_path.write_text(build_srt(shots, durations), encoding="utf-8")
    vertical_subs = work / "film_9x16.ass"
    horizontal_subs = work / "film_16x9.ass"
    write_ass(shots, durations, vertical_subs, width=VERTICAL[0], height=VERTICAL[1])
    write_ass(shots, durations, horizontal_subs, width=HORIZONTAL[0], height=HORIZONTAL[1])
    end_text = work / "end_card.txt"
    end_text.write_text(str(end_card["text"]).replace("\r\n", "\n"), encoding="utf-8")
    end_video = work / "end_card.mp4"
    picture = work / "picture.mp4"
    narration_wav = work / "narration.wav"
    mixed = work / "mixed.wav"
    concat_list = work / "picture.txt"
    timed_dir = work / "timed"
    timed_dir.mkdir(parents=True, exist_ok=True)
    timed_paths = [timed_dir / path.name for path in video_paths]
    if underscore_command is not None:
        music.parent.mkdir(parents=True, exist_ok=True)
    commands = []
    if underscore_command is not None:
        commands.append(underscore_command)
    for source, timed, duration in zip(video_paths, timed_paths, durations, strict=True):
        commands.append(
            build_shot_command(
                image=None,
                wan=source,
                output=timed,
                duration_sec=duration,
                motion={},
                ffmpeg=binary,
                source_duration=_media_duration(source, binary),
            )
        )
    commands.extend([
        _end_card_command(end_text, end_video, float(end_card["duration_sec"]), ffmpeg=binary),
        _concat_command(_write_concat(concat_list, [*timed_paths, end_video]), picture, ffmpeg=binary),
        _narration_command(wav_paths, float(end_card["duration_sec"]), narration_wav, ffmpeg=binary),
        build_mix_command(narration_wav, music, mixed, ffmpeg=binary),
        build_export_command(
            picture, mixed, vertical_subs, vertical,
            width=VERTICAL[0], height=VERTICAL[1], title=storyboard["meta"]["title"], ffmpeg=binary,
        ),
        build_export_command(
            picture, mixed, horizontal_subs, horizontal,
            width=HORIZONTAL[0], height=HORIZONTAL[1], title=storyboard["meta"]["title"], ffmpeg=binary,
        ),
    ])
    execute = runner or _run_ffmpeg
    try:
        for command in commands:
            execute(command)
    except PipelineError as exc:
        _log(settings, current_run, digest, False, "error", spoken, music is not None, str(exc))
        raise
    if runner is None and (not vertical.is_file() or not horizontal.is_file()):
        raise PipelineError("FFmpeg finished without writing both final films.")
    cache.store("assemble:9x16", digest, vertical)
    cache.store("assemble:16x9", digest, horizontal)
    _log(settings, current_run, digest, False, "success", spoken, music is not None, warning)
    return AssemblyResult(vertical, horizontal, subtitle_path, spoken, music, warning)


def load_score_path(settings: Settings, storyboard: dict) -> Path:
    from pipeline.music import score_path

    return score_path(settings, storyboard)


def _end_card_command(text_file: Path, output: Path, duration: float, *, ffmpeg: str) -> list[str]:
    font = Path("C:/Windows/Fonts/arial.ttf")
    font_opt = f":fontfile={_filter_path(font)}" if font.is_file() else ""
    draw = (
        f"drawtext=textfile={_filter_path(text_file)}{font_opt}:"
        "fontcolor=white:fontsize=28:line_spacing=12:x=(w-text_w)/2:y=(h-text_h)/2"
    )
    return [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s={MASTER_SIZE}x{MASTER_SIZE}:r=25:d={duration:.3f}",
        "-vf",
        draw,
        "-t",
        f"{duration:.3f}",
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output),
    ]


def _concat_command(concat_list: Path, output: Path, *, ffmpeg: str) -> list[str]:
    return [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_list),
        "-c",
        "copy",
        str(output),
    ]


def _narration_command(wavs: list[Path], end_sec: float, output: Path, *, ffmpeg: str) -> list[str]:
    command = [ffmpeg, "-y"]
    for path in wavs:
        command.extend(["-i", str(path)])
    command.extend(["-f", "lavfi", "-t", f"{end_sec:.3f}", "-i", "anullsrc=r=24000:cl=mono"])
    labels = []
    filters = []
    for index in range(len(wavs) + 1):
        filters.append(f"[{index}:a]aresample=24000,aformat=channel_layouts=mono[a{index}]")
        labels.append(f"[a{index}]")
    filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=0:a=1[aout]")
    command.extend(
        ["-filter_complex", ";".join(filters), "-map", "[aout]", "-c:a", "pcm_s16le", str(output)]
    )
    return command


def _write_concat(path: Path, files: list[Path]) -> Path:
    lines = ["file '" + item.resolve().as_posix().replace("'", r"'\''") + "'" for item in files]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _filter_path(path: Path) -> str:
    """Quote a path for an FFmpeg filter. A drive-letter colon must not start a new option."""
    escaped = path.resolve().as_posix().replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    return f"'{escaped}'"


def _fit_frame(width: int, height: int) -> str:
    """Show the whole square. Bars fill the extra space instead of cutting people off."""
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
    )


def write_ass(
    shots: list[dict],
    durations: list[float],
    path: Path,
    *,
    width: int,
    height: int,
) -> str:
    """Captions in the real frame size. PlayRes stops libass scaling a 288-line script."""
    vertical = height > width
    font_size = 36 if vertical else 32
    margin_v = 120 if vertical else 22
    margin_h = 64 if vertical else 280
    events = []
    cursor = 0.0
    for shot, duration in zip(shots, durations, strict=True):
        lines = [line.strip() for line in str(shot["subtitle_en"]).splitlines() if line.strip()]
        text = r"\N".join(lines)
        start = _ass_time(cursor)
        cursor += duration
        end = _ass_time(cursor)
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
    script = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,"
        f"{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
        f"0,0,0,0,100,100,0,0,1,2,0,2,{margin_h},{margin_h},{margin_v},1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        + "\n".join(events)
        + "\n"
    )
    path.write_text(script, encoding="utf-8")
    return script


def _subtitle_filter(path: Path) -> str:
    return f"subtitles={_filter_path(path)}"


def _ass_time(seconds: float) -> str:
    centis = max(0, int(round(seconds * 100)))
    hours, centis = divmod(centis, 360_000)
    minutes, centis = divmod(centis, 6_000)
    secs, centis = divmod(centis, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def _timestamp(seconds: float) -> str:
    millis = max(0, int(round(seconds * 1000)))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _sha_name(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"{path.name}:{digest.hexdigest()}"


def _display(settings: Settings, path: Path) -> str:
    try:
        return path.resolve().relative_to(settings.root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _run_ffmpeg(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "FFmpeg failed.").strip()
        raise PipelineError(f"FFmpeg failed during assembly.\n{detail[-1200:]}")


def _log(
    settings: Settings,
    run_id: str,
    digest: str,
    cached: bool,
    status: str,
    spoken: float,
    has_music: bool,
    error: str | None,
) -> None:
    log_event(
        settings.log_path,
        {
            "run_id": run_id,
            "stage": "assemble",
            "shot_id": None,
            "model": "ffmpeg",
            "params": {
                "fingerprint": digest,
                "spoken_duration_sec": round(spoken, 3),
                "music": has_music,
                "loudness": "-14 LUFS",
            },
            "seed": None,
            "latency_sec": 0,
            "cached": cached,
            "status": status,
            "error": error if status == "error" else None,
        },
        settings.secret_values(),
    )
