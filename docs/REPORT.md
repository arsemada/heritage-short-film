# The Neighbour Who Protects

Technical report, 26 November 2026.

## 1. Executive summary

የሚጠብቅ ጎረቤት is an 81.50-second Amharic short film, delivered in 9:16 and 16:9 from one storyboard. I built the pipeline that turns `storyboard.json` into that film, ran it, and kept every measured result in the repository.

The film is a childhood memory set in an urban Ethiopian neighbourhood drink house (tella bet). A boy copies a customer's cigarette, coughs, and is stopped by neighbours who tell his mother. He never tries again. The last spoken line is ሳይቃጠል በቅጠል። The approved narration is not rewritten. Characters are fictionalized. The voice is the prebuilt Gemini voice Kore, not a clone.

| Deliverable | Measured |
| --- | --- |
| `outputs/final_9x16.mp4` | 1080×1920, H.264, AAC 192 kb/s, 81.50 seconds, 14,761,993 bytes |
| `outputs/final_16x9.mp4` | 1920×1080, H.264, AAC 192 kb/s, 81.50 seconds, 15,068,700 bytes |
| Speech inside both films | 78.50 seconds, then a 3-second AI disclosure card |
| Recorded cost | $0.00 |

81.50 seconds is the measured speech plus the card. The storyboard's plan is 80.0 seconds. Assembly follows the WAVs, not the plan.

Wan 2.2 did not produce a clip. This PC has no CUDA GPU. A Kaggle Tesla T4 session exhausted 14.56 GiB and then hit a `Draft Session Error`. The moving shots in the films are ten MiniMax H3 Turbo clips I generated in Raphael, probed at 720×720 and trimmed to each narration line. Ken Burns from the keyframes is the offline fallback, so another machine can still rebuild a picture with FFmpeg and no GPU.

## 2. Creative vision, audience, and the listen

The audience is urban Ethiopian families, peers, and young adults. They watch on a phone and on a desktop, so every shot is framed in the center and the square master is padded into both aspects. Cropping was rejected after it cut people off. English subtitles are burned in: on 9:16 they sit in the lower bar, on 16:9 they wrap inside the center square. Amharic stays the spoken language. The proverb is not replaced by its gloss.

The place is worn plaster, woven wall covering, wooden benches, plastic stools, and tall glasses of an unnamed cloudy drink. It is not a luxury bar and not a caricature. Clothing is locked per character and copied unchanged into each keyframe prompt. Smoking is a failed, unpleasant imitation. Shot 07 does not describe how to smoke. The ten-shot arc, from the afternoon doorway to the twilight lane, is in `DESIGN.md`.

Three listeners heard the first narration on 25 November 2026: `outputs/radio_cut.mp4`, 86.58 seconds, black 9:16 frame, no pictures, no subtitles, no score.

| Listener | What was recorded |
| --- | --- |
| 1 | Pace just right. Easy to picture, like a morning radio ትረካ. The proverb landed. Slight voice shifts between clips, and a few mispronounced Amharic words. |
| 2 | Pace just right. The story and the ending message were clear. Occasional Amharic mispronunciation. |
| 3 | Pace just right. Ending message strong. A couple of words had minor pronunciation quirks. |

That listen is why the style instruction now asks for one consistent Addis Ababa radio voice, and why the spoken proverb no longer includes «». The ten `narration_am` lines were not edited. The restyle measures 78.50 seconds: 5.92, 10.37, 5.19, 7.74, 7.00, 5.91, 6.20, 9.06, 9.86, 11.25. A second three-person listen of that restyle is not recorded. A three-person watch of the finished pictures is not recorded. Those are open tests, not results.

Picture decisions made after watching the exports, separate from those three listeners: pad instead of crop, size captions in the real frame, mix the underscore at the storyboard's 90 BPM, and replace repeated short clips with longer ones trimmed to each line.

## 3. System architecture and reproducibility

