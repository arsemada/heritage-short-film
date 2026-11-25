# Architecture

What is implemented today, and what is deliberately not pretended.

## Command

`python -m pipeline` loads settings, then dispatches:

| Command | What it does | Network |
| --- | --- | --- |
| `validate` | Schema plus structural rules. Duration bounds come from the storyboard. | No |
| `run --stage narration` | Speech for every shot, or one shot with `--scene` | Only when a WAV is missing or stale |
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

## Not built yet

Keyframe generation, Wan or FFmpeg shot animation, music, subtitles burned into the final films, and the two aspect-ratio exports. The storyboard already holds the prompts, seeds, Ken Burns fallback, and end card those stages will read.
