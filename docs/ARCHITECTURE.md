# Architecture

What is implemented today, and what is deliberately not pretended.

## Command

`python -m pipeline` loads settings, then dispatches:

| Command | What it does | Network |
| --- | --- | --- |
| `validate` | Schema plus structural rules. Duration bounds come from the storyboard. | No |
| `run --stage narration` | Speech for every shot, or one shot with `--scene` | Only when a WAV is missing or stale |
| `run --stage keyframes` | One JPEG per shot. Klein 4B when the storyboard has `young_brother`, otherwise FLUX.1 schnell | Only on a cache miss |
| `run` | Conform shots, then assemble both films. Does not call Gemini or Cloudflare | No |
| `run --stage shots` | External clip if one is already in `wan/` or `kaggle_outputs/`, otherwise FFmpeg Ken Burns | No |
| `run --stage assemble` | Trim or loop each master to its WAV, subtitles, ducked score, −14 LUFS, 9:16 and 16:9 | No |
| `radio-cut` | FFmpeg black-frame assembly of the narration WAVs | No |

There is no music stage. `pipeline/music.py` only locates `outputs/music/score.wav`. ACE-Step, when it is used, is `notebooks/kaggle_acestep.py` on a GPU machine.

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

The engine does not open `STORY.md`. This repository's tests compare the shipped narration with that file.

## Narration data flow

1. Validate the storyboard. A failed schema or a broken structural rule stops the run before any request.
2. For each selected shot, build a payload from the spoken text, the separate style instruction, the model id, the voice, the seed, and the stage name. Shot 10's stored `narration_am` is the approved sentence. The proverb is stored in `proverb_am` and spoken after it as its own line.
3. Hash that payload with SHA-256.
4. If `outputs/cache/manifest.json` has the same hash and the WAV is still on disk, log a cache hit and skip the provider.
5. Otherwise call Gemini, write `outputs/narration/shot_XX.wav`, update the manifest, and append a log line. HTTP 429 waits 15, 20, 30, 45, then 60 seconds, up to 6 attempts, with 12 seconds between live requests. The SDK retry count is 1 so those waits are visible. A finished WAV stays cached. A shot that still fails is not saved, and the same command continues from the missing shot.
6. After a full narration run, compare the measured WAV durations with `meta.target_duration_min_sec` and `meta.target_duration_max_sec`. A mismatch is a warning. The text is not edited. This film sets those bounds to 60 and 90.

`TTS_PROVIDER=gemini` selects `GeminiTTSProvider`. The Gemini client is built only when a request is about to be sent, and only when `GEMINI_API_KEY` is set. Verbatim text goes in `input`. Delivery goes in `speech_metadata.style`. The voice goes in `speech_config`.

## Keyframes

`pipeline/keyframes.py` prepends each `characters_present` description verbatim, then the shot `image_prompt`, the shared visual style, framing, and safety. The avoid list is appended because FLUX.1 schnell has no separate negative-prompt field. Schnell sends JSON `prompt` and `steps` only. Sending `seed` returns HTTP 400. The storyboard seed stays in the cache fingerprint and is not sent.

Because this storyboard defines `young_brother`, every keyframe uses `@cf/black-forest-labs/flux-2-klein-4b` as multipart, with `steps` fixed at 4. Shots that include him also send `input_image_0` from `outputs/references/young_brother_ref.png`. That PNG is an AI portrait at 480×480, not a family photograph. Output stills on disk are 1024×1024 JPEGs.

## Shots and duration sync

`pipeline/shots.py` does not run Wan or MiniMax. It looks for a finished clip at `outputs/shots/wan/shot_XX.mp4`, then at `kaggle_outputs/shots/shot_XX.mp4`.

`build_shot_command` fits the whole frame:

`scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2:black,fps=25`

Duration follows the narration WAV.

- If the source duration is unknown, or the source is not longer than the WAV by more than 0.05 seconds, the command adds `-stream_loop -1` and `-t` set to the WAV length. A short clip repeats until the line ends.
- If ffprobe reports a longer source, the loop flag stays off. The same `-t` trims the tail. Playback stays at normal speed. There is no `setpts` factor.

