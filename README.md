# Heritage Short Film

የሚጠብቅ ጎረቤት (The Neighbour Who Protects) is a short Amharic film about one childhood memory. A boy in an everyday urban Ethiopian neighbourhood drink house (tella bet) copies a customer's cigarette, coughs, and is stopped by neighbours who tell his mother. He never tries again. The film ends on the proverb ሳይቃጠል በቅጠል።

I built it as a storyboard-driven pipeline. `storyboard.json` is the production contract: ten shots, the approved Amharic, the English subtitles, the prompts, the seeds, the 90 BPM music brief, and the AI disclosure card. The approved words also live in `STORY.md`. The pipeline does not read that file at runtime, and it does not rewrite the narration. Characters are fictionalized. No family photograph and no cloned voice are in this repository. See `ETHICS.md` and `DESIGN.md`.

The same square picture is padded, not cropped, into two films:

- `outputs/final_9x16.mp4` — 1080×1920, for a phone
- `outputs/final_16x9.mp4` — 1920×1080, for a desktop or YouTube

Both are 81.50 seconds: 78.50 seconds of Amharic speech plus a 3-second card that says the film was made with AI. English subtitles are burned in. The score under the voice is `outputs/music/score.wav`, a quiet original instrumental. The storyboard sets that underscore at 90 BPM, in D major, with no vocals.

## What I contributed

`pipeline/` is a generic engine. Another film can replace `storyboard.json` and use the same commands. For this film I implemented and ran the whole path below.

- **Story contract.** JSON Schema validation, structural checks, and tests that the ten Amharic lines and the proverb still match `STORY.md`. The style instruction is a separate field, so directing the voice does not edit the approved words.
- **Narration.** Gemini `gemini-3.8-flash-tts`, prebuilt voice Kore. Visible retries on HTTP 429. SHA-256 fingerprints so a finished WAV is not requested again. `--scene 04` regenerates one shot.
- **Keyframes.** Character descriptions copied verbatim into each prompt. This storyboard uses Cloudflare FLUX.2 [klein] 4B, with a generated brother reference on the shots that include him. The storyboard seed stays in the cache key and is not sent to Cloudflare.
- **Two finished films.** FFmpeg assembly pads the square into 9:16 and 16:9, burns English captions at the real frame size, ducks the score under the voice, normalizes to −14 LUFS, and appends the disclosure card.
- **Motion after Wan.** This machine has no CUDA GPU, and the Kaggle T4 session did not leave a Wan clip. The delivered pictures are ten MiniMax H3 Turbo clips I generated in Raphael and placed at `outputs/shots/shot_01.mp4` through `shot_10.mp4`. Ken Burns from the keyframes is the offline fallback, so `python -m pipeline run` can still rebuild a picture with no GPU.
- **Picture locked to the voice.** Each Raphael clip is a little longer than its line. Assembly trims the tail at normal speed so the shot ends with the narration. An earlier cut that looped short clips was rejected because the motion repeated.
- **Provenance and cost.** `logs/runs.jsonl` records models, seeds, and measured durations, with API keys redacted. Every step recorded in this repository is $0.00. See `docs/COSTS.md`.

## How the pipeline implements it

Five production steps. Four of them are CLI stages. Music is a file, not a `--stage` flag.

| Step | Command | What it writes | Network |
| --- | --- | --- | --- |
| 1. Narration | `python -m pipeline run --stage narration` | `outputs/narration/shot_01.wav`–`shot_10.wav`. Gemini `gemini-3.8-flash-tts`, voice Kore. | Only on a cache miss |
| 2. Keyframes | `python -m pipeline run --stage keyframes` | `outputs/keyframes/shot_01.jpg`–`shot_10.jpg`. FLUX.2 [klein] 4B for this storyboard. | Only on a cache miss |
| 3. Shots | `python -m pipeline run --stage shots` | `outputs/shots/shot_01.mp4`–`shot_10.mp4`. An external clip if one is already in `wan/` or `kaggle_outputs/`. Otherwise FFmpeg Ken Burns from the keyframe. | No |
| 4. Music | Place `outputs/music/score.wav`. There is no music command. | Assembly ducks that file. A missing file becomes a quiet local drone. | No |
| 5. Assemble | `python -m pipeline run --stage assemble` | Both final MP4s, plus `outputs/subtitles/film.srt`. | No |

```powershell
python -m pipeline run
```

With no `--stage`, that command runs steps 3 and 5 only. It does not call Gemini or Cloudflare.

## Where to read each part of the brief

