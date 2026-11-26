"""Wan 2.2 TI2V-5B image-to-video on a Kaggle T4.

Run from the project root, with a GPU notebook and internet enabled:

    python notebooks/kaggle_wan2_batch.py

Keyframes are read from ./keyframes/shot_XX.jpg (or .png), then from
outputs/keyframes/. Each shot uses only that shot's motion_prompt and seed.
One failed shot is logged and skipped. Clips land in
./kaggle_outputs/shots/shot_XX.mp4. The local shots stage loops a shorter
clip, or trims a longer clip at normal speed, to the narration.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

MODEL_ID = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
WIDTH = 832
HEIGHT = 480
NUM_FRAMES = 49
FPS = 24
STEPS = 25
GUIDANCE = 5.0
NEGATIVE = "text, subtitles, watermark, extra fingers, distorted hands, cartoon, anime, static frame"


def project_root() -> Path:
    here = Path.cwd()
    if (here / "storyboard.json").is_file():
        return here
    parent = Path(__file__).resolve().parents[1]
    if (parent / "storyboard.json").is_file():
        return parent
    raise SystemExit("storyboard.json was not found in the working directory or the repository root.")


def ensure_packages() -> None:
    try:
        import diffusers  # noqa: F401
        import imageio  # noqa: F401
        import torch  # noqa: F401
    except ImportError:
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "diffusers",
                "transformers",
                "accelerate",
                "imageio[ffmpeg]",
                "sentencepiece",
                "ftfy",
                "protobuf",
            ]
        )


def find_keyframe(root: Path, shot_id: str) -> Path | None:
    names = [f"shot_{shot_id}.jpg", f"shot_{shot_id}.png", f"shot_{shot_id}.jpeg"]
    for folder in (root / "keyframes", root / "outputs" / "keyframes"):
        for name in names:
            path = folder / name
            if path.is_file():
                return path
    return None


def fit_frame(image, width: int, height: int):
    """Cover-fit to 832x480 without stretching. Both edges stay divisible by 16."""
    from PIL import Image

    image = image.convert("RGB")
    scale = max(width / image.width, height / image.height)
    resized = image.resize(
        (max(width, round(image.width * scale)), max(height, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    left = max((resized.width - width) // 2, 0)
    top = max((resized.height - height) // 2, 0)
    return resized.crop((left, top, left + width, top + height))


def write_mp4(frames, path: Path, fps: int) -> None:
    import imageio.v2 as imageio
    import numpy as np
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(
        path,
        fps=fps,
        codec="libx264",
        quality=8,
        macro_block_size=1,
        ffmpeg_params=["-pix_fmt", "yuv420p"],
    )
    try:
        for frame in frames:
            if isinstance(frame, Image.Image):
                array = np.asarray(frame.convert("RGB"))
            else:
                array = np.asarray(frame)
                if array.dtype != np.uint8:
                    array = (np.clip(array, 0, 1) * 255).astype(np.uint8)
            writer.append_data(array)
    finally:
        writer.close()


def log_call(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def load_pipe():
    import torch
    from diffusers import AutoencoderKLWan, WanImageToVideoPipeline

    major, _minor = torch.cuda.get_device_capability()
    dtype = torch.bfloat16 if major >= 8 else torch.float16
    print(f"Loading {MODEL_ID} in {dtype} on {torch.cuda.get_device_name(0)}", flush=True)
    vae = AutoencoderKLWan.from_pretrained(MODEL_ID, subfolder="vae", torch_dtype=torch.float32)
    pipe = WanImageToVideoPipeline.from_pretrained(MODEL_ID, vae=vae, torch_dtype=dtype)
    # A 16 GB T4 OOMs if UMT5 and the 5B transformer sit on the GPU together.
    # Sequential offload keeps one block resident. Newer GPUs can use model offload.
    if major < 8:
        pipe.enable_sequential_cpu_offload()
    else:
        pipe.enable_model_cpu_offload()
    if hasattr(pipe, "vae"):
        if hasattr(pipe.vae, "enable_tiling"):
            pipe.vae.enable_tiling()
        if hasattr(pipe.vae, "enable_slicing"):
            pipe.vae.enable_slicing()
    return pipe


def main() -> int:
    ensure_packages()
    import torch

    if not torch.cuda.is_available():
        raise SystemExit("This script needs a CUDA GPU. On Kaggle, set the accelerator to GPU T4.")

    root = project_root()
    storyboard = json.loads((root / "storyboard.json").read_text(encoding="utf-8"))
    out_dir = root / "kaggle_outputs" / "shots"
    log_path = root / "kaggle_outputs" / "kaggle_wan_runs.jsonl"
    pipe = load_pipe()
    failures = 0

    for shot in storyboard["shots"]:
        shot_id = str(shot["id"])
        destination = out_dir / f"shot_{shot_id}.mp4"
        seed = int(shot["seed"])
        started = time.perf_counter()
        record = {
            "shot_id": shot_id,
            "model": MODEL_ID,
            "seed": seed,
            "latency_sec": 0.0,
            "gpu_minutes": 0.0,
            "status": "error",
            "error": None,
        }
        try:
            keyframe = find_keyframe(root, shot_id)
            if keyframe is None:
                raise FileNotFoundError(
                    f"No keyframe for shot {shot_id} in ./keyframes or outputs/keyframes."
                )
            from PIL import Image

            image = fit_frame(Image.open(keyframe), WIDTH, HEIGHT)
            generator = torch.Generator(device="cpu")
            generator.manual_seed(seed)
            result = pipe(
                image=image,
                prompt=str(shot["motion_prompt"]),
                negative_prompt=NEGATIVE,
                height=HEIGHT,
                width=WIDTH,
                num_frames=NUM_FRAMES,
                num_inference_steps=STEPS,
                guidance_scale=GUIDANCE,
                generator=generator,
            )
            write_mp4(result.frames[0], destination, FPS)
            record["status"] = "success"
            print(f"shot {shot_id} wrote {destination}", flush=True)
        except Exception as exc:
            failures += 1
            record["error"] = f"{type(exc).__name__}: {exc}"
            print(f"shot {shot_id} failed: {record['error']}", flush=True)
            traceback.print_exc()
        finally:
            elapsed = time.perf_counter() - started
            record["latency_sec"] = round(elapsed, 3)
            record["gpu_minutes"] = round(elapsed / 60.0, 4)
            log_call(log_path, record)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    print(f"Finished. Failures: {failures}. Log: {log_path}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        import torch  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "torch"])
    raise SystemExit(main())
