# Heritage Short Film

የሚጠብቅ ጎረቤት (The Neighbour Who Protects) is a short Amharic film built from one file, `storyboard.json`.

A boy in an everyday urban Ethiopian neighbourhood drink house (tella bet) copies a customer's cigarette, coughs, and is stopped by neighbours who tell his mother. He never tries again. The film ends on the proverb ሳይቃጠል በቅጠል። The approved words live in `STORY.md`. The pipeline does not rewrite them, and it does not read `STORY.md` at runtime. Characters are fictionalized. See `ETHICS.md` and `DESIGN.md`.

The same square picture is padded into two films:

- `outputs/final_9x16.mp4` — 1080×1920, for a phone
- `outputs/final_16x9.mp4` — 1920×1080, for a desktop or YouTube

Both are 81.50 seconds: 78.50 seconds of Amharic speech plus a 3-second card that says the film was made with AI. English subtitles are burned in. The score under the voice is `outputs/music/score.wav`. The storyboard brief for that underscore is a quiet original instrumental at 90 BPM, in D major, with no vocals. The storyboard does not name the instruments.

`pipeline/` is a generic engine. Another film can replace `storyboard.json` and use the same commands.

## How the film is made

Five production steps, in this order. Four of them are CLI stages. Music is a file, not a `--stage` flag.

| Step | Command | What it writes | Network |
| --- | --- | --- | --- |
| 1. Narration | `python -m pipeline run --stage narration` | `outputs/narration/shot_01.wav`–`shot_10.wav`. Gemini `gemini-3.8-flash-tts`, prebuilt voice Kore. | Only on a cache miss |
| 2. Keyframes | `python -m pipeline run --stage keyframes` | `outputs/keyframes/shot_01.jpg`–`shot_10.jpg`. This storyboard uses Cloudflare FLUX.2 [klein] 4B. | Only on a cache miss |
| 3. Shots | `python -m pipeline run --stage shots` | `outputs/shots/shot_01.mp4`–`shot_10.mp4`. An external clip if one is already in `wan/` or `kaggle_outputs/`. Otherwise FFmpeg Ken Burns from the keyframe. | No |
| 4. Music | Drop the file. There is no music command. | `outputs/music/score.wav`. Assembly uses it. A missing file becomes a quiet local drone. | No |
| 5. Assemble | `python -m pipeline run --stage assemble` | Both final MP4s, plus `outputs/subtitles/film.srt`. | No |

```powershell
python -m pipeline run
```

With no `--stage`, that command runs steps 3 and 5 only. It does not call Gemini or Cloudflare. On a machine with the WAVs and keyframes, and with no external clip in `outputs/shots/wan/` or `kaggle_outputs/shots/`, step 3 writes Ken Burns motion and step 5 builds both films. That is the offline path. It needs FFmpeg and no GPU.

### Why the moving pictures are not Wan

The first motion plan was Wan 2.2 image-to-video, `Wan-AI/Wan2.2-TI2V-5B-Diffusers`, in `notebooks/kaggle_wan2_batch.py`. This PC has no CUDA GPU, so that script stops before it loads the model. On a Kaggle Tesla T4 the session hit a missing `ftfy` import, then a CUDA out-of-memory error at 14.56 GiB while the 5B transformer and the UMT5 text encoder were loaded together. The script now calls `enable_sequential_cpu_offload()` and `vae.enable_tiling()`. The session record after that is about 5.5 minutes per shot, a checkpoint download and reconstruction of about 31.4 GB, and a Kaggle `Draft Session Error`. No Wan MP4 is in this repository. The full account is in `docs/FAILURES.md`.

The pictures in the delivered films are ten user-supplied Raphael clips, stated as MiniMax H3 Turbo, already at `outputs/shots/shot_01.mp4` through `shot_10.mp4`. ffprobe measures them as HEVC, 720×720, from 5.97 to 12.00 seconds. The pipeline does not call Raphael. Recorded cost for every step in this repo is $0.00. See `docs/COSTS.md`.

Ken Burns stays in the shots stage so a reviewer can still rebuild a picture from the keyframes alone. Rebuilding the delivered Raphael cut, without replacing those files, is:

```powershell
python -m pipeline run --stage assemble
```

A shots-stage cache miss writes Ken Burns over `outputs/shots/shot_XX.mp4`. The external source the shots stage is written to read, and not overwrite, is `outputs/shots/wan/shot_XX.mp4` or `kaggle_outputs/shots/shot_XX.mp4`.

## Duration and loudness

Narration lines are 5.19 to 11.25 seconds. The clips now on disk are a little longer than those lines. `build_shot_command` in `pipeline/shots.py` plays a longer clip at normal speed and cuts the extra tail with `-t`. Assembly calls that command for every shot into `outputs/assemble/timed/` before the concat, so the picture ends with the line. A clip shorter than its line is looped instead. An earlier cut did that with clips of about 3.75 seconds, and the repeated motion was rejected. `setpts` slowing was removed. It is not the shipped alignment. Tests assert that a slightly longer source has no `setpts` filter.

The score is ducked under the voice inside one FFmpeg complex graph. Both streams are resampled to 24 kHz mono, the score is set to volume 0.35, `sidechaincompress` ducks it against the narration, and `loudnorm=I=-14:TP=-1.5:LRA=11` runs on the mixed pad. `loudnorm` is not a separate `-af`. Putting it there made FFmpeg refuse the file with `Error opening output files: Invalid argument`.

## Setup

Python 3.11. On this PC, `python` is 3.11.9. The `py` launcher points at a missing Python 3.13.

PowerShell, from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

bash:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and set `GEMINI_API_KEY` before narration. Set `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` before keyframes. `.env.example` lists the names and leaves the values empty. Do not commit `.env`.

