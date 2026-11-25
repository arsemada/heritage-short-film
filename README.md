# Heritage Short Film

An Amharic short film about a childhood memory, and the Python pipeline that rebuilds it from `storyboard.json`.

The narration is approved and lives in `STORY.md`. The pipeline does not rewrite it. Characters are fictionalized. See `ETHICS.md`.

`pipeline/` is a generic engine. Another film can replace `storyboard.json` and use the same commands. This repository ships one storyboard, set in an everyday urban Ethiopian neighbourhood.

This repository currently implements validation, caching, structured logs, and the narration stage. No provider has been called yet. Image, video, and music stages are not in the code yet.

## What you can run

From the repository root, with Python 3.11:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and set `GEMINI_API_KEY`. Leave the Cloudflare values empty until the image stage exists.

```powershell
python -m pipeline validate
python -m pipeline run --stage narration
python -m pipeline run --stage narration --scene 01
python -m pipeline radio-cut
```

Use `python`, not `py`. On this machine the `py` launcher points at a Python install that is not there.

`validate` is offline. It checks `storyboard.json` against `schema/storyboard.schema.json` and against structural rules: unique shot ids, known characters, and a planned runtime inside the storyboard's own duration bounds. The pipeline does not read `STORY.md`. The shipped film's exact Amharic is checked by `pytest`, which compares `storyboard.json` with `STORY.md`.

`run --stage narration` calls the TTS provider named by `TTS_PROVIDER` (default `gemini`, model `gemini-3.8-flash-tts`). This film's storyboard sets the prebuilt voice `Kore`. The command writes `outputs/narration/shot_01.wav` through `shot_10.wav`. A second run skips shots whose text, voice, style, model, and seed have not changed. `--scene 01` regenerates only that shot. If the measured speech is outside the storyboard's target duration, the command warns you and leaves the narration text unchanged.

`radio-cut` needs those WAV files and FFmpeg on `PATH`. It builds `outputs/radio_cut.mp4`: a black 9:16 frame with the narration, and prints the spoken duration. FFmpeg is not installed yet. Install it, then open a new terminal so `PATH` refreshes, and run the command again.

## Layout

| Path | Role |
| --- | --- |
| `storyboard.json` | Source of truth for shots, narration, prompts, and seeds |
| `schema/storyboard.schema.json` | JSON Schema, Draft 2020-12 |
| `pipeline/` | Generic command line, validation, cache, logs, narration, and radio cut. It does not contain this film's story. |
| `outputs/` | Generated media and the cache manifest. Gitignored |
| `logs/runs.jsonl` | One JSON record per stage event. Secrets are redacted. Not gitignored |
| `tests/` | Offline tests with a fake TTS provider |

## Tests

```powershell
python -m pytest
```

The tests do not call Gemini, Cloudflare, or FFmpeg.

## Limits

- Narration code is ready. It has not been run against the API, so there is no speech to review yet.
- Wan 2.2 and ACE-Step are not wired in. The film's picture and music come in later slices.
- Planned shot timing adds up to 82 seconds including a 5-second end card. That is a plan, not a measurement of the voice.
