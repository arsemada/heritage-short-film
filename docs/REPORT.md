# The Neighbour Who Protects

Technical report, 26 November 2026.

The film is an approved Amharic childhood memory. The pipeline reads `storyboard.json` and does not read `STORY.md` at runtime. A test checks that the ten narration lines and the proverb still match `STORY.md`. No names, dialogue, or extra events were added. Characters are fictionalized. The younger brother is not a photograph of a real child. See `ETHICS.md`.

## What the films contain

`outputs/final_9x16.mp4` and `outputs/final_16x9.mp4` were assembled on 26 November 2026.

- Spoken narration is 78.50 seconds, voice Kore, model `gemini-3.8-flash-tts`. The 3-second end card discloses that the film is AI-generated.
- English captions are burned in. On 9:16 they sit in the lower black bar. On 16:9 they wrap along the bottom.
- The picture is ten 1080×1080 masters fitted whole into each frame, with black bars rather than a crop that cuts people off.
- `outputs/music/score.wav` is ducked under the voice and the mix is normalized to -14 LUFS.

`python -m pipeline run` on 26 November 2026 left all ten shot files cached and reused the assembled films.

## How a storyboard becomes a film

1. `run --stage narration` sends each approved Amharic line to Gemini. The style instruction is a separate field, not part of the transcript. A SHA-256 fingerprint of the line, style, voice, model, and seed skips unchanged shots. `--scene 04` rebuilds one shot when that fingerprint misses.
2. `run --stage keyframes` prepends each present character description verbatim, then the shot prompt and the shared visual style. This storyboard defines `young_brother`, so the images go to FLUX.2 [klein] 4B. Brother shots also send `outputs/references/young_brother_ref.png`. The storyboard seed is not sent to Cloudflare. It only changes the cache key.
3. `run --stage shots` uses a clip already at `outputs/shots/wan/shot_XX.mp4` or `kaggle_outputs/shots/shot_XX.mp4` when one exists, and loops or slow-trims it to the WAV. Otherwise FFmpeg Ken Burns moves the keyframe. The source clip is not overwritten. A matching fingerprint does not rewrite `outputs/shots/shot_XX.mp4`.
4. Music is the file at `outputs/music/score.wav`. This pipeline does not generate it. A missing file becomes a quiet local drone, not a second model call.
5. `run --stage assemble` joins the masters, the end card, the captions, and the ducked score, then writes both aspect ratios.

`python -m pipeline run` with no `--stage` performs steps 3 and 5 only.

## What was measured

| Item | Result |
| --- | --- |
| First narration | 86.58 seconds. Three listeners. Pronunciation drifted. |
| Restyled narration | 78.50 seconds. Lines unchanged. |
| Keyframes | Ten Klein JPEGs. Shots 05 and 07 regenerated after prompt edits. The others stayed cached. |
| Shot masters | 1080×1080, durations matched to the WAVs. Model in the log: `ffmpeg-ken-burns`. |
| Score | 148.77 seconds, 48 kHz stereo, converted from `score.mp3`. Storyboard tempo 90 BPM. |
| Billed cost | $0.00. See `docs/COSTS.md`. |

## What failed

The full notes are in `docs/FAILURES.md`.

- Gemini returned HTTP 429. Finished WAVs stayed cached. Later shots waited and retried.
- FFmpeg was installed but invisible to an old terminal. The pipeline now finds the WinGet shim. A Windows drive colon also broke the end-card filter until the path was escaped.
- This PC has no CUDA GPU, so Wan 2.2 did not load.
- On a Kaggle Tesla T4, the Wan install hit an `ftfy` import error, then a CUDA out-of-memory error at 14.56 GiB while loading `Wan-AI/Wan2.2-TI2V-5B-Diffusers` with UMT5. Sequential CPU offload and VAE tiling are now in the Kaggle script. The container still ran about 5.5 minutes per shot and hit draft-session memory and disk pressure.
- No 480p, 4-second, 16:9 MiniMax H3 Turbo file is in this repository. The reproducible motion is Ken Burns. A browser clip can be dropped into `outputs/shots/wan/` and the next shots run will conform it without deleting that source.

## Reproducing the local films

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pipeline validate
python -m pipeline run
```

Provider stages, only when a fingerprint misses:

```powershell
python -m pipeline run --stage narration --scene 01
python -m pipeline run --stage keyframes
```

Tests are offline: `python -m pytest`.
