# Experiments

No model has been called.

The narration provider is written against the Gemini speech-generation guide checked on 25 November 2026:

- Model: `gemini-3.8-flash-tts`
- Voice: prebuilt `Kore`
- Amharic is listed as supported for this model
- Transcript and speaking style are separate fields
- Unary responses are WAV

That request shape is covered by an offline test with a fake client. It is not evidence of pronunciation, timing, or cost. Those get a row here only after a real WAV exists and has been listened to.

| Date | What was tried | Result |
| --- | --- | --- |
| 2026-11-25 | Offline pipeline, schema, cache, and fake TTS | Tests pass locally. No audio was generated. |