| Part of the brief | Where the evidence is |
| --- | --- |
| Software engineering and reproducibility | `pipeline/`, `tests/`, and `schema/storyboard.schema.json`. `python -m pipeline validate` checks the contract. `python -m pytest` stays offline. SHA-256 fingerprints in `outputs/cache/manifest.json` skip unchanged shots. `--scene 04` rebuilds one shot. `python -m pipeline run` rebuilds pictures and both films from files on disk, with no Gemini or Cloudflare call. `.env.example` has empty values. `.env` is gitignored. |
| Documentation | This file, `docs/ARCHITECTURE.md`, `docs/REPORT.md`, and `REPORT.pdf`. |
| Design thinking and audience | `DESIGN.md`. The audience is urban Ethiopian families and young adults, on a phone (9:16) and on a desktop (16:9). The square is padded so people are not cropped. English captions are burned in. Three listeners heard the 86.58-second radio cut and called the pace right. Their notes changed the voice style. A three-person watch of the finished pictures is not recorded yet. |
| Experimentation and iteration | `docs/EXPERIMENTS.md`. Narration was restyled from 86.58 seconds to 78.50. Keyframes were regenerated only when the prompt changed. Short looped clips were rejected. The score brief moved from 72 BPM to the 90 BPM file that is mixed. |
| Troubleshooting and persistence | `docs/FAILURES.md`. Gemini HTTP 429, FFmpeg missing from an old terminal, no local CUDA GPU, the Kaggle T4 `ftfy` error and 14.56 GiB out-of-memory, the `Draft Session Error`, the `loudnorm` filter conflict, and the picture running ahead of the Amharic. |
| Measurement | Durations in the table later in this file, probed with ffprobe on 26 November 2026. The same numbers are in `logs/runs.jsonl`. Cost is `docs/COSTS.md`: $0.00 recorded. |
| Consent, labelling, and licences | `ETHICS.md`. No family photograph and no cloned voice are in git. The film ends on a card that names Gemini voice Kore and Cloudflare Workers AI, and says the characters are fictionalized. The same disclosure is in the MP4 comment. The moving-clip model is in `logs/runs.jsonl`. |

## Setup

Python 3.11. On this PC, `python` is 3.11.9. The `py` launcher points at a missing Python 3.13, so use `python`.

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

Check the storyboard, then build:

```powershell
python -m pipeline validate
python -m pipeline run
```

`validate` checks `storyboard.json` against `schema/storyboard.schema.json`. This storyboard plans 80.0 seconds, including the 3-second end card. Assembly follows the measured speech, so the films are 81.50 seconds.

## Why Wan is not the motion in these films

The first motion plan was Wan 2.2 image-to-video, `Wan-AI/Wan2.2-TI2V-5B-Diffusers`, in `notebooks/kaggle_wan2_batch.py`. I did not ship Wan clips, for three reasons that are written up in `docs/FAILURES.md`.

1. **No local GPU.** Running that script on this PC installs the libraries and then stops: `This script needs a CUDA GPU.` The 5B model never loads here.
2. **The Kaggle T4 ran out of memory.** The session hit a missing `ftfy` import, then a CUDA out-of-memory error with 14.56 GiB allocated on a 14.56 GiB Tesla T4 while the 5B transformer and the UMT5 text encoder were loaded together. The script now calls `enable_sequential_cpu_offload()` and `vae.enable_tiling()`.
3. **The session still did not finish the film.** After that change, the session record is a checkpoint download and reconstruction of about 31.4 GB, about 5.5 minutes per shot, and a Kaggle `Draft Session Error`. No Wan MP4 is in this repository.

I generated the ten moving shots in Raphael with MiniMax H3 Turbo and placed them at `outputs/shots/shot_01.mp4` through `shot_10.mp4`. ffprobe measures them as HEVC, 720×720, from 5.97 to 12.00 seconds. The pipeline does not call Raphael. The recorded cost stays $0.00.

Ken Burns stays in the shots stage so a reviewer can still rebuild a picture from the keyframes alone, with FFmpeg and no GPU. On a machine that has the WAVs and keyframes, and no external clip in `outputs/shots/wan/` or `kaggle_outputs/shots/`, `python -m pipeline run` writes Ken Burns and then both films.

Rebuilding the delivered Raphael cut, without replacing those files, is:

```powershell
python -m pipeline run --stage assemble
```

A shots-stage cache miss writes Ken Burns over `outputs/shots/shot_XX.mp4`. The external source the shots stage reads, and does not overwrite, is `outputs/shots/wan/shot_XX.mp4` or `kaggle_outputs/shots/shot_XX.mp4`.

## Duration and loudness

Narration lines are 5.19 to 11.25 seconds. The Raphael clips are a little longer than those lines. `build_shot_command` in `pipeline/shots.py` plays a longer clip at normal speed and cuts the extra tail with `-t`. Assembly calls that command for every shot into `outputs/assemble/timed/` before the concat, so the picture ends with the line. A clip shorter than its line is looped instead. An earlier cut did that with clips of about 3.75 seconds, and the repeated motion was rejected. `setpts` slowing was removed. It is not the shipped alignment.

The score is ducked under the voice inside one FFmpeg complex graph. Both streams are resampled to 24 kHz mono, the score is set to volume 0.35, `sidechaincompress` ducks it against the narration, and `loudnorm=I=-14:TP=-1.5:LRA=11` runs on the mixed pad. `loudnorm` is not a separate `-af`. Putting it there made FFmpeg refuse the file with `Error opening output files: Invalid argument`.

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
| Shots | Ten HEVC clips, 720×720. 5.97, 11.01, 6.01, 8.01, 7.01, 6.01, 7.01, 10.01, 10.01, 12.00 seconds. MiniMax H3 Turbo via Raphael. No model tag inside the files. |
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
