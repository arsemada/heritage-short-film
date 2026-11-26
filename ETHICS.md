# Ethics

Rules for making this film without turning a private childhood memory into someone else's face, voice, or advertisement for smoking.

## Consent and likeness policy

Zero real photographs are committed to this repository, and no family voice is cloned.

The younger brother is a fictionalized boy of about 10–12. His face, short curly black hair, and outfit are visually inspired by a private family reference. Family consent for that inspiration is recorded here. The private photograph itself is not in the repository, is not a pipeline input, and must not be added later. The file `outputs/references/young_brother_ref.png`, when generated, is an AI picture of this fictional character. It is gitignored with the rest of `outputs/`.

The mother, the smoking customer, and the elderly neighbours are fictionalized types as well. Their descriptions lock clothes and age range so the pictures stay consistent. Those ranges are for the pictures. They are not claimed facts about real people.

Narration uses a standard prebuilt Gemini TTS voice, `Kore`. The pipeline does not call Gemini voice replication, voice design based on a family recording, or any other cloning feature. A real person's voice must not be substituted later without documented consent. That consent is not on file, and this project does not seek it for the deadline.

The story's facts stay inside `STORY.md`. The narration does not add names, dialogue, or extra events, and it does not name the drink. The pictures place the memory in a neighborhood traditional drink house (tella bet) and show an unnamed cloudy amber-brown drink. The brother's age is not spoken. The 10–12 range is the fictionalized look recorded above.

## Labelling and provenance

Three disclosures travel with the finished film:

1. **Platform disclosure.** When the film is posted, the platform's AI-content label is turned on.
2. **Visible end card.** The export ends on a card that says the film was made with AI, names the generation roles, and states that the characters are fictionalized. The card text lives in `storyboard.json` under `end_card`.
3. **Intact metadata.** Assembly writes a comment into the media file stating that the narration is AI-generated, that the voice is the prebuilt voice Kore, and that the characters are fictionalized. That comment is not stripped in later exports.

`logs/runs.jsonl` records models, seeds, and outcomes. It does not record API keys, account tokens, or private family details. The moving shots in the delivered films are logged as MiniMax H3 Turbo (Raphael AI), with the resolution and duration ffprobe measured. The visible end card names the narration voice and Cloudflare Workers AI for the pictures, and states that the characters are fictionalized.

## Cultural care

The home, the drink trade, and the neighbours are shown as an ordinary urban Ethiopian neighborhood drink house: worn plaster, woven wall covering, wooden benches, plastic stools, and tall glasses. They are not a luxury bar, a rural costume, or a caricature. Smoking is a harm the story warns against. The pictures of the cough are awkward and unappealing. They are not a lesson in how to smoke, and they are not a stylish image of a cigarette.

The proverb «ሳይቃጠል በቅጠል።» stays in Amharic. The English subtitle gives a plain gloss so a non-Amharic viewer can follow it. The gloss does not replace the proverb.

## Model licences

Checked again on 25 November 2026. Gemini narration and one FLUX.1 [schnell] keyframe have already been called. Hosted copies can change, so the model id in the request is the one that was approved.

| Component | Licence | What was checked | Use in this project |
| --- | --- | --- | --- |
| Gemini API, model `gemini-3.8-flash-tts` | Google Gemini API terms. This is a proprietary service, not an open-source licence. | [Speech generation guide](https://ai.google.dev/gemini-api/docs/speech-generation), which lists Amharic for this model and the prebuilt voice `Kore`. | Narration only. No voice cloning. |
| Cloudflare Workers AI hosting FLUX.1 [schnell] (`@cf/black-forest-labs/flux-1-schnell`) | FLUX.1 [schnell] is published by Black Forest Labs under Apache-2.0. Calls also follow Cloudflare's service terms. | Cloudflare's model page for `flux-1-schnell`. | Keyframes that do not include the younger brother. One shot was generated before this redesign. |
| Cloudflare Workers AI hosting FLUX.2 [klein] 4B (`@cf/black-forest-labs/flux-2-klein-4b`) | Apache-2.0 for the 4B model. Calls also follow Cloudflare's service terms. FLUX.2 [klein] 9B and FLUX.2 [dev] are different licences and are not approved. | Black Forest Labs' model card for `FLUX.2-klein-4B` states Apache-2.0. Cloudflare's 15 January 2026 changelog documents multipart input and `input_image_0` through `input_image_3`, each smaller than 512×512. | The generated brother reference, and every keyframe in a storyboard that defines `young_brother`. The reference is attached only on shots that include him. |
| Wan 2.2 | Apache-2.0 | `LICENSE.txt` in `Wan-Video/Wan2.2`. | Optional image-to-video script. Not run to a finished clip. |
| MiniMax H3 Turbo via Raphael | The browser tool's own terms. This repository has no MiniMax key and no receipt. The MP4s contain no model tag. | The files at `outputs/shots/shot_01.mp4` through `shot_10.mp4`, probed 26 November 2026. | The moving shots in the delivered films. Stated source: Raphael. FFmpeg Ken Burns remains the offline fallback when those files are absent. |
| ACE-Step 1.5 | MIT | `LICENSE` in `ace-step/ACE-Step-1.5` (copyright 2026 ACEStep). The older `ace-step/ACE-Step` repository is Apache-2.0 and is not the checkpoint this row approves. | Optional score script. The mixed file is `outputs/music/score.wav`, converted locally from `score.mp3`. The pipeline did not call ACE-Step. |
| FFmpeg | LGPL 2.1 or later for the core. GPL 2 or later when the build includes GPL parts such as libx264. | FFmpeg's published licensing. The radio-cut command uses libx264, so the installed build should be a GPL build. | Assembly, subtitles, still-image motion, and the radio cut. |

Generated media stays in `outputs/` and is gitignored. Secrets stay in `.env`, which is gitignored. `.env.example` has empty values only.
