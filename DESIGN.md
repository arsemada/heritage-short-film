# Design

Creative direction for የሚጠብቅ ጎረቤት (The Neighbour Who Protects).

`storyboard.json` is the production source of truth. This document explains the choices behind it. The approved narration in `STORY.md` is not rewritten here. Characters are fictionalized. See `ETHICS.md`.

## Story premise

An adult remembers one childhood afternoon in Amharic. The younger brother watches a customer smoke, copies the stance with a discarded cigarette, and coughs. Neighbours who could have walked past stop him and tell his mother. He never tries again. The film ends on the proverb ሳይቃጠል በቅጠል። — before it burns, while it is still a leaf.

The feeling is warmth, everyday urban nostalgia, gentle awkward humor, and gratitude for community care. The humor is the failed imitation. It is not a joke about the child, and it is not an attractive picture of smoking.

No names, dialogue, or extra events are added. The brother's numeric age is not a story fact. The 10–12 range is the fictionalized look used for pictures.

## Cultural authenticity

The place is an everyday urban Ethiopian neighbourhood traditional drink house (tella bet), not a luxury bar and not a rural costume. `style_block.look` and `style_block.visual_style` lock woven wall covering, worn plaster, wooden benches, plastic stools, and tall glasses of an unnamed cloudy amber-brown drink. Clothing is locked per character in `storyboard.json` and copied unchanged into each keyframe prompt.

The narration stays in Amharic, voice `Kore`, model `gemini-3.8-flash-tts`. The speaking style is a separate storyboard field, so the approved words are not rewritten to direct the voice. English subtitles are burned into both exports from each shot's `subtitle_en`. On the 9:16 film they sit in the lower black bar. On the 16:9 film they wrap along the bottom of the center square. The square picture is padded, not cropped, so people are not cut off to fill the frame.

## Ten-shot visual arc

Light moves from a warm afternoon into twilight. The camera stays close to still.

| Shot | Size | What the picture is for |
| --- | --- | --- |
| 01 | wide | The drink-house doorway, before any person has to carry the story. |
| 02 | medium | The mother pouring for neighbours who come to drink and talk. |
| 03 | medium | A regular customer smoking while he drinks, as ordinary life, not a pose. |
| 04 | close-up | The brother watching, curious, before he has touched anything. |
| 05 | medium close-up | He crouches toward a discarded cigarette at dusk. |
| 06 | medium | He checks that nobody is watching and moves toward the wall. |
| 07 | medium | He copies the stance, one foot against the wall, and coughs. The attempt fails. |
| 08 | medium | An older neighbouring couple stop him. |
| 09 | medium | They bring him home. His mother is saddened and explains the harm. Both pairs of hands stay empty. |
| 10 | wide | Twilight in the lane. He never tried again. Protecting a child belongs to the community. The proverb is spoken here. |

Smoking stays on screen because it is part of the memory. Shot 07 is uncomfortable. There is no lighter, no flame, and no successful inhalation. The image prompt for that shot does not describe a lesson in how to smoke.

## Audio and pacing

Speech is one adult remembering. The style instruction asks for one consistent Addis Ababa radio voice, the same pitch and pace on every clip, and pauses at the commas and full stops already in the line. The restyled WAVs in `outputs/narration/` measure 78.50 seconds: 5.92, 10.37, 5.19, 7.74, 7.00, 5.91, 6.20, 9.06, 9.86, 11.25. A 3-second end card brings both films to 81.50 seconds.

The storyboard asks for a quiet original instrumental with no vocals. `music.tempo_bpm` is 90 and `music.key` is D major. Those are brief fields. The file actually mixed is `outputs/music/score.wav` (148.77 seconds, 48 kHz stereo), converted locally from `outputs/music/score.mp3`. The storyboard does not name instruments, so this document does not name them either. Assembly lowers that score, ducks it under the voice with `sidechaincompress`, and normalizes the mix to −14 LUFS inside one filter graph. The pipeline does not generate the score. If `score.wav` is missing, assembly uses a quiet local drone instead of calling another model.

## User testing summary (3 participants)

User Test #1 was completed on 25 November 2026. Three listeners, recorded as Listener 1, Listener 2, and Listener 3, heard `outputs/radio_cut.mp4`: Amharic narration over a black 9:16 frame, spoken duration 86.58 seconds. They did not see pictures, English subtitles, or a score. A second three-person watch of the finished films is not recorded. Their words below are the notes already in this file. They are not expanded.

**Listener 1.** The 86-second pace is just right. The story is easy to visualize without pictures and feels cozy, like a morning radio ትረካ. The proverb «ሳይቃጠል በቅጠል» landed strongly. They also heard slight voice and prosody shifts between clips, and a few mispronounced Amharic words.

**Listener 2.** The pace is just right. The story is clear and the ending message is strong. They noticed occasional Amharic mispronunciation.

**Listener 3.** Overall good, with just-right pacing and a strong ending message. A couple of words had minor Amharic pronunciation quirks.

Read against the questions that test can answer:

| Question | What the three listeners actually gave us |
| --- | --- |
| Emotional clarity | All three followed the story and the ending. Listener 1 could picture it without images and said the proverb landed. Listeners 2 and 3 called the ending message strong. |
| Subtitle readability | Not tested. The radio cut has no burned-in subtitles. |
| Audio balance and pacing | Pacing of the voice was "just right" for all three. There was no music to balance. They did flag pitch, pace, and pronunciation shifting between clips. |

**Changes made because of that listen:**

- `meta.tts_style_instruction` now asks for one consistent Addis Ababa radio voice, the same pitch and pace on every clip, and pauses at the punctuation already in the line. That field is inside every narration fingerprint, so the next narration run regenerated all 10 shots. Measured speech for that set is 78.50 seconds.
- Shot 10's spoken proverb is `ሳይቃጠል በቅጠል።` The written proverb in `STORY.md` still has the guillemets. They were removed from the spoken text so the voice does not treat «» as something to pronounce. The ten `narration_am` lines were not rewritten, and no commas were inserted into them.

A second three-person listen of the 78.50-second set is not recorded. Amharic pronunciation remains a known limit of `gemini-3.8-flash-tts` with the prebuilt voice Kore.

## Picture-cut refinements

These changes came from building and watching the picture, not from the three radio listeners.

- The first 9:16 and 16:9 exports center-cropped the square frame and scaled captions from libass's default 384×288 play resolution, so people were cut off and the type was huge. Assembly now pads the square into each aspect and burns an ASS file whose PlayRes matches the export.
- The score brief was first 72 BPM. The underscore that was dropped in and mixed is recorded at 90 BPM in `storyboard.json`. The mix ducks it under the voice.
- The first moving-picture cut used short clips and repeated them to fill each narration line. That repeat was rejected. The clips now in `outputs/shots/shot_01.mp4` through `shot_10.mp4` are user-supplied Raphael downloads, stated as MiniMax H3 Turbo. ffprobe measures them at 720×720, from 5.97 seconds to 12.00 seconds, each a little longer than its WAV.
- Those longer clips are not sped up with `setpts`. `build_shot_command` in `pipeline/shots.py` plays a longer source at normal speed and trims the tail with `-t` so the picture ends with the line. A source shorter than the line would still loop. Assembly calls that command for every shot before the concat. The timed clips match the WAVs, and both finals are 81.50 seconds.

User Test #2, a three-person watch of the near-final picture in both aspects, has not been run.
