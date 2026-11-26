# Failures

These are the failures that were actually hit, in the order the work ran into them. Narration and keyframes were generated on 25 November 2026. The picture and the score were finished on 26 November 2026. The Kaggle lines below are the session record filed for that Wan attempt. This repository does not contain the Kaggle traceback, the Wan checkpoint, or a Wan MP4.

## 1. Gemini HTTP 429, and what the cache kept

Narration calls `gemini-3.8-flash-tts`. Two earlier attempts never left the machine: `.env` had an empty `GEMINI_API_KEY`, and the log says `GEMINI_API_KEY is missing. Add it to .env. No request was sent.` Saving the key produced the first ten WAVs.

On later calls the Gemini SDK slept inside its own `time.sleep` on HTTP 429 before this pipeline printed anything, so a run looked hung. The client is now created with `retry_options.attempts` of 1. The pipeline prints each shot, treats 429 and "too many requests" as a rate limit, and waits 15, 20, 30, 45, then 60 seconds, up to 6 attempts, with 12 seconds between live requests. Other transient errors still wait 1 second, then 2. A message that only says "rate limited" does not take the long wait.

The SHA-256 narration fingerprint includes the line, the style instruction, the voice, the model, and the seed. The keyframe fingerprint includes the composed prompt, the model, the step count, and, when the brother reference is attached, the PNG hash. A file that already matches is not requested again. During the 429 stretch, shots that had already written a WAV stayed cached and the run continued from the shot that had no file. The restyle in the films measures 78.50 seconds. The approved Amharic lines were not rewritten to get around the limit.

## 2. FFmpeg was installed and still invisible

`ffmpeg` was not on `PATH` in a terminal that had been opened before the install. `winget` already showed Gyan.FFmpeg 9.1. The user PATH contained `WinGet\Links`, and that terminal's PATH did not. `python -m pipeline radio-cut` printed 86.58 seconds and did not write the MP4. A later shots and assemble run printed `FFmpeg was not found on PATH`.

`pipeline/ffmpeg_lookup.py` now checks `shutil.which("ffmpeg")`, then `~/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe`. ffprobe is taken from that same folder, so a probe and a render use one install. A new terminal also sees `ffmpeg` on PATH. The `py` launcher on this PC points at a missing Python 3.13. The commands in the README use `python`, which is 3.11.9.

A separate Windows filter bug showed up on the end card. FFmpeg splits filter options on `:`, so the `C:` in `C:\Users\...` became `No option name near '/Users/arsem/...'` and `Error opening output files: Invalid argument`. Paths inside filters are escaped as `C\:/...`.

## 3. No local CUDA GPU

`python notebooks/kaggle_wan2_batch.py` on this Windows machine installed Diffusers, Transformers, Accelerate, and imageio into `.venv`, then exited: `This script needs a CUDA GPU.` Wan 2.2 TI2V-5B was not loaded here. No Wan MP4 was written. The shot stage can still build a film with FFmpeg Ken Burns from the keyframes. That is the path `python -m pipeline run` takes when `outputs/shots/wan/` and `kaggle_outputs/shots/` are empty.

## 4. Kaggle T4: missing `ftfy`, then 14.56 GiB out of memory

The Kaggle environment raised an `ftfy` dependency error while importing the Wan stack. `ftfy` is now in the install list in `notebooks/kaggle_wan2_batch.py`.

Loading `Wan-AI/Wan2.2-TI2V-5B-Diffusers` together with UMT5 on the Tesla T4 then hit a CUDA out-of-memory error. The session record is 14.56 GiB allocated on a 14.56 GiB T4. `enable_model_cpu_offload()` did not keep the text encoder and the 5B transformer apart. The script now checks the device. Below compute capability 8, which includes the T4, it calls `enable_sequential_cpu_offload()` and loads weights in float16. It also calls `vae.enable_tiling()` and `vae.enable_slicing()` when those methods exist. Newer GPUs use bfloat16 and `enable_model_cpu_offload()`. The comment in `load_pipe` records why: a 16 GB-class T4 runs out of memory if UMT5 and the transformer sit on the GPU together.

## 5. Draft Session Error, after the model fit