`pipeline/` does not contain this film's story. Another `storyboard.json` can use the same commands. `python -m pipeline validate` checks the schema and the structural rules before any provider is called. `python -m pytest` covers the cache, the CLI, narration text, picture filters, and the storyboard contract without calling Gemini, Cloudflare, or FFmpeg.

Production has five steps. Four are CLI stages. Music is a file.

1. **Narration.** Each approved line goes to `gemini-3.8-flash-tts`, voice Kore. The style instruction is a separate field. The SHA-256 fingerprint covers the line, the style, the voice, the model, and the seed. A matching WAV is not requested again. `--scene 04` rebuilds only shot 04. HTTP 429 waits 15, 20, 30, 45, then 60 seconds, up to six attempts, and finished shots stay cached.
2. **Keyframes.** Each present character description is prepended verbatim. This storyboard defines `young_brother`, so every still uses FLUX.2 [klein] 4B. Brother shots also send `outputs/references/young_brother_ref.png`, a generated 480×480 portrait, not a family photograph. The ten JPEGs are 1024×1024. Cloudflare does not receive the storyboard seed. Sending `seed` to FLUX.1 [schnell] returned HTTP 400, so the provider sends `prompt` and `steps` only. The seed remains in the cache key.
3. **Shots.** An external clip at `outputs/shots/wan/shot_XX.mp4` or `kaggle_outputs/shots/shot_XX.mp4` is conformed to the WAV. If neither file exists, FFmpeg Ken Burns moves the keyframe. That is the path with no GPU. The source clip in `wan/` is never overwritten.
4. **Music.** `outputs/music/score.wav` is ducked under the voice. There is no `--stage music` and no ACE-Step call inside `python -m pipeline run`. A missing score becomes a quiet local drone.
5. **Assemble.** Each master is fit to a 1080×1080, 25 fps timeline for the length of its WAV, joined to the 3-second disclosure card, captioned, mixed, and written to both aspects.

`python -m pipeline run` with no `--stage` runs steps 3 and 5 only. It does not call Gemini or Cloudflare. Secrets live in `.env`, which is gitignored. `.env.example` lists the names and leaves the values empty.

### Duration sync

Narration lines run from 5.19 to 11.25 seconds. The Raphael masters run from 5.97 to 12.00 seconds. `build_shot_command` in `pipeline/shots.py` plays a longer source at normal speed and cuts the tail with `-t`. `pipeline/assemble.py` calls that command for every shot into `outputs/assemble/timed/` before the concat. A shorter source is looped. An earlier cut looped clips of about 3.75 seconds, the motion repeated, and that cut was rejected. `setpts` slowing was removed so a clip that is only slightly longer than the line is not stretched. The picture test asserts that a longer source has no `setpts` filter. After the rebuild, each timed shot matches its WAV within a frame.

### Audio

The score and the narration do not share a sample rate. Narration is 24 kHz mono. `score.wav` is 48 kHz stereo, 148.77 seconds. One complex graph resamples both to 24 kHz mono, sets the score to volume 0.35, ducks it with `sidechaincompress`, and runs `loudnorm=I=-14:TP=-1.5:LRA=11` on the mixed pad. `loudnorm` is not a second `-af`. The square is then padded to 1080×1920 and 1920×1080. Black bars are intentional. Captions are an ASS file whose PlayRes matches the export, so the type is sized in real pixels.

### What is reproducible offline

With the WAVs and keyframes on disk, and with no file in `wan/` or `kaggle_outputs/`, `python -m pipeline run` writes Ken Burns masters and both films. The delivered Raphael cut is rebuilt with `python -m pipeline run --stage assemble`, which trims the files already at `outputs/shots/shot_XX.mp4` and does not call a network. A shots-stage cache miss would replace those masters with Ken Burns. The external path the shots stage is written to read, and not overwrite, is `outputs/shots/wan/`.

## 4. Experiments and measured results

