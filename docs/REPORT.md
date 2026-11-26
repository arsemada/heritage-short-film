# The Neighbour Who Protects

Technical report, 26 November 2026.

የሚጠብቅ ጎረቤት is an approved Amharic childhood memory. A boy in an urban Ethiopian neighbourhood drink house (tella bet) copies a customer's cigarette, coughs, and is stopped by neighbours who tell his mother. He never tries again. The film closes on ሳይቃጠል በቅጠል።

The pipeline reads `storyboard.json` and does not read `STORY.md` at runtime. A test checks that the ten narration lines and the proverb still match `STORY.md`. No names, dialogue, or extra events were added. Characters are fictionalized. The younger brother is not a photograph of a real child, and the voice is the prebuilt Gemini voice Kore, not a clone. See `ETHICS.md`.

## What the films contain

`outputs/final_9x16.mp4` and `outputs/final_16x9.mp4` were assembled on 26 November 2026 and probed with ffprobe.

| Export | Frame | Runtime | Video | Audio |
| --- | --- | --- | --- | --- |
| `outputs/final_9x16.mp4` | 1080×1920 | 81.50 seconds | H.264 | AAC 192 kb/s |
| `outputs/final_16x9.mp4` | 1920×1080 | 81.50 seconds | H.264 | AAC 192 kb/s |

81.50 seconds is 78.50 seconds of speech plus the 3-second end card. The card says the film was made with AI, names Gemini TTS voice Kore and Cloudflare Workers AI, and states that the characters are fictionalized. The same disclosure is in the file comment.

English captions are burned in. On 9:16 they sit in the lower black bar. On 16:9 they wrap along the bottom of the center square. The square picture is padded into each frame so people are not cropped.

The picture masters are ten user-supplied clips at `outputs/shots/shot_01.mp4` through `shot_10.mp4`, stated as MiniMax H3 Turbo from Raphael. ffprobe measures HEVC, 720×720, and durations 5.97, 11.01, 6.01, 8.01, 7.01, 6.01, 7.01, 10.01, 10.01, and 12.00 seconds. Each clip is slightly longer than its narration line. Assembly trims the tail at normal speed. The files are not 480p, 4-second, or 16:9, and they contain no model tag.

`outputs/music/score.wav` (148.77 seconds, 48 kHz stereo) is ducked under the voice. The mix is normalized to −14 LUFS. The storyboard tempo for that underscore is 90 BPM.

## How a storyboard becomes a film

1. `run --stage narration` sends each approved Amharic line to Gemini. The style instruction is a separate field. A SHA-256 fingerprint of the line, style, voice, model, and seed skips unchanged shots. `--scene 04` rebuilds one shot when that fingerprint misses.
2. `run --stage keyframes` prepends each present character description verbatim, then the shot prompt and the shared visual style. This storyboard defines `young_brother`, so the images go to FLUX.2 [klein] 4B. Brother shots also send `outputs/references/young_brother_ref.png`. The storyboard seed is not sent to Cloudflare. It only changes the cache key. The ten JPEGs are 1024×1024.
3. `run --stage shots` uses a clip already at `outputs/shots/wan/shot_XX.mp4` or `kaggle_outputs/shots/shot_XX.mp4` when one exists. A shorter clip loops. A longer clip is trimmed with `-t` at 1× speed. Otherwise FFmpeg Ken Burns moves the keyframe. That fallback is what lets `python -m pipeline run` rebuild a picture with no GPU. The current delivered masters were placed directly on `outputs/shots/shot_XX.mp4`. A shots cache miss would replace those files with Ken Burns.
4. Music is the file at `outputs/music/score.wav`. This pipeline does not generate it. A missing file becomes a quiet local drone, not a second model call. There is no `--stage music`.
5. `run --stage assemble` trims each master to its WAV, joins the 3-second end card, burns the captions, ducks the score, and writes both aspect ratios.

`python -m pipeline run` with no `--stage` performs steps 3 and 5 only.

## Experiments

