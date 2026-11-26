# Failures

Narration was generated on 25 November 2026. The Gemini calls that ran returned audio. The problems below are the ones that actually happened.

## Amharic pronunciation

Three listeners of the radio cut heard the same limitation. The voice is understandable, and the proverb landed, but `gemini-3.8-flash-tts` with the prebuilt voice `Kore` mispronounces some Amharic words and shifts pitch or pace between clips. Amharic is listed as supported. Support is not the same as consistent pronunciation.

The storyboard style instruction and the spoken proverb punctuation were changed in response. A later narration run did generate the restyled set. Measured speech is 78.50 seconds. A second three-person listen of that set is not recorded here. The approved narration lines were not rewritten to hide pronunciation.

## Runs that stopped before a request

| When | What the log shows | Cause | What fixed it |
| --- | --- | --- | --- |
| 25 November 2026, two narration attempts | `GEMINI_API_KEY is missing. Add it to .env. No request was sent.` | `.env` had an empty `GEMINI_API_KEY` line. The editor copy had not been saved. | Save the key in `.env` and run the command again. The following run produced the ten WAVs. |

No API key is copied into this file.

## Keyframes

| When | What the log shows | Cause | What fixed it |
| --- | --- | --- | --- |
| 25 November 2026, two keyframe attempts | `Cloudflare image request returned HTTP 400.` Shot 01, model `@cf/black-forest-labs/flux-1-schnell`. No JPEG was written. | The request body included `seed`. The live schema allows only `prompt` and `steps`, and answered `Additional or unevaluated properties '/seed'`. | The provider no longer sends `seed`. The storyboard seed remains in the cache fingerprint. |

## Environment

| Observation | Effect | What happened next |
| --- | --- | --- |
| `ffmpeg` was not on `PATH` in the terminal that was already open | `python -m pipeline radio-cut` printed 86.58 seconds and did not write the MP4. `winget` reported Gyan.FFmpeg 9.1 was already installed. The user PATH contained `WinGet\Links`, and that terminal's PATH did not. | A process with the refreshed PATH ran FFmpeg 9.1 and wrote `outputs/radio_cut.mp4`. A new terminal sees `ffmpeg` after the window is opened again. |
| The `py` launcher points at a missing Python 3.13 | `py` fails. | Use `python`, which is Python 3.11.9. |
| FFmpeg missing from an already-open terminal | `python -m pipeline run --stage shots` and `assemble` printed `FFmpeg was not found on PATH`. | `pipeline/ffmpeg_lookup.py` also checks the WinGet Links shim `ffmpeg.exe`. |
| End-card `drawtext` on Windows | FFmpeg split the filter on the `C:` drive colon. | Paths inside filters are escaped as `C\:/...`. |
| Score mix, 26 November 2026 | `Simple and complex filtering cannot be used together` while opening `outputs/assemble/mixed.wav`. Narration was 24 kHz mono. `score.wav` was 48 kHz stereo. | `loudnorm` moved into the same `filter_complex` as `sidechaincompress`, and the score is converted to mono 24 kHz before the duck. |

## Gemini HTTP 429

Narration calls `gemini-3.8-flash-tts`. The SDK's own retry slept inside `time.sleep` on HTTP 429 before this pipeline printed anything, so a run looked hung. The client is now created with `retry_options.attempts` of 1. The pipeline prints each shot, treats 429 and "too many requests" as a rate limit, and waits 15, 20, 30, 45, then 60 seconds, up to 6 attempts, with 12 seconds between live requests. Finished WAVs stay cached. A shot that still fails is not saved, and the same command continues from the missing shot.

## No local CUDA

`python notebooks/kaggle_wan2_batch.py` on this Windows machine installed Diffusers and then stopped: `This script needs a CUDA GPU.` Wan 2.2 TI2V-5B was not loaded here. The shot stage fell back to Ken Burns.

## Kaggle T4

These are the session results recorded for the deadline. This repository does not contain a downloaded 480p MiniMax clip.

1. The Kaggle environment raised an `ftfy` dependency error while importing the Wan stack. `ftfy` is now in the install list in `notebooks/kaggle_wan2_batch.py`.
2. Loading `Wan-AI/Wan2.2-TI2V-5B-Diffusers` together with UMT5 on the Tesla T4 hit a CUDA out-of-memory error at 14.56 GiB. `enable_model_cpu_offload()` was not enough to keep the text encoder and the transformer apart. The script now calls `enable_sequential_cpu_offload()` on GPUs below compute capability 8, and turns on VAE tiling and slicing.
3. The container then hit draft-session memory and disk pressure. A shot that did run took about 5.5 minutes. That cost is why the reproducible picture path in this repo stays FFmpeg Ken Burns from the keyframes: `python -m pipeline run` rebuilds the films on a machine with no GPU. Browser MiniMax H3 Turbo clips, if used outside this repo, belong in `outputs/shots/wan/shot_XX.mp4`. The shots stage will loop or slow-trim them to the WAV and will not overwrite that source file. The masters probed on 26 November 2026 are 1080×1080 Ken Burns files whose durations match the narration, not 4-second 480p 16:9 files.