The session record after the offload change: the checkpoint download and reconstruction was about 31.4 GB, a shot that did run took about 5.5 minutes, and ten shots at that rate are about 55 minutes. The Kaggle container then disconnected with a `Draft Session Error`. The notebook UI and the worker froze under that memory and disk pressure. This repository has no Wan clip from that session, and `python -m pipeline run` does not start it.

## 6. The pivot: Raphael clips on disk, Ken Burns if they are absent

Wan stayed off the local reproduce path. Two picture sources remain.

The delivered motion is ten user-supplied Raphael downloads, stated as MiniMax H3 Turbo, copied to `outputs/shots/shot_01.mp4` through `shot_10.mp4`. ffprobe on 26 November 2026 measures HEVC, 720×720, and durations 5.97, 11.01, 6.01, 8.01, 7.01, 6.01, 7.01, 10.01, 10.01, and 12.00 seconds. The MP4s carry no model tag. They are not 480p, 4-second, 16:9 files. The pipeline has no MiniMax key and does not call Raphael. `logs/runs.jsonl` run `8bdfc409f00245c6abc06253af61fca5` records those probed fields with status `cached_external`.

The deterministic fallback is still Ken Burns. `run --stage shots` looks for `outputs/shots/wan/shot_XX.mp4`, then `kaggle_outputs/shots/shot_XX.mp4`. If neither file exists, FFmpeg `zoompan` moves the keyframe for the length of the WAV and writes `outputs/shots/shot_XX.mp4`. That source file in `wan/` is never overwritten. A cache hit does not rewrite an existing master. A cache miss on the shots stage would replace a file that was dropped directly onto `outputs/shots/shot_XX.mp4`. Rebuilding the current films without that risk is `python -m pipeline run --stage assemble`.

An earlier Raphael set, about 3.75 seconds at 640×640 for nine shots, is not the set in the films. It is described in the next section because of what assembly did with it.

## 7. Loudness, then picture running ahead of the Amharic

On 26 November 2026 the first mix that included `outputs/music/score.wav` failed while opening `outputs/assemble/mixed.wav`:

`Filtergraph 'loudnorm=I=-14:TP=-1.5:LRA=11' was specified for a stream fed from a complex filtergraph. Simple and complex filtering cannot be used together for the same stream.`

`Error opening output files: Invalid argument.`

The narration concat is 24 kHz mono. The score is 48 kHz stereo. `sidechaincompress` already required `-filter_complex`, and `loudnorm` had been passed as `-af` on that same stream. The fix moves `loudnorm` onto the mixed pad inside the complex graph, after both streams are resampled to 24 kHz mono. The score is volume 0.35. The next assemble wrote both films. That error line is still in `logs/runs.jsonl`, followed by the successful mix.

The short Raphael set was then concatenated as-is against lines of 5.19 to 11.25 seconds, so the picture changed before the sentence finished. Looping each short clip out to the WAV made the durations match and made the motion repeat. That repeat was rejected.

The replacement clips are longer than the lines. `build_shot_command` used to slow a source up to 1.5 times the WAV with `setpts`. That slowdown was removed. A longer source now plays at 1× and `-t` cuts the extra tail. Assembly calls this from `pipeline/assemble.py` for every shot into `outputs/assemble/timed/` before the concat, which also forces every master onto one 1080×1080, 25 fps timeline. After the rebuild, each timed clip matches its WAV within a frame, and both finals are 81.50 seconds. `setpts` is not the shipped alignment. The unit test for a 2.4-second source and a 2.0-second target asserts that the filter has no `setpts`.

## Also recorded

Cloudflare FLUX.1 [schnell] returned HTTP 400 when the body included `seed`: `Additional or unevaluated properties '/seed'`. The provider sends `prompt` and `steps` only. The seed remains in the cache key.

Three listeners of the 86.58-second radio cut heard the proverb and the ending, and they also heard Amharic mispronunciation and a shift in pitch or pace between clips. The style instruction and the spoken proverb punctuation were changed. The restyle is what the films use. A second three-person listen of that restyle is not recorded. The approved narration lines were not rewritten to hide pronunciation.
