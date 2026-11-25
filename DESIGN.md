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

The picture is cinematic and realistic. Light is warm and late in the day outdoors, and warm electric light indoors. The place is an everyday urban Ethiopian residential neighbourhood: painted plaster and concrete walls, a metal compound gate, a paved or cobblestone lane, and a cozy living room with ordinary furniture. Clothing is everyday urban clothes. The camera barely moves, the way a patient documentary camera would.

The pictures do not use a rural village, a mud hut, or a caricature of Ethiopian life. Those exclusions are stored in `style_block.negative_prompt` as well as in the look itself.

The narration is one adult voice remembering, in Amharic, using the prebuilt Gemini voice `Kore`. The speaking style is warm and unhurried. That instruction is stored separately from the narration text so the approved words are not rewritten to direct the actor.

Music, when it is made, should be an original instrumental that stays under the voice. No vocals.

## Characters

These are fictionalized visual descriptions for image generation. They are not portraits of the real family. The brother's age is not stated as a number. The other ages below are appearance ranges for the pictures, not claimed facts about the real people.

| Id | Who | What the pictures show |
| --- | --- | --- |
| `brother` | The younger brother | A primary-school-age Ethiopian boy in everyday urban clothes: a faded mustard t-shirt, cuffed jeans, and worn sneakers. |
| `mother` | The mother | An Ethiopian woman in her late 30s, in a casual dress and a light cardigan, serving traditional drinks in ordinary glasses and cups. The drink is never given a specific name. |
| `customer` | A regular customer | An Ethiopian man in his 40s, in a casual jacket and a collared shirt, seated outside with his drink and a cigarette. The habit looks ordinary and unappealing. |
| `neighbour_wife` | One of the neighbours | A kind woman in her 60s, in a neat everyday coat, with a light gabi over normal clothes. |
| `neighbour_husband` | Her husband | A kind man in his 60s, in a neat sweater. They are a married couple the family already knew, walking the residential street at dusk. |

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

- **Status:** Not run.
- **Audience:** At least 3 people from the intended audience (families, peers, or young adults).
- **Material:** Amharic narration over a black screen, produced with `python -m pipeline radio-cut`.
- **Listen for:** Pronunciation of the proverb, whether the voice feels respectful, whether any line is hard to follow, and whether the total length feels like a short film rather than a lecture.
- **Record:** Date, who was present (first names or roles only), what they understood the message to be, and any line they asked to hear again.
- **Results:** Pending.

### User Test #2 — Near-Final Cut

- **Status:** Not run.
- **Audience:** At least 3 people from the intended audience. They may include people from Test #1.
- **Material:** Near-final picture, narration, music, English subtitles, and the AI disclosure card, in both 9:16 and 16:9 if both exports exist.
- **Watch for:** Whether the brother, mother, customer, and neighbours stay recognizable; whether the smoking moment feels unsafe or glamorous; whether the neighbours' intervention is clear without dialogue.
- **Record:** Date, who was present, which shot they questioned, and whether the ending proverb landed.
- **Results:** Pending.

A problem found in either test is fixed in the storyboard and regenerated for that shot only. The narration text changes only with explicit approval.