The full notes are in `docs/EXPERIMENTS.md`. The path that reached the current films:

1. First Gemini narration, 86.58 seconds. Three listeners. Pace and the proverb worked. Pronunciation drifted.
2. Style instruction tightened and the spoken proverb's guillemets removed. Second narration, 78.50 seconds. Lines unchanged.
3. HTTP 429 retries made visible. Finished shots stay cached.
4. FLUX.1 [schnell] rejected `seed`. The provider stopped sending it.
5. Drink-house prompts and locked characters. Klein 4B for every keyframe, with a generated brother reference on the brother shots.
6. Two further keyframe passes. Unchanged shots stayed cached. Shots 05 and 07 were the last regenerations.
7. Ken Burns masters matched the WAVs, then were replaced for the delivered cut.
8. Pad instead of crop, and ASS captions in the real frame size.
9. Wan 2.2 did not run here (no CUDA). A Kaggle T4 hit `ftfy`, then 14.56 GiB out of memory, then about 5.5 minutes per shot and draft-session pressure.
10. The score brief moved from 72 BPM to the 90 BPM underscore that was actually mixed. The first mix failed on `loudnorm`. The fix is inside the complex filter graph.
11. Short clips were looped to the narration and the repeat looked wrong. Longer clips are trimmed at normal speed. `setpts` is not used.

## User testing

Three listeners heard the 86.58-second radio cut on 25 November 2026. They did not see pictures or subtitles, and they did not hear the score. All three called the pace just right and the ending clear. Listener 1 said the story was easy to picture and that the proverb landed, and heard voice shifts plus a few mispronounced words. Listeners 2 and 3 also heard occasional Amharic mispronunciation.

That listen changed the style instruction and the spoken proverb punctuation. It did not choose the 90 BPM score, the moving clips, or the duration trim. Those came later, from watching the picture cut. A three-person watch of the finished films is not recorded. Details are in `DESIGN.md`.

## Failures and pivots

The full notes are in `docs/FAILURES.md`.

- Gemini returned HTTP 429. Finished WAVs stayed cached. Later shots waited and retried.
- FFmpeg was installed but invisible to an old terminal. The pipeline now finds the WinGet shim. A Windows drive colon also broke the end-card filter until the path was escaped.
- This PC has no CUDA GPU, so Wan 2.2 did not load.
- On a Kaggle Tesla T4, the Wan install hit an `ftfy` import error, then a CUDA out-of-memory error at 14.56 GiB. Sequential CPU offload and VAE tiling are in the Kaggle script. The container still ran about 5.5 minutes per shot and hit draft-session pressure. Wan is not on the local reproduce path.
- The first score mix failed because `loudnorm` was a simple filter on a complex graph. It now sits on the mixed pad, after both streams are 24 kHz mono.
- Short image-to-video clips ran ahead of the Amharic. Looping them matched the clock and repeated the motion. The shipped fix trims a longer clip with `-t`. Both finals are 81.50 seconds, and each timed shot matches its WAV.

## Cost and ethics

Recorded cost is $0.00. Gemini and Cloudflare ran on free tiers. FFmpeg ran locally. The score and the Raphael clips were brought in as files. This repository has no MiniMax receipt. See `docs/COSTS.md`.

The end card, the MP4 comment, and `ETHICS.md` state that the film is AI-generated and that the characters are fictionalized. `logs/runs.jsonl` records models and measured durations. It does not record API keys. Smoking is shown as a failed, unpleasant imitation, not as a lesson.

## Reproducing the local films

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pipeline validate
python -m pipeline run --stage assemble
```

`python -m pipeline run` with no stage also conforms shots and then assembles. It does not call Gemini or Cloudflare. Use `--stage assemble` when the Raphael masters are already at `outputs/shots/shot_XX.mp4` and must not be replaced by a Ken Burns cache miss.

Provider stages, only when a fingerprint misses:

```powershell
python -m pipeline run --stage narration --scene 01
python -m pipeline run --stage keyframes
```

Tests are offline: `python -m pytest`.
