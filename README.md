# Heritage Short Film

An Amharic short film about a childhood memory, rebuilt from `storyboard.json`.

The narration is approved and lives in `STORY.md`. The pipeline does not rewrite it. Characters are fictionalized. See `ETHICS.md` and `DESIGN.md`.

`pipeline/` is a generic engine. Another film can replace `storyboard.json` and use the same commands. This repository ships one storyboard, set in an everyday urban Ethiopian neighbourhood drink house (tella bet).

## Setup

From the repository root, with Python 3.11:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set `GEMINI_API_KEY` before narration. Set `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` before keyframes. Use `python`, not `py`. The `py` launcher on this machine points at a missing Python 3.13.

`.env.example` lists the variable names and leaves the values empty. Do not commit `.env`.

FFmpeg is required for shots and assembly. This machine uses the Gyan.FFmpeg 9.1 WinGet build. `pipeline/ffmpeg_lookup.py` checks `PATH`, then the WinGet Links shim. If a terminal was opened before FFmpeg was installed, open a new one.

## Build the films

When the narration WAVs, keyframes, shot masters, and `outputs/music/score.wav` are already on disk:

```powershell
python -m pipeline validate
python -m pipeline run
```

`python -m pipeline validate` checks `storyboard.json` against `schema/storyboard.schema.json`. It prints the shot count and the planned runtime, including the 3-second end card.

`python -m pipeline run` with no `--stage` conforms the ten shots, then assembles both films. It does not call Gemini or Cloudflare. There is no `--stage music`. The score is a file. Assembly uses `outputs/music/score.wav` when that file is present.

```powershell
python -m pipeline run --stage narration
python -m pipeline run --stage narration --scene 01
python -m pipeline run --stage keyframes
python -m pipeline run --stage shots
python -m pipeline run --stage assemble
python -m pipeline radio-cut
```

`--scene 01` limits a stage to shot 01. Omit `--scene` to process every shot. A shot runs again only when its SHA-256 fingerprint misses and the output file is missing or empty. Unchanged shots stay cached.

The narration fingerprint includes the Amharic line, the style instruction, the voice, the model, and the seed. The keyframe fingerprint includes the composed prompt, the model, the step count, and, when the brother reference is attached, the PNG hash. Changing only one shot's prompt or seed misses only that shot.

`run --stage shots` looks for an external clip at `outputs/shots/wan/shot_XX.mp4`, then at `kaggle_outputs/shots/shot_XX.mp4`. A shorter clip is looped to the WAV. A longer clip is trimmed at normal speed with `-t`. The source file is not overwritten. If neither clip exists, FFmpeg Ken Burns writes `outputs/shots/shot_XX.mp4` from the keyframe. A cache hit does not rewrite that MP4. The cache checks that the file exists. It does not re-hash a file you replaced by hand. A later cache miss on this stage would replace `outputs/shots/shot_XX.mp4` with Ken Burns.

`run --stage assemble` reads the masters already at `outputs/shots/shot_XX.mp4`, trims or loops each one to its WAV, burns the English captions, ducks `outputs/music/score.wav` under the voice, normalizes to −14 LUFS, adds the 3-second AI disclosure card, and writes `outputs/final_9x16.mp4` and `outputs/final_16x9.mp4`. Rebuilding the current films after a clip is replaced is `python -m pipeline run --stage assemble`.

## Repository structure

| Path | Role |
| --- | --- |
| `storyboard.json` | Shots, narration, prompts, seeds, music brief, and the end card |
| `STORY.md` | Approved narration. The pipeline does not read it at runtime. Tests compare the storyboard with it. |
| `schema/storyboard.schema.json` | JSON Schema, Draft 2020-12 |
| `pipeline/` | Validation, cache, logs, narration, keyframes, shots, music, and assembly. It does not contain this film's story. |
| `notebooks/` | Optional Kaggle GPU scripts for Wan 2.2 and ACE-Step. They are not part of `python -m pipeline run`. |
| `outputs/` | Generated media and the cache manifest. Gitignored |
| `logs/runs.jsonl` | One JSON record per stage event. Secrets are redacted. Tracked |
| `docs/` | Architecture, experiments, failures, costs, and the report |
| `DESIGN.md`, `ETHICS.md` | Creative direction, the recorded listen, and consent rules |
| `tests/` | Offline tests with fake providers |
| `.env.example` | Variable names only |

## Tests

```powershell
python -m pytest
```

The tests do not call Gemini, Cloudflare, or FFmpeg.

## What is on disk for this film

Probed 26 November 2026.

- Narration: ten WAVs, 24 kHz mono, 78.50 seconds of speech, voice Kore.
- Keyframes: ten 1024×1024 JPEGs from Cloudflare FLUX.2 [klein] 4B, plus `outputs/references/young_brother_ref.png`.
- Shots: `outputs/shots/shot_01.mp4` through `shot_10.mp4`, user-supplied Raphael clips stated as MiniMax H3 Turbo. ffprobe measures HEVC, 720×720, durations 5.97, 11.01, 6.01, 8.01, 7.01, 6.01, 7.01, 10.01, 10.01, and 12.00 seconds. Assembly trims each one to its WAV.
- Score: `outputs/music/score.wav`, 148.77 seconds, 48 kHz stereo, converted from `score.mp3`. The storyboard tempo is 90 BPM. `music.status` in the storyboard is still `not_generated`, and `music.path` is null. Assembly finds the default `score.wav` anyway.
- Films: `outputs/final_9x16.mp4` (1080×1920) and `outputs/final_16x9.mp4` (1920×1080). Both are 81.50 seconds, which is 78.50 seconds of speech plus the 3-second end card.

Planned storyboard time is 80 seconds including the end card. Assembly follows the measured speech, so the picture is longer than that plan.
