# The Neighbour Who Protects

Technical report, 26 November 2026.

## 1. Executive summary

የሚጠብቅ ጎረቤት is an 81.50-second Amharic short film in two aspect ratios. A structured `storyboard.json` is the only production contract. The pipeline does not rewrite the approved narration, does not invent names or dialogue, and does not clone a real person's face or voice.

The films on disk are `outputs/final_9x16.mp4` (1080×1920, 14,761,993 bytes) and `outputs/final_16x9.mp4` (1920×1080, 15,068,700 bytes). ffprobe measures both at 81.50 seconds. That is 78.50 seconds of speech, voice Kore, model `gemini-3.8-flash-tts`, plus a 3-second end card. English subtitles are burned in. A 90 BPM instrumental underscore is ducked under the voice. Recorded cost in this repository is $0.00.

Wan 2.2 image-to-video did not produce a clip here. This PC has no CUDA GPU. A Kaggle Tesla T4 session ran out of memory at 14.56 GiB, then hit a `Draft Session Error` at about 5.5 minutes per shot. The delivered motion is ten Raphael clips, stated as MiniMax H3 Turbo, probed at 720×720 and trimmed to each narration line. FFmpeg Ken Burns remains the offline fallback from the keyframes.

## 2. Creative vision and the listen

The story is one childhood memory. In an urban Ethiopian neighbourhood drink house (tella bet), a boy watches a customer smoke, copies the stance with a discarded cigarette, and coughs. Neighbours who could have walked past stop him and tell his mother. He never tries again. The last line is the proverb ሳይቃጠል በቅጠል። English on screen gives a plain gloss: "Before it burns, while it is still a leaf."

The place is worn plaster, woven wall covering, wooden benches, plastic stools, and tall glasses of an unnamed cloudy drink. It is not a luxury bar. Clothing is locked per character in `storyboard.json` and copied unchanged into each keyframe prompt. Smoking is awkward and unsuccessful. Shot 07 does not describe a lesson in how to smoke. The ten-shot arc, from the doorway at afternoon to the lane at twilight, is in `DESIGN.md`.

Three listeners heard `outputs/radio_cut.mp4` on 25 November 2026. That cut was the first narration, 86.58 seconds, on a black 9:16 frame. They did not see pictures or subtitles, and they did not hear the score.

| Listener | What was recorded |
| --- | --- |
| 1 | Pace just right. Easy to picture, like a morning radio ትረካ. The proverb landed. Slight voice shifts between clips, and a few mispronounced Amharic words. |
| 2 | Pace just right. The story and the ending message were clear. Occasional Amharic mispronunciation. |
| 3 | Pace just right. Ending message strong. A couple of words had minor pronunciation quirks. |

That listen changed the style instruction to one consistent Addis Ababa radio voice, and removed the guillemets from the spoken proverb so the voice would not treat «» as a word. The ten `narration_am` lines were not rewritten. The restyle measures 78.50 seconds: 5.92, 10.37, 5.19, 7.74, 7.00, 5.91, 6.20, 9.06, 9.86, 11.25. A second three-person listen of that restyle is not recorded. A three-person watch of the finished pictures is not recorded.

Later picture work, from watching the exports rather than from those three listeners: pad the square instead of cropping people, size captions in the real frame, mix the dropped underscore at the storyboard's 90 BPM, and replace repeated short clips with longer ones trimmed to each line.

## 3. Pipeline

`python -m pipeline` validates the storyboard, then runs one stage or, with no `--stage`, conforms shots and assembles both films. SHA-256 fingerprints in `outputs/cache/manifest.json` skip work whose inputs have not changed. `--scene 04` limits a stage to shot 04.

1. Narration sends each approved line to Gemini. The style instruction is a separate field. The fingerprint covers the line, the style, the voice, the model, and the seed.
2. Keyframes prepend each present character description verbatim. This storyboard defines `young_brother`, so every still goes to FLUX.2 [klein] 4B. Brother shots also send `outputs/references/young_brother_ref.png`, a generated 480×480 portrait. The ten JPEGs are 1024×1024. Cloudflare does not receive the storyboard seed. Sending `seed` to FLUX.1 [schnell] returned HTTP 400.
3. Shots use a clip already at `outputs/shots/wan/shot_XX.mp4` or `kaggle_outputs/shots/shot_XX.mp4`. A shorter clip loops to the WAV. A longer clip is trimmed with `-t` at normal speed. Otherwise FFmpeg Ken Burns moves the keyframe. That fallback is what lets `python -m pipeline run` rebuild a picture with no GPU and no Raphael account.
4. Music is the file `outputs/music/score.wav`. There is no music stage and no ACE-Step call inside `python -m pipeline run`. A missing file becomes a quiet local drone.
5. Assembly trims each master to its WAV, joins the 3-second disclosure card, burns ASS captions whose PlayRes matches the export, ducks the score, and writes both aspect ratios.

The duration sync is `build_shot_command` in `pipeline/shots.py`, called by `pipeline/assemble.py` for every shot before the concat. `setpts` is not in that command. Slowing a slightly longer clip was tried and removed. The current sources are longer than the lines, so the tail is cut and the motion stays at 1×.

The score mix is one complex filter graph: both streams to 24 kHz mono, score volume 0.35, `sidechaincompress` against the voice, then `loudnorm=I=-14:TP=-1.5:LRA=11` on the mixed pad. The square picture is padded into 1080×1920 and 1920×1080. Black bars are intentional.

The clips in the delivered films were copied onto `outputs/shots/shot_XX.mp4` themselves. `python -m pipeline run --stage assemble` is the command that rebuilds this cut. A shots-stage cache miss would replace those files with Ken Burns. Details are in `docs/ARCHITECTURE.md`.

## 4. Experiments and measured results

