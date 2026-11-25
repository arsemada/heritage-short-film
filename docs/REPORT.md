# Project report

Status on 25 November 2026: slices 1–4 are implemented and covered by offline tests. The film has not been generated.

## Done

- Storyboard with 10 shots, the approved Amharic narration, English subtitles, fictionalized character descriptions, and an AI disclosure end card.
- JSON Schema and a validator that refuses a rewritten narration line.
- Cache fingerprints, JSONL logs with secrets removed, and bounded retries.
- Gemini TTS provider coded against the published interactions API, with the speaking style kept out of the transcript. It has not been called.
- Radio-cut command, which needs FFmpeg before it can write `outputs/radio_cut.mp4`.

## Not done

- A listened-to Amharic narration.
- Keyframes, shot animation, original music, burned-in subtitles, and the 9:16 and 16:9 films.
- Audience tests, the public post, and the walkthrough.

## Planned runtime

Shot durations plus the 5-second end card add up to 82 seconds. That number is a plan. The spoken length will be measured from the WAV files and will not be fixed by editing the narration without approval.
