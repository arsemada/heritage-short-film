# Design

Creative direction for የሚጠብቅ ጎረቤት (The Neighbour Who Protects).

`storyboard.json` is the production source of truth. This document explains the choices behind it. The approved narration in `STORY.md` is not rewritten here.

## Audience and platform

The film is for urban Ethiopian families, peers, and young adults.

People will watch it in two places:

- On a phone, in a vertical 9:16 frame.
- On a desktop or YouTube, in a horizontal 16:9 frame.

Every keyframe keeps the subject in the center, with room above and below, so both crops still show the person who matters in that shot.

## Emotional intent

The feeling of the film is warmth, everyday urban nostalgia, gentle childhood humor, and gratitude for community care.

The closing proverb carries that gratitude:

**«ሳይቃጠል በቅጠል።»**

The humor is the awkwardness of a child copying an adult and immediately coughing. It is not a joke about the child, and it is not an attractive picture of smoking. The last movement is quiet relief: a mother who is saddened, neighbours who did not walk past, and a child who never tried a cigarette again.

## Look and sound

The picture is candid 35mm documentary photography. Light moves from a warm afternoon into twilight. The place is an everyday urban Ethiopian neighborhood traditional drink house (tella bet): woven wall covering, worn plaster, wooden benches, plastic stools, and tall glasses of an unnamed cloudy amber-brown drink. Clothing is locked per character. The camera barely moves.

The pictures are not a luxury bar, a cartoon, or a caricature. Those exclusions are stored in `style_block.negative_prompt`.

The narration is one adult voice remembering, in Amharic, using the prebuilt Gemini voice `Kore`. The speaking style is warm and unhurried. That instruction is stored separately from the narration text so the approved words are not rewritten to direct the actor.

Music, when it is made, should be an original instrumental that stays under the voice. No vocals.

## Characters

These are fictionalized visual descriptions for image generation. The younger brother is a fictionalized 10–12-year-old whose look is inspired by a private family reference. That photograph is not in the repository. The other ages below are appearance ranges for the pictures, not claimed facts about real people. The exact sentences live in `storyboard.json` and are copied unchanged into each keyframe prompt.

| Id | Who | What the pictures show |
| --- | --- | --- |
| `young_brother` | The younger brother | A 10-to-12-year-old Ethiopian boy, short curly black hair, navy v-neck sweater over a light-blue collared shirt, dark trousers, worn sneakers. The same outfit in every shot. |
| `mother` | The mother | An Ethiopian woman in her late 30s, patterned headscarf, coral-red zip jacket, dark floral skirt, small traditional necklace. |
| `smoker_customer` | A regular customer | An Ethiopian man in his late 30s, short curly hair and a light beard, faded blue sweatshirt and jeans, seated with a drink and a cigarette. |
| `elderly_neighbors` | The neighbouring couple | A husband in his 60s in an olive-brown overcoat with a wooden walking stick, and his wife in a dark patterned dress and light shawl. |

No names are used. No dialogue is invented. The pictures show concern, a cough, and a conversation. They do not put words in anyone's mouth.

## Smoking on screen

The cigarette is part of the memory, so it cannot disappear. It also cannot be taught or admired.

- The customer smokes in the background of ordinary life, not as a pose.
- The boy notices a small discarded cigarette on the ground.
- His imitation is a clumsy foot against the wall, then a cough. No lighter, no flame, and no successful inhalation.
- Shot 07 is uncomfortable to watch. That discomfort is the point.

## Prototype and test plan

Neither test has been run. Fill the result lines after real viewers have watched. Do not invent their reactions.

### User Test #1 — Radio Cut

- **Status:** Completed on 25 November 2026.
- **Audience:** 3 listeners. Names are not recorded. They are listed as Listener 1, Listener 2, and Listener 3.
- **Material:** `outputs/radio_cut.mp4`. Amharic narration over a black 9:16 frame. Spoken duration 86.58 seconds.
- **Listen for:** Pronunciation of the proverb, whether the voice feels respectful, whether any line is hard to follow, and whether the total length feels like a short film rather than a lecture.

Listener 1: The 86-second pace is just right. The story is easy to visualize without pictures and feels cozy, like a morning radio ትረካ. The proverb «ሳይቃጠል በቅጠል» landed strongly. They also heard slight voice and prosody shifts between clips, and a few mispronounced Amharic words.

Listener 2: The pace is just right. The story is clear and the ending message is strong. They noticed occasional Amharic mispronunciation.

Listener 3: Overall good, with just-right pacing and a strong ending message. A couple of words had minor Amharic pronunciation quirks.

**Changes made after the test:**

- `meta.tts_style_instruction` now asks for one consistent Addis Ababa radio voice, the same pitch and pace on every clip, and pauses at the commas and full stops already in the line. That value is part of every narration fingerprint, so the next narration run regenerates all 10 shots. That is the cache doing what it should.
- Shot 10's spoken proverb is now `ሳይቃጠል በቅጠል።` The written proverb in `STORY.md` still has the guillemets. They were removed from the spoken text so the voice does not treat «» as something to pronounce. The ten `narration_am` lines are unchanged.
- Extra commas were not inserted into those lines. The lines already contain Ethiopian commas and full stops, and the new style instruction tells the voice to pause there. Adding commas would rewrite the approved narration. If the next listen still shows mispronunciation, that is a separate approved edit.
- The end card plan is 3 seconds. The spoken narration is 86.58 seconds, so a 3-second card keeps the finished film inside 90 seconds.

The new voice has not been generated yet. These notes describe the change, not a second listening test.

### User Test #2 — Near-Final Cut

- **Status:** Not run.
- **Audience:** At least 3 people from the intended audience. They may include people from Test #1.
- **Material:** Near-final picture, narration, music, English subtitles, and the AI disclosure card, in both 9:16 and 16:9 if both exports exist.
- **Watch for:** Whether the brother, mother, customer, and neighbours stay recognizable; whether the smoking moment feels unsafe or glamorous; whether the neighbours' intervention is clear without dialogue.
- **Record:** Date, who was present, which shot they questioned, and whether the ending proverb landed.
- **Results:** Pending.

A problem found in either test is fixed in the storyboard and regenerated for that shot only. The narration text changes only with explicit approval.