`docs/EXPERIMENTS.md` is the run log. These are the measurements that define the films on disk, probed with ffprobe on 26 November 2026 unless the row says otherwise.

| Item | Result |
| --- | --- |
| First narration | 86.58 seconds. Per shot: 6.90, 13.26, 6.18, 8.62, 8.18, 7.10, 6.24, 9.90, 10.11, 10.09. Three listeners. Pace and the proverb worked. Pronunciation drifted. |
| Restyle | Same ten lines. New style instruction, spoken proverb without guillemets. 78.50 seconds: 5.92, 10.37, 5.19, 7.74, 7.00, 5.91, 6.20, 9.06, 9.86, 11.25. These WAVs are in the films. |
| Cache proof | Shots whose prompt and seed did not change kept their keyframe hash. Shots 05 and 07 were the last regenerations. A later shots run with the same fingerprint did not rewrite the MP4. |
| Keyframes | Ten 1024×1024 JPEGs, FLUX.2 [klein] 4B. Brother reference 480×480 PNG, generated, not a photograph. |
| Wan 2.2 | No MP4. Local run stopped before the model loaded. The T4 session left no clip in `outputs/shots/`. |
| Rejected picture cut | About 3.75-second clips against 5–11 second lines. Looping matched the clock and repeated the motion. |
| Delivered masters | HEVC, 720×720. 5.97, 11.01, 6.01, 8.01, 7.01, 6.01, 7.01, 10.01, 10.01, 12.00 seconds. Each is longer than its WAV. No model tag inside the file. Stated source: MiniMax H3 Turbo via Raphael. |
| After `-t` | Timed shots match the WAVs within a frame. Both finals are 81.50 seconds. |
| Score | 148.77 seconds, 48 kHz stereo, converted locally from `score.mp3`. Storyboard tempo 90 BPM. The earlier brief was 72 BPM. The 90 is the storyboard field, not a BPM reading of the WAV. |

## 5. Failures and the pivot

`docs/FAILURES.md` keeps the order in which the work actually broke.

1. **HTTP 429.** Gemini's SDK slept with no pipeline log. The client retry count is now 1. The pipeline waits and prints the shot. A WAV that already matches its fingerprint is not requested again, so a failed shot does not redo the shots that finished.
2. **FFmpeg was installed and invisible.** An old terminal did not see the WinGet Links shim. `pipeline/ffmpeg_lookup.py` checks `PATH`, then that shim, and takes ffprobe from the same folder. A Windows `C:` in the end-card filter was escaped so the drive colon is not parsed as a filter option.
3. **No local CUDA GPU.** `notebooks/kaggle_wan2_batch.py` installs its libraries and exits: `This script needs a CUDA GPU.`
4. **Tesla T4.** The session record is a missing `ftfy` import, then a CUDA out-of-memory error with 14.56 GiB allocated on a 14.56 GiB card while `Wan-AI/Wan2.2-TI2V-5B-Diffusers` and UMT5 were loaded together. The script now calls `enable_sequential_cpu_offload()` on that class of GPU and `vae.enable_tiling()`.
5. **Draft Session Error.** The session record after that change is about 31.4 GB of checkpoint download and reconstruction, about 5.5 minutes per shot, about 55 minutes for ten shots, then a Kaggle disconnect and a frozen worker. This repository does not contain the checkpoint, the traceback, or a Wan MP4.
6. **Pivot.** I generated ten moving shots in Raphael and placed them at `outputs/shots/shot_01.mp4` through `shot_10.mp4`. The run log records the probed 720×720 durations with status `cached_external`. It does not claim 480p, 4 seconds, or 16:9, because that is not what ffprobe measured. Ken Burns remains the fallback when the shots stage has no external clip, which is what makes `python -m pipeline run` reproducible on a machine with no GPU.
7. **Assembly.** `loudnorm` as `-af` on a complex graph failed with `Error opening output files: Invalid argument`. It now sits on the mixed pad. Short clips that ran ahead of the Amharic were replaced. The shipped alignment is `-t` at normal speed, not `setpts`.

