"""ACE-Step 1.5 instrumental candidates on a Kaggle T4.

Run from the project root, with a GPU notebook and internet enabled:

    python notebooks/kaggle_acestep.py

The script clones ACE-Step 1.5, reads music.caption, music.tempo_bpm,
music.key, and music.seed from storyboard.json, and writes three 90-second
instrumental takes:

    ./kaggle_outputs/music/score_candidate_1.wav
    ./kaggle_outputs/music/score_candidate_2.wav
    ./kaggle_outputs/music/score_candidate_3.wav

Listen, copy the chosen take to outputs/music/score.wav, then run
``python -m pipeline run --stage assemble``. One failed seed is logged
and does not stop the other two.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

REPO_URL = "https://github.com/ACE-Step/ACE-Step-1.5.git"
DURATION = 90.0
CANDIDATES = 3


def project_root() -> Path:
    here = Path.cwd()
    if (here / "storyboard.json").is_file():
        return here
    parent = Path(__file__).resolve().parents[1]
    if (parent / "storyboard.json").is_file():
        return parent
    raise SystemExit("storyboard.json was not found in the working directory or the repository root.")


def run(command: list[str], cwd: Path | None = None) -> None:
    subprocess.check_call(command, cwd=str(cwd) if cwd is not None else None)


def ensure_repo(root: Path) -> Path:
    repo = root / "ACE-Step-1.5"
    if not (repo / "pyproject.toml").is_file() and not (repo / "setup.py").is_file():
        if repo.exists():
            shutil.rmtree(repo)
        run(["git", "clone", "--depth", "1", REPO_URL, str(repo)])
    requirements = repo / "requirements.txt"
    if requirements.is_file():
        run([sys.executable, "-m", "pip", "install", "-r", str(requirements)])
    install = run
    try:
        install([sys.executable, "-m", "pip", "install", "-e", str(repo)])
    except subprocess.CalledProcessError:
        if str(repo) not in sys.path:
            sys.path.insert(0, str(repo))
    else:
        if str(repo) not in sys.path:
            sys.path.insert(0, str(repo))
    return repo


def call_with_known_args(func, preferred: dict):
    import inspect

    allowed = set(inspect.signature(func).parameters)
    kwargs = {key: value for key, value in preferred.items() if key in allowed}
    return func(**kwargs)


def log_call(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def newest_audio(folder: Path) -> Path | None:
    files = [path for path in folder.glob("*") if path.suffix.lower() in {".wav", ".flac", ".mp3"}]
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)


def to_wav(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".wav":
        shutil.copyfile(source, destination)
        return
    run(["ffmpeg", "-y", "-i", str(source), str(destination)])


def load_handlers(repo: Path):
    from acestep.handler import AceStepHandler
    from acestep.llm_inference import LLMHandler

    dit = AceStepHandler()
    call_with_known_args(
        dit.initialize_service,
        {
            "project_root": str(repo),
            "config_path": "acestep-v15-turbo",
            "device": "cuda",
            "offload_to_cpu": True,
            "quantization": "int8_weight_only",
        },
    )
    llm = LLMHandler()
    lm_preferred = {
        "checkpoint_dir": str(repo / "checkpoints"),
        "lm_model_path": "acestep-5Hz-lm-0.6B",
        "backend": "vllm",
        "device": "cuda",
        "offload_to_cpu": True,
    }
    try:
        call_with_known_args(llm.initialize, lm_preferred)
    except Exception:
        lm_preferred["backend"] = "pt"
        call_with_known_args(llm.initialize, lm_preferred)
    return dit, llm


def main() -> int:
    import torch

    if not torch.cuda.is_available():
        raise SystemExit("This script needs a CUDA GPU. On Kaggle, set the accelerator to GPU T4.")

    root = project_root()
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    music = storyboard.get("music") or {}
    for field in ("caption", "tempo_bpm", "key", "seed"):
        if music.get(field) in (None, ""):
            raise SystemExit(f"storyboard.json music.{field} is missing.")
    caption = str(music["caption"])
    tempo = int(music["tempo_bpm"])
    key = str(music["key"])
    base_seed = int(music["seed"])

    repo = ensure_repo(root)
    dit, llm = load_handlers(repo)
    from acestep.inference import GenerationConfig, GenerationParams, generate_music

    out_dir = root / "kaggle_outputs" / "music"
    work = root / "kaggle_outputs" / "music_work"
    log_path = root / "kaggle_outputs" / "kaggle_music_runs.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)
    failures = 0

    for index in range(1, CANDIDATES + 1):
        seed = base_seed + (index - 1)
        destination = out_dir / f"score_candidate_{index}.wav"
        take_dir = work / f"candidate_{index}"
        if take_dir.exists():
            shutil.rmtree(take_dir)
        take_dir.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        record = {
            "shot_id": None,
            "candidate": index,
            "model": "ACE-Step 1.5",
            "seed": seed,
            "tempo_bpm": tempo,
            "key": key,
            "duration_sec": DURATION,
            "latency_sec": 0.0,
            "gpu_minutes": 0.0,
            "status": "error",
            "error": None,
        }
        try:
            params = GenerationParams(
                task_type="text2music",
                caption=caption,
                lyrics="[Instrumental]",
                instrumental=True,
                bpm=tempo,
                keyscale=key,
                duration=DURATION,
                seed=seed,
                inference_steps=8,
                shift=3.0,
                thinking=False,
                use_cot_caption=False,
                use_cot_metas=False,
                use_cot_lyrics=False,
            )
            config = GenerationConfig(
                batch_size=1,
                use_random_seed=False,
                seeds=[seed],
                audio_format="wav",
            )
            result = generate_music(dit, llm, params, config, save_dir=str(take_dir))
            if not getattr(result, "success", False):
                raise RuntimeError(getattr(result, "error", None) or "ACE-Step returned success=False")
            audios = list(getattr(result, "audios", []) or [])
            source = Path(audios[0]["path"]) if audios else newest_audio(take_dir)
            if source is None or not source.is_file():
                raise RuntimeError(f"ACE-Step wrote no audio in {take_dir}")
            to_wav(source, destination)
            record["status"] = "success"
            print(f"candidate {index} seed {seed} wrote {destination}", flush=True)
        except Exception as exc:
            failures += 1
            record["error"] = f"{type(exc).__name__}: {exc}"
            print(f"candidate {index} seed {seed} failed: {record['error']}", flush=True)
            traceback.print_exc()
        finally:
            elapsed = time.perf_counter() - started
            record["latency_sec"] = round(elapsed, 3)
            record["gpu_minutes"] = round(elapsed / 60.0, 4)
            log_call(log_path, record)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    print(f"Finished. Failures: {failures}. Log: {log_path}", flush=True)
    print("Copy the chosen take to outputs/music/score.wav, then run assemble.", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        import torch  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "torch"])
    raise SystemExit(main())
