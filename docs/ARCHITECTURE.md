# Architecture

What is implemented today. The film contract is `storyboard.json`. The engine does not open `STORY.md`.

## The five steps

Production order is narration, keyframes, shots, a music file, then assembly. The CLI stages are the four names in `pipeline/__main__.py`: `narration`, `keyframes`, `shots`, `assemble`. There is no `--stage music`.

| Command | What it does | Network |
| --- | --- | --- |
| `validate` | Schema plus structural rules. Duration bounds come from the storyboard. | No |
| `run --stage narration` | Speech for every shot, or one shot with `--scene` | Only when a WAV is missing or stale |
| `run --stage keyframes` | One JPEG per shot. Klein 4B when the storyboard has `young_brother`, otherwise FLUX.1 schnell | Only on a cache miss |
| `run --stage shots` | External clip if one is already in `wan/` or `kaggle_outputs/`, otherwise FFmpeg Ken Burns | No |
| `run --stage assemble` | Trim or loop each master to its WAV, subtitles, ducked score, −14 LUFS, 9:16 and 16:9 | No |
| `run` | Shots, then assemble. Does not call Gemini or Cloudflare | No |
| `radio-cut` | FFmpeg black-frame assembly of the narration WAVs | No |

Music is `pipeline/music.py`. It locates `outputs/music/score.wav`. ACE-Step, when it is used, is `notebooks/kaggle_acestep.py` on a GPU machine. Wan 2.2, when it is used, is `notebooks/kaggle_wan2_batch.py`. Neither script is started by `python -m pipeline run`.

## Why Wan is not on that command

`notebooks/kaggle_wan2_batch.py` loads `Wan-AI/Wan2.2-TI2V-5B-Diffusers` through `WanImageToVideoPipeline` and `AutoencoderKLWan`. It is written for a Kaggle GPU: 49 frames, 24 fps, 832×480, 25 steps. This Windows machine has no CUDA device, and the script exits with `This script needs a CUDA GPU.`

On a Tesla T4 the session record is: an `ftfy` import error, then a CUDA out-of-memory error with 14.56 GiB allocated on a 14.56 GiB card while UMT5 and the 5B transformer were loaded together. `load_pipe` now calls `enable_sequential_cpu_offload()` on GPUs below compute capability 8, and `vae.enable_tiling()` plus `vae.enable_slicing()` when those methods exist. The session record after that change is a checkpoint download and reconstruction of about 31.4 GB, about 5.5 minutes per shot, and a Kaggle `Draft Session Error`. No Wan file was left in `outputs/shots/`.

The offline picture is therefore Ken Burns from the Klein keyframes, which needs only FFmpeg. The delivered films use a second, external source: the Raphael clips already at `outputs/shots/shot_01.mp4` through `shot_10.mp4`, probed as HEVC 720×720 and slightly longer than each WAV. `python -m pipeline run --stage assemble` trims those files and writes both aspects with no network and no GPU. If those files are removed and the shots stage runs with an empty `wan/` directory, the same command path writes Ken Burns instead. That is the hybrid. The pipeline never calls MiniMax or Raphael.

## Modules

```text
python -m pipeline
        |
        v
pipeline/config.py          paths, .env, provider name
        |
        v
pipeline/validator.py       JSON Schema and structural rules
        |
        v
pipeline/orchestrator.py    narration order, retries, cache decisions
        |
        +-- pipeline/narration.py     Gemini TTS, model gemini-3.8-flash-tts
        +-- pipeline/keyframes.py     Cloudflare FLUX.1 schnell or FLUX.2 klein 4B
        +-- pipeline/shots.py         external clip conform, or Ken Burns
        +-- pipeline/music.py         locate score.wav, or plan a local drone
        +-- pipeline/assemble.py      timed shots, captions, duck, both aspects
        +-- pipeline/cache.py         SHA-256 manifest
        +-- pipeline/logger.py        logs/runs.jsonl, secrets removed
        +-- pipeline/ffmpeg_lookup.py PATH, then the WinGet Links shim
```

## Narration

1. Validate the storyboard. A failed schema or a broken structural rule stops the run before any request.
2. For each selected shot, build a payload from the spoken text, the separate style instruction, the model id, the voice, the seed, and the stage name. Shot 10's stored `narration_am` is the approved sentence. The proverb is stored in `proverb_am` and spoken after it as its own line.
3. Hash that payload with SHA-256.
4. If `outputs/cache/manifest.json` has the same hash and the WAV is still on disk, log a cache hit and skip the provider.
5. Otherwise call Gemini, write `outputs/narration/shot_XX.wav`, update the manifest, and append a log line. HTTP 429 waits 15, 20, 30, 45, then 60 seconds, up to 6 attempts, with 12 seconds between live requests. The SDK retry count is 1 so those waits are visible.
6. After a full narration run, compare the measured durations with `meta.target_duration_min_sec` and `meta.target_duration_max_sec` (60 and 90 for this film). A mismatch is a warning. The text is not edited.

`--scene 04` hashes and generates only shot 04. Changing shot 04's line or seed does not miss shots 01–03 or 05–10. Changing `meta.tts_style_instruction` misses every shot, because that field is inside every narration payload.

`TTS_PROVIDER=gemini` selects `GeminiTTSProvider`. The client is built only when a request is about to be sent, and only when `GEMINI_API_KEY` is set. Verbatim text goes in `input`. Delivery goes in `speech_metadata.style`.

## Keyframes

