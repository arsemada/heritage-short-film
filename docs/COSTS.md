# Costs

No paid invoice was issued. Every call below was on a free tier or on this machine. Dollar amounts are `$0.00` because that is what was billed, not because the providers are estimated.

| Work | Where it ran | What was recorded | Billed |
| --- | --- | --- | --- |
| Amharic narration, `gemini-3.8-flash-tts`, voice Kore | Gemini free tier | Ten WAVs, then a restyle of the same ten lines. Several HTTP 429 responses. No token count was returned. | $0.00 |
| Keyframes and the brother reference | Cloudflare Workers AI free tier | FLUX.1 [schnell] rejected one seeded request. Klein 4B then wrote the reference PNG and the ten JPEGs, including regenerated shots 05 and 07. | $0.00 |
| Wan 2.2 TI2V-5B | This PC, then a Kaggle T4 session | This PC stopped before loading the model. The T4 session hit a 14.56 GiB CUDA out-of-memory error and container pressure. No Wan MP4 is in `outputs/shots/`. | $0.00 |
| MiniMax H3 Turbo / Raphael AI | Not in this repository | No 480p, 4-second, 16:9 clip is on disk. Nothing is billed here. | $0.00 |
| Instrumental score | File dropped in by hand | `outputs/music/score.mp3` converted locally to `outputs/music/score.wav`. The generator did not report a price. | $0.00 |
| Ken Burns, ducking, loudness, captions, both films | Local FFmpeg 9.1 | `outputs/final_9x16.mp4` and `outputs/final_16x9.mp4`. Spoken narration 78.50 seconds plus a 3-second end card. | $0.00 |

Total billed: **$0.00**.