FFmpeg is required for shots and assembly. This machine uses the Gyan.FFmpeg 9.1 WinGet build. `pipeline/ffmpeg_lookup.py` checks `PATH`, then the WinGet Links shim `ffmpeg.exe`. ffprobe is taken from that same folder. If a terminal was opened before FFmpeg was installed, open a new one.

## Commands

```powershell
python -m pipeline validate
python -m pipeline run
python -m pipeline run --stage narration
python -m pipeline run --stage keyframes
python -m pipeline run --stage shots
python -m pipeline run --stage assemble
python -m pipeline radio-cut
```

`validate` checks `storyboard.json` against `schema/storyboard.schema.json` and prints the planned runtime, including the 3-second end card. This storyboard plans 80.0 seconds. Assembly follows the measured speech, so the films are 81.50 seconds.

`radio-cut` writes `outputs/radio_cut.mp4`, the narration over a black 9:16 frame. The cut the three listeners heard was the earlier 86.58-second narration.

### One shot at a time

`--scene 04` limits a stage to shot 04. Omit it to process every shot. A shot is regenerated only when its SHA-256 fingerprint misses. The other nine stay cached.

```powershell
python -m pipeline run --stage narration --scene 04
python -m pipeline run --stage keyframes --scene 04
python -m pipeline run --stage shots --scene 04
```

Edit shot 04 in `storyboard.json`, then run the stage that owns the field you changed:

| What you edit | What misses the cache |
| --- | --- |
| `narration_am`, the proverb on shot 10, the style instruction, the voice, the model, or that shot's `seed` | Narration for that shot. The style instruction is shared, so changing it misses all ten. |
| `image_prompt`, a character in `characters_present`, or that shot's `seed` | That shot's keyframe. Klein does not receive the seed. The seed only changes the cache key. |
| The keyframe file, the WAV length, `motion_prompt`, `fallback_ken_burns`, or the seed | That shot's video, the next time the shots stage runs and the fingerprint misses. |

The cache stores the fingerprint in `outputs/cache/manifest.json` and checks that the output file still exists. It does not re-hash a master you replaced by hand. Replacing `outputs/shots/shot_04.mp4` and running `python -m pipeline run --stage assemble` rebuilds both films from the new bytes. Running `run --stage shots` after that does not, until the shots fingerprint itself misses.

## Tests

```powershell
python -m pytest
```

The tests do not call Gemini, Cloudflare, or FFmpeg.

## What is on disk

Probed 26 November 2026.

| Asset | Measured |
| --- | --- |
| Narration | Ten WAVs, 24 kHz mono, voice Kore. 5.92, 10.37, 5.19, 7.74, 7.00, 5.91, 6.20, 9.06, 9.86, 11.25 seconds. Total 78.50. |
| Keyframes | Ten 1024×1024 JPEGs, FLUX.2 [klein] 4B, plus `outputs/references/young_brother_ref.png` at 480×480. |
| Shots | Ten HEVC clips, 720×720. 5.97, 11.01, 6.01, 8.01, 7.01, 6.01, 7.01, 10.01, 10.01, 12.00 seconds. Stated source: MiniMax H3 Turbo via Raphael. No model tag inside the files. |
| Score | `outputs/music/score.wav`, 148.77 seconds, 48 kHz stereo, converted from `score.mp3`. Storyboard tempo 90 BPM. `music.status` is `not_generated` and `music.path` is null. Assembly still finds the default `score.wav`. |
| Films | Both finals, 81.50 seconds. 9:16 is 14,761,993 bytes. 16:9 is 15,068,700 bytes. |

## Repository map

| Path | What it is |
| --- | --- |
| `storyboard.json` | The film: ten shots, Amharic lines, English subtitles, prompts, seeds, the 90 BPM music brief, and the end card. |
| `STORY.md` | The approved narration. Tests compare the storyboard with it. |
| `schema/storyboard.schema.json` | JSON Schema, Draft 2020-12. |
| `pipeline/` | The engine: validate, cache, log, narration, keyframes, shots, music lookup, assembly, FFmpeg lookup. No story text. |
| `notebooks/kaggle_wan2_batch.py` | Optional Wan 2.2 batch for a Kaggle GPU. Not part of `python -m pipeline run`. |
| `notebooks/kaggle_acestep.py` | Optional ACE-Step score script for a Kaggle GPU. Not part of `python -m pipeline run`. |
| `outputs/` | Generated media and `outputs/cache/manifest.json`. Gitignored. |
| `logs/runs.jsonl` | One JSON object per stage event. Secrets are redacted. This file is tracked. |
| `DESIGN.md` | Creative direction and the three-listener radio-cut notes. |
| `ETHICS.md` | Fictionalized characters, no voice cloning, the AI disclosure. |
| `docs/ARCHITECTURE.md` | What each stage hashes, and how conform, captions, and the mix work. |
| `docs/FAILURES.md` | The 429s, the missing FFmpeg, the T4 session, the loudnorm bug, and the duration fix. |
| `docs/EXPERIMENTS.md` | The runs that produced a file or a rejected file. |
| `docs/COSTS.md` | The $0.00 record. |
| `docs/REPORT.md` | The technical report. |
| `REPORT.pdf` | That report, printed. |
| `tests/` | Offline tests. |
| `.env.example` | Variable names only. |

There is no `README.md` inside `pipeline/`, `docs/`, `outputs/`, or `notebooks/`. This file is the map for those directories.

## Documentation index

Start with this file. Then `DESIGN.md` for the story and the listen, `docs/ARCHITECTURE.md` for the cache and the FFmpeg graph, `docs/FAILURES.md` for the Wan pivot, and `docs/REPORT.md` or `REPORT.pdf` for the whole account.
