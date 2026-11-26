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
| `run --stage shots` | External clip if one is already on disk, otherwise FFmpeg Ken Burns | No |
| `run --stage assemble` | Subtitles, ducked music when a score exists, -14 LUFS, 9:16 and 16:9 | No |
| `radio-cut` | FFmpeg black-frame assembly of the narration WAVs | No |

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
pipeline/orchestrator.py    stage order, retries, cache decisions
        |
        +-- pipeline/narration.py     TTS provider interface
        |         |
        |         +-- GeminiTTSProvider   default model gemini-3.8-flash-tts
        |
        +-- pipeline/cache.py         SHA-256 manifest
        +-- pipeline/logger.py        logs/runs.jsonl, secrets removed
        +-- pipeline/radio_cut.py     FFmpeg command for the listening cut
```

Generation logic stops at audio files. The radio cut is a separate assembly step. A later image or video provider can be added beside `GeminiTTSProvider` without rewriting assembly.

## Narration data flow

1. Validate the storyboard. A failed schema or a broken structural rule stops the run before any request. The engine does not open `STORY.md`. This repository's tests compare the shipped narration with that file.
2. For each selected shot, build a payload from the spoken text, the separate style instruction, the model id, the voice, the seed, and the stage name.
3. Hash that payload with SHA-256.
4. If `outputs/cache/manifest.json` has the same hash and the WAV is still on disk, log a cache hit and skip the provider.
5. Otherwise call the provider, retry up to three times on rate limits and server errors, write `outputs/narration/shot_XX.wav`, update the manifest, and append a log line.
6. After a full narration run, compare the measured WAV durations with `meta.target_duration_min_sec` and `meta.target_duration_max_sec`. A mismatch is a warning. The text is not edited. This film sets those bounds to 60 and 90.

Shot 10's stored `narration_am` is the approved sentence. The proverb is stored in `proverb_am` and spoken after it as its own line.

## Provider hook

`TTS_PROVIDER=gemini` selects `GeminiTTSProvider`. `register_tts_provider` adds another class. Unknown names fail with the list of providers that exist. The Gemini client is built only when a request is about to be sent, and only when `GEMINI_API_KEY` is set.

The request follows the Gemini speech-generation guide: verbatim text in `input`, delivery in `speech_metadata.style`, voice in `speech_config`. Unary audio is WAV.

## Logs

Each line of `logs/runs.jsonl` has `timestamp`, `run_id`, `stage`, `shot_id`, `model`, `params`, `seed`, `latency_sec`, `cached`, `status`, and `error`. `params` carries the voice, the fingerprint, and the retry count. It does not carry the API key. Fields named like secrets are dropped, and known secret values are replaced with `[REDACTED]`.

## Picture, shots, and assembly

`pipeline/keyframes.py` prepends each `characters_present` description verbatim, then the shot `image_prompt`, `style_block.visual_style` (or `look`), framing, and safety. The avoid list is appended because FLUX.1 schnell has no separate negative-prompt field. The request URL is `https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}`. Schnell sends JSON `prompt` and `steps`. A storyboard that defines `young_brother` sends every keyframe to `@cf/black-forest-labs/flux-2-klein-4b` as multipart, and shots that include him also send `input_image_0` from `outputs/references/young_brother_ref.png`. The storyboard seed is not sent.

`pipeline/shots.py` does not run Wan or MiniMax. It looks for a finished clip at `outputs/shots/wan/shot_XX.mp4`, then at `kaggle_outputs/shots/shot_XX.mp4`. A clip shorter than the narration WAV is looped. A clip up to 1.5 times the WAV is slowed to fit. A longer clip is trimmed. The whole frame is padded into a 1080×1080 master at `outputs/shots/shot_XX.mp4`. If neither clip exists, FFmpeg `zoompan` uses `fallback_ken_burns` (`in_slow` / `zoom_in`, `out_slow` / `zoom_out`, `left_slow` / `pan_left`, `right_slow` / `pan_right`). The SHA-256 fingerprint covers the shot id, the source file hash, the WAV duration, the motion fields, and the seed. An unchanged fingerprint leaves the existing MP4 in place. `--scene 04` rebuilds only that shot, and only when its fingerprint misses.

`pipeline/music.py` loads `outputs/music/score.wav`, or `music.path` when that file exists. It does not replace that file. A missing score is a separate quiet drone at `outputs/music/underscore.wav`.

`pipeline/assemble.py` concatenates the masters, adds the 3-second end card, burns English captions from `outputs/subtitles/film.srt`, and fits the square into `outputs/final_9x16.mp4` and `outputs/final_16x9.mp4` with black bars. The score is ducked with `sidechaincompress` inside the same filter graph as `loudnorm=I=-14:TP=-1.5:LRA=11`.

## Cache

Every provider stage hashes a canonical JSON payload with SHA-256 and stores the hit in `outputs/cache/manifest.json`. Narration hashes the Amharic line, the style instruction, the voice, the model, and the seed. Keyframes hash the composed prompt, the model, the step count, and, when the brother reference is attached, the PNG hash. Shots hash the picture source. Assembly hashes the shot files, the WAVs, the score file, the end card, and the subtitle text. Changing one shot's storyboard fields misses only that shot. The score file is not an input to narration or keyframes, so replacing `score.wav` rebuilds the mix and leaves the speech and stills alone.

## What this repository does not run

Wan 2.2 and ACE-Step have Kaggle scripts under `notebooks/`. This machine has no CUDA GPU, and the T4 session did not leave 480p clips in `outputs/shots/`. The films in `outputs/final_9x16.mp4` and `outputs/final_16x9.mp4` use the Ken Burns masters and the dropped score.
