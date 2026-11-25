# Ethics

Rules for making this film without turning a private childhood memory into someone else's face, voice, or advertisement for smoking.

## Consent and likeness policy

Zero real photographs, faces, or cloned family voices are used.

Every character is a fictionalized visual representation inspired by a childhood memory. Image prompts describe types of people and clothes. They do not describe a real relative, and no family photograph is a reference image.

Narration uses a standard prebuilt Gemini TTS voice, `Kore`. The pipeline does not call Gemini voice replication, voice design based on a family recording, or any other cloning feature. A real person's voice must not be substituted later without documented consent. That consent is not on file, and this project does not seek it for the deadline.

The story's facts stay inside `STORY.md`. The film does not invent the brother's age as a number, the kind of traditional drink, names, dialogue, or extra events.

## Labelling and provenance

Three disclosures travel with the finished film:

1. **Platform disclosure.** When the film is posted, the platform's AI-content label is turned on.
2. **Visible end card.** The export ends on a card that says the film was made with AI, names the generation roles, and states that the characters are fictionalized. The card text lives in `storyboard.json` under `end_card`.
3. **Intact metadata.** Assembly writes a comment into the media file stating that the narration is AI-generated, that the voice is the prebuilt voice Kore, and that the characters are fictionalized. That comment is not stripped in later exports.

`logs/runs.jsonl` records models, seeds, and outcomes. It does not record API keys, account tokens, or private family details.

## Cultural care

The home, the drink trade, and the neighbours are shown as ordinary urban Ethiopian life: a residential lane, a compound gate, a living room. They are not a rural costume and not a caricature. Smoking is a harm the story warns against. The pictures of the cough are awkward and unappealing. They are not a lesson in how to smoke, and they are not a stylish image of a cigarette.

The proverb «ሳይቃጠል በቅጠል።» stays in Amharic. The English subtitle gives a plain gloss so a non-Amharic viewer can follow it. The gloss does not replace the proverb.

## Model licences

Checked while building the offline pipeline. No model has been called yet. Confirm the exact checkpoint again before a paid or GPU run, because hosted copies can change.

| Component | Licence | What was checked | Use in this project |
| --- | --- | --- | --- |
| Gemini API, model `gemini-3.8-flash-tts` | Google Gemini API terms. This is a proprietary service, not an open-source licence. | [Speech generation guide](https://ai.google.dev/gemini-api/docs/speech-generation), which lists Amharic for this model and the prebuilt voice `Kore`. | Narration only. No voice cloning. |
| Cloudflare Workers AI hosting FLUX.1 [schnell] (`@cf/black-forest-labs/flux-1-schnell`) | FLUX.1 [schnell] is published by Black Forest Labs under Apache-2.0. Calls also follow Cloudflare's service terms. | Cloudflare's model page for `flux-1-schnell`. The Hugging Face licence file returned 401 during this check, so confirm the card in the Cloudflare account before the first image call. FLUX.2 [dev] is a different licence and is not approved by this row. | Planned keyframes. Not called yet. |
| Wan 2.2 | Apache-2.0 | `LICENSE.txt` in `Wan-Video/Wan2.2`. | Optional image-to-video. Not run. The deadline path is FFmpeg animation of stills. |
| ACE-Step 1.5 | MIT | `LICENSE` in `ace-step/ACE-Step-1.5` (copyright 2026 ACEStep). The older `ace-step/ACE-Step` repository is Apache-2.0 and is not the checkpoint this row approves. | Planned original instrumental. Not generated. |
| FFmpeg | LGPL 2.1 or later for the core. GPL 2 or later when the build includes GPL parts such as libx264. | FFmpeg's published licensing. The radio-cut command uses libx264, so the installed build should be a GPL build. | Assembly, subtitles, still-image motion, and the radio cut. |

Generated media stays in `outputs/` and is gitignored. Secrets stay in `.env`, which is gitignored. `.env.example` has empty values only.
