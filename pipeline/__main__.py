"""Command line for validation and each production stage.

Run these from the repository root:

    python -m pipeline validate
    python -m pipeline run
    python -m pipeline run --stage narration
    python -m pipeline run --stage narration --scene 01
    python -m pipeline run --stage keyframes
    python -m pipeline run --stage shots
    python -m pipeline run --stage assemble
    python -m pipeline radio-cut
"""

from __future__ import annotations

import argparse
import sys

from pipeline.config import load_settings
from pipeline.errors import MissingFFmpegError, PipelineError
from pipeline.assemble import render_film
from pipeline.keyframes import run_keyframes
from pipeline.orchestrator import planned_seconds, run_narration, run_radio_cut, validate_project
from pipeline.shots import run_shots


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline",
        description="Storyboard production pipeline. The film itself lives in storyboard.json.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("validate", help="Check storyboard.json against the schema and structural rules.")

    run = commands.add_parser(
        "run",
        help="Build the films from assets on disk, or run one stage.",
    )
    run.add_argument(
        "--stage",
        default=None,
        choices=["narration", "keyframes", "shots", "assemble"],
        help="Stage to run. Omit it to conform shots and assemble both films. That path does not call Gemini or Cloudflare.",
    )
    run.add_argument(
        "--scene",
        default=None,
        help="Shot id to generate, for example 01. Omit this to process every shot.",
    )

    commands.add_parser(
        "radio-cut",
        help="Stitch narration WAVs over a black 9:16 frame into outputs/radio_cut.mp4.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _prefer_utf8_stdio()
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings()
        if args.command == "validate":
            return _validate(settings)
        if args.command == "run":
            if args.stage is None:
                _shots(settings, args.scene)
                return _assemble(settings)
            return _run(settings, args.stage, args.scene)
        if args.command == "radio-cut":
            return _radio(settings)
    except PipelineError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Error: unknown command {args.command}", file=sys.stderr)
    return 2


def _validate(settings) -> int:
    storyboard = validate_project(settings)
    total = planned_seconds(storyboard)
    print(
        f"Storyboard is valid: {len(storyboard['shots'])} shots, "
        f"planned runtime {total:.1f} seconds including the end card."
    )
    return 0


def _run(settings, stage: str, scene: str | None) -> int:
    if stage == "keyframes":
        return _keyframes(settings, scene)
    if stage == "shots":
        return _shots(settings, scene)
    if stage == "assemble":
        return _assemble(settings)
    if stage != "narration":
        raise PipelineError(f"Stage '{stage}' is not implemented yet.")
    report = run_narration(settings, scene=scene)
    print(f"Spoken narration in this run: {report.total_duration_sec:.2f} seconds")
    if report.warning:
        print(f"WARNING: {report.warning}", file=sys.stderr)
    return 0


def _keyframes(settings, scene: str | None) -> int:
    for shot in run_keyframes(settings, scene=scene):
        state = "cached" if shot.cached else "generated"
        print(f"shot {shot.shot_id}  {state}  {shot.path}")
    return 0


def _shots(settings, scene: str | None) -> int:
    for shot in run_shots(settings, scene=scene):
        state = "cached" if shot.cached else shot.source
        print(f"shot {shot.shot_id}  {state}  {shot.path}  ({shot.duration_sec:.2f}s)")
    return 0


def _assemble(settings) -> int:
    result = render_film(settings)
    print(f"Spoken narration: {result.spoken_duration_sec:.2f} seconds")
    if result.warning:
        print(f"WARNING: {result.warning}", file=sys.stderr)
    print(f"Wrote {result.subtitle_path}")
    print(f"Wrote {result.vertical_path}")
    print(f"Wrote {result.horizontal_path}")
    return 0


def _radio(settings) -> int:
    try:
        result = run_radio_cut(settings)
    except MissingFFmpegError as exc:
        print(f"Radio cut spoken duration: {exc.spoken_duration_sec:.2f} seconds")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Radio cut spoken duration: {result.spoken_duration_sec:.2f} seconds")
    if result.warning:
        print(f"WARNING: {result.warning}", file=sys.stderr)
    print(f"Wrote {result.output_path}")
    return 0


def _prefer_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            continue


if __name__ == "__main__":
    raise SystemExit(main())
