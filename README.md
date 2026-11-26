# Heritage Short Film

An Amharic short film about a childhood memory, rebuilt from `storyboard.json`.

The narration is approved and lives in `STORY.md`. The pipeline does not rewrite it. Characters are fictionalized. See `ETHICS.md`.

`pipeline/` is a generic engine. Another film can replace `storyboard.json` and use the same commands. This repository ships one storyboard, set in an everyday urban Ethiopian neighbourhood drink house.

## Setup

From the repository root, with Python 3.11:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set `GEMINI_API_KEY` before narration. Set `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` before keyframes. Use `python`, not `py`.

FFmpeg 9.1 is required for shots and assembly. If a terminal was opened before FFmpeg was installed, open a new one. The pipeline also checks the WinGet Links shim.

## Build the films

When the narration WAVs, keyframes, and `outputs/music/score.wav` are already on disk:

```powershell
python -m pipeline validate
python -m pipeline run
```

`python -m pipeline run` conforms the ten shots and writes both films. It does not call Gemini or Cloudflare.

```powershell
python -m pipeline run --stage narration
python -m pipeline run --stage narration --scene 01
python -m pipeline run --stage keyframes
python -m pipeline run --stage shots
python -m pipeline run --stage assemble
python -m pipeline radio-cut
```

`--scene 01` regenerates only shot 01, and only when that shot's SHA-256 fingerprint misses. Unchanged shots stay cached. The fingerprint for speech includes the Amharic line, the style instruction, the voice, the model, and the seed. The fingerprint for a shot video includes the source image or clip, the WAV duration, the motion fields, and the seed.

`run --stage shots` uses `outputs/shots/wan/shot_XX.mp4` or `kaggle_outputs/shots/shot_XX.mp4` when that file is present, and loops or slow-trims it to the WAV. Otherwise it writes FFmpeg Ken Burns motion to `outputs/shots/shot_XX.mp4`. A cache hit does not rewrite the MP4. The source clip in `wan/` is never overwritten.

`run --stage assemble` writes `outputs/subtitles/film.srt`, burns the English captions, ducks `outputs/music/score.wav` under the voice, normalizes to -14 LUFS, adds the 3-second AI disclosure card, and writes `outputs/final_9x16.mp4` and `outputs/final_16x9.mp4`.

## Layout

| Path | Role |
| --- | --- |
| `storyboard.json` | Source of truth for shots, narration, prompts, seeds, and the score brief |
| `schema/storyboard.schema.json` | JSON Schema, Draft 2020-12 |
| `pipeline/` | Validation, cache, logs, narration, keyframes, shots, music, and assembly. It does not contain this film's story. |
| `notebooks/` | Optional Kaggle GPU scripts for Wan 2.2 and ACE-Step. They are not part of `python -m pipeline run`. |
| `outputs/` | Generated media and the cache manifest. Gitignored |
| `logs/runs.jsonl` | One JSON record per stage event. Secrets are redacted. Not gitignored |
| `docs/` | Architecture, experiments, failures, costs, and the report |
| `tests/` | Offline tests with fake providers |

## Tests

```powershell
python -m pytest
```

The tests do not call Gemini, Cloudflare, or FFmpeg.

## What is on disk for this film

- Narration: ten WAVs, 78.50 seconds of speech, voice Kore.
- Keyframes: ten JPEGs from Cloudflare FLUX.2 Klein 4B, plus `outputs/references/young_brother_ref.png`.
- Shots: ten 1080×1080 Ken Burns masters matched to those WAVs.
- Score: `outputs/music/score.wav`, converted from `score.mp3`. Storyboard tempo is 90 BPM.
- Films: `outputs/final_9x16.mp4` and `outputs/final_16x9.mp4`.

Planned storyboard time is 80 seconds including the 3-second end card. Assembly follows the measured speech, so the picture is 78.50 seconds plus the card.
