# Experiments

Each row is a run or a listen that produced a file or a rejected file. A change that only exists in the storyboard is labeled as such.

## 1. First Amharic narration

| Item | Record |
| --- | --- |
| When | 25 November 2026 |
| Model | `gemini-3.8-flash-tts`, prebuilt voice Kore |
| Input | Each shot's approved `narration_am`. Shot 10 also spoke `«ሳይቃጠል በቅጠል።»`. Style was a separate field. |
| Output | `outputs/narration/shot_01.wav` through `shot_10.wav` |
| Measured speech | 86.58 seconds. Inside the 60–90 second target. Per shot: 6.90, 13.26, 6.18, 8.62, 8.18, 7.10, 6.24, 9.90, 10.11, 10.09. |
| Cache | A later run reused shots 01–09 and generated only shot 10, which had been missing. |
| Listen | User Test #1, three people, black-screen radio cut. Pace and ending landed. Pronunciation and consistency did not. |

The API response did not include a token count or a price.

## 2. Prosody restyle

`tts_style_instruction` was rewritten for one consistent Addis Ababa radio voice, and the spoken proverb lost its guillemets. The style field is hashed, so the cache missed for all 10 shots. The second set measures 78.50 seconds: 5.92, 10.37, 5.19, 7.74, 7.00, 5.91, 6.20, 9.06, 9.86, 11.25. The approved Amharic sentences were not edited, and no commas were inserted. These WAVs are the ones in the finals. A second three-person listen is not recorded.

## 3. Visible 429 retries

Gemini HTTP 429 made the SDK sleep with no pipeline log. The client retry count is now 1. Pipeline waits are 15, 20, 30, 45, and 60 seconds, six attempts, 12 seconds between live requests. Finished WAVs stay cached, so a failed shot does not redo the shots that already wrote a file.

## 4. FLUX.1 [schnell] rejects `seed`

`python -m pipeline run --stage keyframes` returned HTTP 400 for shot 01 before any JPEG was saved. The same short prompt with `steps` and `seed` was rejected: `Additional or unevaluated properties '/seed'`. The same prompt and `steps` without `seed` returned HTTP 200 and a JPEG. The provider now sends `prompt` and `steps` only. The storyboard seed stays in the fingerprint. The avoid list is appended as `Avoid: ...` because that model has no negative field.

## 5. Drink house, locked characters, Klein 4B

On 25 November 2026 the look, the character descriptions, and all ten `image_prompt` values were rewritten toward an urban tella bet. The approved Amharic lines were not changed.

`@cf/black-forest-labs/flux-2-klein-4b` takes multipart input. Reference images are `input_image_0` through `input_image_3`, each under 512×512. `steps` is fixed at 4. Because this storyboard defines `young_brother`, every keyframe uses Klein. Shots that include him also attach `outputs/references/young_brother_ref.png` as image 0. That PNG is a generated 480×480 portrait, not a family photograph. The ten film keyframes after this pass are 1024×1024 JPEGs.

## 6. Second keyframe pass

After looking at those ten JPEGs, shots 04, 05, 06, 07, 09, and 10 changed. Shots 01, 02, 03, and 08 kept the same `image_prompt` and `seed`, so their fingerprints stayed and the cache kept those JPEGs.

Shot 04 became a close-up of the brother, and `smoker_customer` was removed from that shot so his description is not pasted into the portrait. Shot 05 was a dusk insert of the cigarette stub, with cups forbidden, so the shared tumbler sentence is left off that prompt. Shot 06 asks for a mid-stride glance. Shot 07's seed moved from 1007 to 1008. Shot 09 states that both pairs of hands are empty. Shot 10's seed moved from 1010 to 1020. Klein still does not receive `seed`. The new numbers only miss the cache. The same seed is in the narration fingerprint, so a later narration run would call Gemini again for shots 07 and 10. Those WAVs were left in place.

## 7. Third keyframe pass

Only shots 05 and 07 were rewritten. Shot 05 is a medium close-up: the brother crouches and reaches toward the stub. Shot 07 returns to the wall pose, one foot back, coughing. Both prompts changed and those two JPEGs were regenerated. The other eight stayed cached.

## 8. Ken Burns matched to the WAVs

With no Wan file on disk, `run --stage shots` wrote ten 1080×1080 H.264 masters whose durations match the 78.50-second narration. A later run with the same fingerprint printed `cached` and did not rewrite the MP4s. Those lines are still in `logs/runs.jsonl` as `ffmpeg-ken-burns`. They describe that run. They do not describe the files in the folder now.

## 9. Captions and crops

Square masters were center-cropped into 9:16 and 16:9, which cut people off. Captions rendered huge because libass scaled a font written for a 288-line play resolution. Assembly now pads the square into each aspect and writes an ASS file whose PlayRes equals the export. Vertical type sits in the lower bar. Horizontal margins are 280 so a long English line wraps inside the center square.

## 10. Wan on this PC, then on a T4

`notebooks/kaggle_wan2_batch.py` on this machine stopped with `This script needs a CUDA GPU.` On a Kaggle Tesla T4 the install hit an `ftfy` import error, then a CUDA out-of-memory error at 14.56 GiB while loading `Wan-AI/Wan2.2-TI2V-5B-Diffusers` with UMT5. Sequential CPU offload and VAE tiling are in the script. The container still ran about 5.5 minutes per shot and hit draft-session memory and disk pressure. No Wan MP4 is in `outputs/shots/`.

## 11. Score tempo: 72 BPM brief, then the 90 BPM file

The storyboard first named a 72 BPM score. The file that was dropped is `outputs/music/score.mp3`, converted with local FFmpeg to `outputs/music/score.wav` (148.77 seconds, 48 kHz stereo, PCM). `music.tempo_bpm` is now 90 for that chosen underscore. The 90 is the storyboard field, not a BPM detector reading of the WAV. The storyboard does not name instruments. `music.status` remains `not_generated` and `music.path` remains null. Assembly still finds the default `score.wav`, sets it to volume 0.35, and ducks it under the voice.

The first mix failed because `loudnorm` was `-af` on a complex graph. The successful mix puts `loudnorm` inside the same graph. That mix is in the final MP4s.

## 12. Duration sync: loop, then trim

Nine Raphael clips of about 3.75 seconds at 640×640 were concatenated against lines of 5–11 seconds, so the picture moved on early. Looping them to the WAV made the lengths match and made the motion repeat. That cut was rejected.

The replacement files, copied to `outputs/shots/shot_01.mp4` through `shot_10.mp4`, measure 720×720 and 5.97, 11.01, 6.01, 8.01, 7.01, 6.01, 7.01, 10.01, 10.01, and 12.00 seconds. Each is longer than its WAV. `setpts` slowing was removed so a slightly longer clip is not slowed and then cut. `-t` trims the tail at normal speed. The rebuild on 26 November 2026 wrote both finals at 81.50 seconds, and each timed clip matches its WAV within a frame.