`docs/EXPERIMENTS.md` has the run log. The measurements that define the delivered films:

| Item | Result |
| --- | --- |
| First narration | 86.58 seconds. Three listeners. Pace and the proverb worked. Pronunciation drifted. |
| Restyled narration | 78.50 seconds. Lines unchanged. These are the WAVs in the films. |
| Keyframes | Ten Klein JPEGs at 1024×1024. Shots 05 and 07 were the last regenerations. The others stayed cached when their prompts did not change. |
| Wan 2.2 | No MP4. This PC has no CUDA GPU. The T4 session did not leave a clip. |
| First moving-picture join | Clips of about 3.75 seconds against lines of 5–11 seconds. Looping them matched the clock and repeated the motion. Rejected. |
| Delivered masters | HEVC, 720×720. 5.97, 11.01, 6.01, 8.01, 7.01, 6.01, 7.01, 10.01, 10.01, 12.00 seconds. Each is longer than its WAV. |
| Timed shots after `-t` | Match the WAVs within a frame. |
| Score | 148.77 seconds, 48 kHz stereo, from `score.mp3`. Storyboard tempo 90 BPM. The earlier brief was 72 BPM. |
| Both finals | 81.50 seconds. H.264 video, AAC audio at 192 kb/s. |

## 5. Failures and the pivot

The notes are in `docs/FAILURES.md`. In order:

1. Gemini HTTP 429. The SDK slept silently. Pipeline retries are now visible, and a finished WAV is not requested again.
2. FFmpeg 9.1 was installed and invisible to an old terminal. The pipeline finds the WinGet shim. A Windows drive colon in the end-card filter was escaped.
3. This PC cannot load a 5B video model. `notebooks/kaggle_wan2_batch.py` exits with `This script needs a CUDA GPU.`
4. On a Kaggle Tesla T4, Wan failed an `ftfy` import, then a CUDA out-of-memory error with 14.56 GiB allocated on a 14.56 GiB card while `Wan-AI/Wan2.2-TI2V-5B-Diffusers` and UMT5 were loaded together. The script now uses `enable_sequential_cpu_offload()` and `vae.enable_tiling()`.
5. The session record after that mitigation: about 31.4 GB of checkpoint download and reconstruction, about 5.5 minutes per shot, about 55 minutes for ten shots, then a Kaggle `Draft Session Error` and a frozen worker. No Wan MP4 was recovered.
6. Motion for the delivered films was generated in the browser as Raphael / MiniMax H3 Turbo clips and cached at `outputs/shots/shot_01.mp4` through `shot_10.mp4`. Provenance in `logs/runs.jsonl` uses the ffprobe measurements, not a 480p / 4-second / 16:9 label. Ken Burns remains the offline fallback when the shots stage has no external clip.
7. `loudnorm` as `-af` on the ducked mix failed with `Error opening output files: Invalid argument`. It now sits inside the complex graph. Short clips that ran ahead of the Amharic were replaced by longer clips, trimmed with `-t`. `setpts` is not used.

## 6. Cost, ethics, and disclosure

No invoice is in this repository. Gemini and Cloudflare ran on free tiers. FFmpeg ran locally. The score and the Raphael clips were brought in as files. This repo has no MiniMax key and no Raphael receipt. If a browser credit balance moved when the longer clips were generated, that charge is not recorded here and is not invented in `docs/COSTS.md`. Total recorded: **$0.00**.

Three disclosures travel with the film, as set out in `ETHICS.md`:

- The 3-second end card names Gemini TTS voice Kore, Cloudflare Workers AI, and states that the characters are fictionalized.
- The MP4 comment repeats that the narration is AI-generated and that the voice is the prebuilt voice Kore.
- `logs/runs.jsonl` records models, seeds, and measured durations. It does not record API keys.

No family photograph and no family voice are in the repository. The brother reference PNG is a generated portrait. Smoking is shown as a failed imitation.

## 7. Verification and what is still open

Checked on 26 November 2026 against the files and the code:

| Check | Result |
| --- | --- |
| Storyboard | `storyboard.json` plans 80.0 seconds including the 3-second end card. Assembly follows the measured 78.50 seconds of speech, so the films are 81.50 seconds. |
| Narration WAVs | Ten files, durations sum to 78.50 seconds. |
| Keyframes | Ten 1024×1024 JPEGs. |
| Shot masters | Ten files, 720×720, each longer than its WAV. |
| Timed alignment | Each assembled shot matches its WAV within a frame. |
| Finals | Both exist, non-empty, 81.50 seconds, 1080×1920 and 1920×1080. |
| Score | `outputs/music/score.wav` present, 148.77 seconds. The mix log shows `music: true`. |
| `setpts` | Absent from `build_shot_command`. The picture test asserts that. |
| Secrets | `.env` is gitignored. The run log has no API key. |
| Tests | Offline. They do not call Gemini, Cloudflare, or FFmpeg. |

Still open:

- A second three-person listen of the 78.50-second narration. Amharic pronunciation was the gap the first three listeners heard.
- A three-person watch of both finished films, for whether the brother, mother, customer, and neighbours stay recognizable and whether shot 07 feels unsafe rather than glamorous.
- Wan 2.2 and ACE-Step remain optional Kaggle scripts. They are not required to rebuild the local films.
- `music.status` in the storyboard is `not_generated` even though `score.wav` is the file assembly uses. The status field does not select the file. `load_score` looks at the path.

Reproducing the delivered cut, once the WAVs, keyframes, Raphael masters, and `score.wav` are on disk:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pipeline validate
python -m pipeline run --stage assemble
```

`python -m pipeline run` with no stage also conforms shots and then assembles. It does not call Gemini or Cloudflare. Use `--stage assemble` when the Raphael masters must stay where they are.
