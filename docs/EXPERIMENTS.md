# Experiments

Rows are added after a real run or a real listening session. A planned change is labeled as a hypothesis until the new audio exists.

## Narration, 25 November 2026

| Item | Record |
| --- | --- |
| Model | `gemini-3.8-flash-tts` |
| Voice | Prebuilt `Kore` |
| Input | Each shot's approved `narration_am`. Shot 10 also spoke `«ሳይቃጠል በቅጠል።»`. Style was a separate field: warm, unhurried Ethiopian storytelling. |
| Output | `outputs/narration/shot_01.wav` through `shot_10.wav` |
| Measured speech | 86.58 seconds. Inside the 60–90 second target. |
| Cache | A later run reused shots 01–09 and generated only shot 10, which had been missing. |
| Listeners | User Test #1, three people, black-screen radio cut. Pace and ending landed. Pronunciation and consistency did not. |

Per-shot durations from `logs/runs.jsonl`: 6.90, 13.26, 6.18, 8.62, 8.18, 7.10, 6.24, 9.90, 10.11, 10.09 seconds.

The API response did not include a token count or a price. No cost is invented here.

## Hypothesis, not yet regenerated

Tightening `tts_style_instruction` for one consistent Addis Ababa Amharic radio prosody, removing the «» guillemets around ሳይቃጠል በቅጠል።, and pausing at the punctuation already in the dense clauses will reduce voice drift and mispronunciation.

What changed in `storyboard.json` on 25 November 2026:

- The style instruction was rewritten. Because it is hashed into every shot, the next `python -m pipeline run --stage narration` will call Gemini for all 10 shots.
- The spoken proverb no longer includes «». The approved narration lines were not rewritten, and no new commas were inserted into them.

The restyle was generated after this note. Measured speech for that set is 78.50 seconds: 5.92, 10.37, 5.19, 7.74, 7.00, 5.91, 6.20, 9.06, 9.86, 11.25. The approved Amharic lines were still not rewritten.

## Images

On 25 November 2026, `python -m pipeline run --stage keyframes` returned HTTP 400 for shot 01 before any JPEG was saved. A direct comparison found the cause. The same short prompt with `steps` and `seed` was rejected: `Additional or unevaluated properties '/seed'`. The same prompt and `steps` without `seed` returned HTTP 200 and a JPEG. The model page curl example still shows `seed`, but the live REST schema for `@cf/black-forest-labs/flux-1-schnell` accepts only `prompt` and `steps`.

The provider now sends those two fields for FLUX.1 [schnell]. The storyboard seed stays in the cache fingerprint, so changing it still misses the cache, but Cloudflare chooses the image seed. The successful check used the prompt `a painted plaster wall` and was not written to `outputs/`. A later keyframe run did save `outputs/keyframes/shot_01.jpg` from the previous urban prompt. That JPEG does not match the drink-house redesign below.

That model page does not list a negative-prompt field, so the storyboard avoid-list is appended to the prompt as `Avoid: ...`. FLUX.2 [dev] is still refused. FLUX.2 [klein] 4B is the exception in the next section.

## Drink house and locked characters

On 25 November 2026 the storyboard look, character descriptions, and all ten `image_prompt` values were rewritten from a visual-reference review. The approved Amharic lines were not changed.

`@cf/black-forest-labs/flux-2-klein-4b` is listed on Cloudflare Workers AI. Its REST input is multipart, and it accepts reference images as `input_image_0` through `input_image_3`. There is no field named `image` or `reference_images`. Each reference must be smaller than 512×512. `steps` is fixed at 4.

The pipeline now prepends each `characters_present` description verbatim. Because this storyboard defines `young_brother`, every keyframe uses Klein so the drink house stays one photographic style. Shots that include him also attach `outputs/references/young_brother_ref.png` as `input_image_0`. That PNG was generated on 25 November 2026 at 480×480. It is a fictional portrait, not a family photograph. The ten film keyframes were generated after this change.

## Second keyframe pass

