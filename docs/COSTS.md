# Costs

No paid invoice is in this repository. Dollar amounts are `$0.00` because nothing here was billed, not because a price was estimated and then waived on paper.

| Work | Where it ran | What was recorded | Latency | Billed |
| --- | --- | --- | --- | --- |
| Amharic narration, `gemini-3.8-flash-tts`, voice Kore | Gemini free tier | First ten WAVs, 86.58 seconds of speech, then a restyle of the same ten lines, 78.50 seconds. Several HTTP 429 responses. No token count was returned. | Per successful call in `logs/runs.jsonl`, about 6–12 seconds. 429 waits are 15–60 seconds and are not a charge. | $0.00 |
| Keyframes and the brother reference | Cloudflare Workers AI free tier | FLUX.1 [schnell] rejected one seeded request. Klein 4B wrote the 480×480 reference PNG and the ten 1024×1024 JPEGs, including regenerated shots 05 and 07. | Successful Klein calls in the log are about 11–19 seconds each. | $0.00 |
| Wan 2.2 TI2V-5B | This PC, then a Kaggle T4 session | This PC stopped before loading the model. The T4 session hit a 14.56 GiB CUDA out-of-memory error, then draft-session pressure at about 5.5 minutes per shot. No Wan MP4 is in `outputs/shots/`. | No finished clip, so no delivered-shot latency. | $0.00 |
| Moving clips stated as MiniMax H3 Turbo / Raphael AI | Downloaded by hand into `outputs/shots/` | Ten HEVC files, 720×720, 5.97–12.00 seconds. No model tag inside the MP4. This repo has no MiniMax key and no Raphael receipt. | Not measured here. The pipeline did not call the service. | $0.00 |
| Instrumental score | File dropped in by hand | `outputs/music/score.mp3` converted locally to `outputs/music/score.wav` (148.77 seconds). The generator did not report a price. The storyboard tempo is 90 BPM. | Local FFmpeg convert only. | $0.00 |
| Ken Burns fallback, trim, ducking, loudness, captions, both films | Local FFmpeg 9.1 on Windows | Ken Burns masters were written earlier and later replaced. The delivered films are `outputs/final_9x16.mp4` and `outputs/final_16x9.mp4`, each 81.50 seconds. | The assemble that wrote the current films finished in about 83 seconds of wall clock. | $0.00 |

Total recorded in this project: **$0.00**.

If a Raphael credit balance moved when the longer clips were generated, that charge is not in this repository, and this table does not invent it.
