# Failures

No provider request has failed, because no provider request has been sent.

## Environment notes

These are local setup facts from 25 November 2026, not generation failures.

| Observation | Effect | What to do |
| --- | --- | --- |
| `ffmpeg` is not on `PATH` | `python -m pipeline radio-cut` cannot write the MP4 until FFmpeg is installed. If the narration WAVs already exist, the command still prints their spoken duration and then stops. | Install FFmpeg, open a new terminal, and run the command again. |
| The `py` launcher points at a missing Python 3.13 | `py` fails. | Use `python`, which is Python 3.11.9. |

When a real call fails, record the date, the stage, the shot id, the redacted error from `logs/runs.jsonl`, the cause, and the change that fixed it. Do not paste API keys into this file.