`pipeline/keyframes.py` prepends each `characters_present` description verbatim, then the shot `image_prompt`, the shared visual style, framing, and safety. The avoid list is appended because FLUX.1 schnell has no separate negative-prompt field. Schnell sends JSON `prompt` and `steps` only. Sending `seed` returns HTTP 400. The storyboard seed stays in the cache fingerprint and is not sent.

Because this storyboard defines `young_brother`, every keyframe uses `@cf/black-forest-labs/flux-2-klein-4b` as multipart, with `steps` fixed at 4. Shots that include him also send `input_image_0` from `outputs/references/young_brother_ref.png`. That PNG is an AI portrait at 480×480, not a family photograph. The ten stills on disk are 1024×1024 JPEGs. Editing one shot's `image_prompt` misses only that shot's keyframe fingerprint.

## Shots and duration sync

`pipeline/shots.py` does not run Wan or MiniMax. It looks for a finished clip at `outputs/shots/wan/shot_XX.mp4`, then at `kaggle_outputs/shots/shot_XX.mp4`.

`build_shot_command` fits the whole frame into a 1080×1080 master at 25 fps:

`scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2:black,fps=25`

Duration follows the narration WAV.

- If the source duration is unknown, or the source is not longer than the WAV by more than 0.05 seconds, the command adds `-stream_loop -1` and `-t` set to the WAV length.
- If ffprobe reports a longer source, the loop stays off. The same `-t` trims the tail. Playback stays at 1×. There is no `setpts` factor. A slower `setpts` path was removed so a clip that is only slightly longer than the line is not stretched and then cut.

A missing external clip falls back to FFmpeg `zoompan` from the keyframe, using `fallback_ken_burns` (`in_slow` / `zoom_in`, `out_slow` / `zoom_out`, `left_slow` / `pan_left`, `right_slow` / `pan_right`, `up_slow` / `pan_up`). The SHA-256 fingerprint covers the shot id, the source file hash, the WAV duration, the motion fields, the motion prompt, and the seed. The stored conform label for an external clip is still the string `loop-or-slow-trim`. The command itself no longer slows the picture. An unchanged fingerprint leaves the existing MP4 in place. The lookup checks that the path exists and is non-empty. It does not hash those bytes again.

The clips in the current films were copied onto `outputs/shots/shot_XX.mp4` directly. Assembly, not the shots stage, is what trimmed them.

## Assembly

`pipeline/assemble.py` does this before the join:

1. Measure each WAV.
2. Call `build_shot_command` into `outputs/assemble/timed/shot_XX.mp4`, passing the probed source duration. This is the duration sync. It lives in `build_shot_command`. Assembly calls it. It does not add `setpts`.
3. Concatenate those timed clips with the 3-second end card. The card is 1080×1080 at 25 fps. Its text is `end_card.text`: the film is AI-generated, the narration is Gemini TTS voice Kore, the pictures went through Cloudflare Workers AI, and the characters are fictionalized.
4. Write `outputs/subtitles/film.srt` and an ASS file per export. PlayResX and PlayResY match the export, so FontSize is in real pixels. Vertical captions use Arial 36, side margins 64, bottom margin 120. Horizontal captions use Arial 32 and side margins 280 so a long English line wraps inside the center square.
5. Fit the square with `scale=W:H:force_original_aspect_ratio=decrease` and pad with black. 9:16 is 1080×1920. 16:9 is 1920×1080. Black bars are intentional. Captions are burned after the pad.
6. Mix audio in one complex graph:

```text
[1:a]aresample=24000,aformat=channel_layouts=mono,volume=0.35[mus];
[0:a]aresample=24000,aformat=channel_layouts=mono[nar];
[mus][nar]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=300[ducked];
[nar][ducked]amix=inputs=2:duration=first:normalize=0[mix];
[mix]loudnorm=I=-14:TP=-1.5:LRA=11[aout]
```

`loudnorm` stays on `[mix]`. It is not a second `-af`. The export audio is AAC at 192 kb/s. A comment metadata field repeats the AI disclosure.

The assembly fingerprint hashes the shot files, the WAVs, the score file, the end card, the subtitle texts, and the layout string `fit-square-captions-v5-loop-to-wav`. Replacing a master or the score misses that cache. The probed runtime of both current MP4s is 81.50 seconds.

## Music

`load_score` returns `outputs/music/score.wav`, or `music.path` when that field is a non-empty path and the file exists. It does not replace `score.wav` and it does not call ACE-Step. A missing score is planned as `outputs/music/underscore.wav`: a 196 Hz sine at volume 0.03, lowpassed, faded, long enough for the film. This film's mix uses the dropped score. The storyboard brief says 90 BPM, D major, status `not_generated`, path null. The tempo is the brief, not a BPM measurement of the WAV. The brief asks for a quiet original instrumental with no vocals. It does not name instruments.

## Cache and logs

Every provider stage hashes canonical JSON with SHA-256 and stores the hit in `outputs/cache/manifest.json`. Changing one shot's storyboard fields misses only that shot, except for a shared field such as the style instruction or the visual style. The score file is not an input to narration or keyframes.

Each line of `logs/runs.jsonl` has `timestamp`, `run_id`, `stage`, `shot_id`, `model`, `params`, `seed`, `latency_sec`, `cached`, `status`, and `error`. Fields named like secrets are dropped, and known secret values are replaced with `[REDACTED]`. The probe pass for the files inside the current films is run `8bdfc409f00245c6abc06253af61fca5`.