A missing external clip falls back to FFmpeg `zoompan` from the keyframe, using `fallback_ken_burns` (`in_slow` / `zoom_in`, `out_slow` / `zoom_out`, `left_slow` / `pan_left`, `right_slow` / `pan_right`, `up_slow` / `pan_up`). That path is what makes `python -m pipeline run` able to rebuild a picture on a machine with no GPU, from the keyframes and WAVs alone.

The SHA-256 fingerprint for a shot covers the shot id, the source file hash, the WAV duration, the motion fields, the motion prompt, and the seed. The stored conform label for an external clip is still the string `loop-or-slow-trim`. The command itself no longer slows the picture. An unchanged fingerprint leaves the existing MP4 in place. The lookup checks that the path exists and is non-empty. It does not hash the bytes again, so a file replaced by hand at `outputs/shots/shot_XX.mp4` is left alone until the fingerprint misses. A miss writes Ken Burns over that path. The external source in `wan/` is never overwritten.

The clips in the current films were copied onto `outputs/shots/shot_XX.mp4` directly. They are HEVC, 720×720, and each is slightly longer than its WAV. Assembly, not the shots stage, is what trimmed them for the concat.

## Assembly

`pipeline/assemble.py` does this for every shot before the join:

1. Measure the WAV.
2. Call `build_shot_command` into `outputs/assemble/timed/shot_XX.mp4`, passing the probed source duration.
3. Concatenate those timed clips with the 3-second end card. The card is 1080×1080 at 25 fps, so the concat can copy one video size. Its text is `end_card.text` in the storyboard: the film is AI-generated, the narration is Gemini TTS voice Kore, the pictures went through Cloudflare Workers AI, and the characters are fictionalized.
4. Write `outputs/subtitles/film.srt` and an ASS file per export. PlayResX and PlayResY match the export, so FontSize is in real pixels. Vertical captions use Arial 36, side margins 64, bottom margin 120. Horizontal captions use Arial 32 and side margins 280 so lines wrap inside the center square.
5. Fit the square into the target with `scale=W:H:force_original_aspect_ratio=decrease,pad=...:black`, then burn the ASS. 9:16 is 1080×1920. 16:9 is 1920×1080. Black bars are intentional.
6. Mix audio. The score is resampled to 24 kHz mono, set to volume 0.35, ducked with `sidechaincompress` against the narration, and passed through `loudnorm=I=-14:TP=-1.5:LRA=11` on the same complex filter graph. `loudnorm` is not a separate `-af`. The export audio is AAC at 192 kb/s. A comment metadata field repeats the AI disclosure.

The assembly fingerprint hashes the shot files, the WAVs, the score file, the end card, the subtitle texts, and the layout string `fit-square-captions-v5-loop-to-wav`. Replacing a master or the score misses that cache and rebuilds both films. The current probed runtime of both MP4s is 81.50 seconds.

## Music

`load_score` returns `outputs/music/score.wav`, or `music.path` when that field is a non-empty path and the file exists. It does not replace `score.wav` and it does not call ACE-Step. A missing score is planned as `outputs/music/underscore.wav`: a 196 Hz sine at volume 0.03, lowpassed, faded, long enough for the film. This film's mix uses the dropped score. The storyboard brief says 90 BPM, D major, status `not_generated`, path null. The tempo is the brief, not a BPM measurement of the WAV.

## Cache and logs

Every provider stage hashes canonical JSON with SHA-256 and stores the hit in `outputs/cache/manifest.json`. Changing one shot's storyboard fields misses only that shot. The score file is not an input to narration or keyframes.

Each line of `logs/runs.jsonl` has `timestamp`, `run_id`, `stage`, `shot_id`, `model`, `params`, `seed`, `latency_sec`, `cached`, `status`, and `error`. `params` carries fingerprints and measured durations. It does not carry the API key. Fields named like secrets are dropped, and known secret values are replaced with `[REDACTED]`.

## What this repository does not run

Wan 2.2 and ACE-Step have Kaggle scripts under `notebooks/`. This machine has no CUDA GPU. The T4 session did not leave Wan clips in `outputs/shots/`. The moving pictures in the current finals are the user-supplied files at `outputs/shots/shot_01.mp4` through `shot_10.mp4`, trimmed to the narration. Ken Burns remains the offline fallback when those files are absent and the shots stage has to write a master.