## 6. Cost, consent, labelling, and licences

No invoice is in this repository. Dollar amounts are $0.00 because nothing here was billed.

| Work | Where | Billed |
| --- | --- | --- |
| Narration, `gemini-3.8-flash-tts`, voice Kore | Gemini free tier. Two full sets. Several HTTP 429 responses. No token count was returned. | $0.00 |
| Keyframes and the brother reference | Cloudflare Workers AI free tier. Klein 4B. One FLUX.1 [schnell] request was rejected for `seed` before a JPEG was saved. | $0.00 |
| Wan 2.2 TI2V-5B | This PC, then a Kaggle T4. No finished clip. | $0.00 |
| MiniMax H3 Turbo on Raphael AI | Raphael AI free tier, in the browser. Ten files brought into `outputs/shots/`. | $0.00 |
| Score | `score.mp3` converted locally to `score.wav`. The pipeline did not call ACE-Step. | $0.00 |
| Ken Burns, trim, ducking, captions, both films | Local FFmpeg 9.1. | $0.00 |

Total recorded: **$0.00**. Raphael AI was the free tier. See `docs/COSTS.md`.

Consent and labelling are in `ETHICS.md`.

- No family photograph is committed. The brother reference is a generated portrait. Family consent covers the inspiration, not a file in git.
- Narration uses the prebuilt voice Kore. The pipeline does not call voice cloning.
- The 3-second end card says the film was made with AI, names Gemini voice Kore and Cloudflare Workers AI, and states that the characters are fictionalized.
- The MP4 comment repeats that disclosure.
- `logs/runs.jsonl` records models, seeds, and measured durations. It does not record API keys. The moving-clip rows name MiniMax H3 Turbo (Raphael AI) and the probed geometry.

Licences checked for this project: Gemini API terms for narration, Apache-2.0 for FLUX.2 [klein] 4B and for Wan 2.2, MIT for the ACE-Step 1.5 script that was not called, and FFmpeg's LGPL/GPL terms for the local build that uses libx264. FLUX.2 [klein] 9B and FLUX.2 [dev] were not used. Raphael's own terms cover the browser clips. This repo does not redistribute those weights.

## 7. Verification and what is still open

| Check | Result |
| --- | --- |
| Storyboard | Valid. 10 shots. Planned runtime 80.0 seconds including the end card. Films follow the measured 78.50 seconds of speech and are 81.50 seconds. |
| Narration | Ten 24 kHz mono WAVs. Durations sum to 78.50 seconds. |
| Keyframes | Ten 1024×1024 JPEGs. |
| Shot masters | Ten HEVC files, 720×720, each longer than its WAV. |
| Timed alignment | Each assembled shot matches its WAV within a frame. |
| Finals | Both exist, non-empty, 81.50 seconds, at the two frame sizes above. |
| Score | `outputs/music/score.wav`, 148.77 seconds. The successful mix log has `music: true`. |
| `setpts` | Not in `build_shot_command`. The picture test asserts that. |
| Secrets in git | `.env`, `outputs/`, and media extensions are gitignored. They are not in any commit. `logs/runs.jsonl` is tracked on purpose and contains no API key. |
| Tests | Offline. |

Still open, and not claimed as done:

- A second three-person listen of the 78.50-second narration. Pronunciation was the gap the first three listeners heard.
- A three-person watch of both finished films.
- Wan 2.2 and ACE-Step remain optional Kaggle scripts. They are not required to rebuild the local films.
- `music.status` in the storyboard is `not_generated` even though assembly uses `outputs/music/score.wav`. The status field does not select the file.

Reproducing the delivered cut, once the WAVs, keyframes, Raphael masters, and score are on disk:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pipeline validate
python -m pipeline run --stage assemble
```

`python -m pipeline run` with no stage conforms shots and then assembles. Use `--stage assemble` when the Raphael masters must stay where they are.