On 25 November 2026, after looking at those ten JPEGs, only shots 04, 05, 06, 07, 09, and 10 changed. Shots 01, 02, 03, and 08 kept the same `image_prompt` and `seed`. Their keyframe fingerprints stay the same, so the SHA-256 cache still points at the JPEGs already saved.

What the six edits are for:

- Shot 04 is a tight close-up of the brother's face, watching someone off-camera. `smoker_customer` was removed from that shot's `characters_present` so his description is not pasted into the portrait.
- Shot 05 is a dusk insert of the cigarette stub beside the sneakers. Its prompt forbids cups, glasses, drinks, and beverages. The shared style line about tall glass tumblers is left off that shot's composed prompt, and off shot 09, which also forbids cups. Shots 01, 02, 03, and 08 still receive the full style line.
- Shot 06 asks for a mid-stride glance over the shoulder.
- Shot 07 keeps the wall pose and asks for one foot on the ground and one sole on the wall. Its seed moved from 1007 to 1008 so the cache misses and the leg can be drawn again.
- Shot 09 keeps the indoor correction and states that both pairs of hands are empty.
- Shot 10 is a new neighborhood twilight wide shot. Its seed moved from 1010 to 1020.

Klein still does not receive `seed` in the request. The new numbers only change the cache key, so the next keyframe run asks for a new picture. The same seed field is also in the narration fingerprint, so a later `run --stage narration` would call Gemini again for shots 07 and 10. The WAVs already on disk are left in place until that command is run.

## Shot 05 and shot 07 again

After the second keyframe set, only shots 05 and 07 were rewritten. Every other shot kept its `image_prompt` and `seed`, so those keyframe fingerprints did not move.

Shot 05 is now a medium close-up at dusk: the brother crouches and reaches toward the cigarette stub beside his sneakers. The prompt still forbids cups, glasses, and drinks, so the shared tumbler line stays off that composed prompt. Its seed is still 1005. Shot 07 returns to the earlier wall pose, one foot back against the wall, coughing, and its seed stays 1008. Both prompts changed. Those two keyframes were regenerated. The other eight JPEGs stayed cached.

## Iterations that reached a file

1. First Gemini narration, voice Kore. Ten WAVs. Measured speech 86.58 seconds. Three listeners heard the radio cut. Pace worked. Pronunciation drifted.
2. Style instruction rewritten and the proverb guillemets removed. Cache missed. Second narration measured 78.50 seconds. The Amharic sentences were not edited.
3. Gemini HTTP 429. The SDK slept silently. Pipeline retries now wait on 429 and leave finished shots cached.
4. Cloudflare FLUX.1 [schnell] rejected `seed` with HTTP 400. The same prompt with `steps` only returned a JPEG. The provider stopped sending `seed`.
5. Drink-house prompts and locked character descriptions. Klein 4B for every keyframe in this storyboard, with `young_brother_ref.png` on the brother shots.
6. Second keyframe pass. Shots 04, 05, 06, 07, 09, and 10 changed. Shots 01, 02, 03, and 08 kept their hashes.
7. Third keyframe pass. Only shots 05 and 07 changed. The other fingerprints stayed put, and those two JPEGs were regenerated.
8. Ken Burns shots matched each WAV. A later run with the same fingerprint printed `cached` and did not rewrite the MP4s.
9. Square masters center-cropped into 9:16 and 16:9 cut people off, and captions rendered huge because libass scaled a 288-line font. Assembly now pads the square and sizes captions in the real frame.
10. Motion. Wan 2.2 was not run on this PC (no CUDA). The Kaggle T4 session ran out of memory and time. The film's motion remains Ken Burns. An external clip dropped at `outputs/shots/wan/shot_XX.mp4` is conformed instead, and that source file is not replaced.
11. Music. The storyboard first named a 72 BPM score. The file actually dropped is `outputs/music/score.mp3`, converted to `outputs/music/score.wav` (2 minutes 28.77 seconds, 48 kHz stereo). The storyboard tempo is now 90 BPM for that chosen underscore. Assembly ducks it under the voice. A first mix failed because `loudnorm` was a second filter on a complex graph. The successful mix is the one in the final MP4s.
