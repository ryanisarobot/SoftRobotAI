# SoftRobotAI — Updated 2×2 voice study prototype

Built using the original `SoftRobotAI_starter(1).zip` project as the folder base. The original team-testing interface has been replaced with a research-oriented pilot interface; the admin page remains but reads the new study database.

## Running locally (Windows PowerShell)

```powershell
py -m pip install -r requirements.txt
$env:OPENAI_API_KEY="YOUR_SECRET_API_KEY"
$env:ROBOT_ADMIN_PASSWORD="LONG_PRIVATE_ADMIN_PASSWORD"
py -m streamlit run app.py
```

Supported default text model: `gpt-4o-mini`, with temperature 0.3 or 0.9. Change via `SS4T_MODEL` only after confirming temperature support. Audio transcription `gpt-4o-mini-transcribe`; voice synthesis `gpt-4o-mini-tts`, default voice `marin` (change via `SS4T_TTS_VOICE`).

## Experimental protocol and features

- Two prompts: P1 responsive, P2 proactive. Two temperatures: 0.3 and 0.9. Four total conditions.
- Two conditions per participant assigned by a preliminary pilot heuristic (not statistically finalized counterbalancing).
- Five minutes plus one final submitted user utterance and one final AI reply, within a 60-second final window; participants can end early.
- Browser audio recorder and manual send; text fallback. Auto-send after 1 s silence is **not implemented**. It requires real-time browser audio/VAD logic separate from the basic Streamlit recorder.
- Optional age range, optional gender and previous AI experience (all have prefer-not-to-say); no real names.
- Six 1–7 ratings, voluntary-continuation question, optional free-text comments.
- Session survey and metadata saved in `study.db`; no raw audio or transcripts stored by this version.
- Admin page protected by ROBOT_ADMIN_PASSWORD, CSV export.

## Important

The code has not been tested end-to-end with API credentials, microphone, or real participants. Consent checkbox is **not a substitute** for IRB-approved informed consent. Obtain IRB approval **before recruitment or research data collection**. The anonymous per-browser identity is not robust against reloads. SQLite is local, with no encrypted hosting, backup, rate-limiting or deployment hardening. Study prompts and voice should be frozen before the approved study. Do not deploy publicly as-is.

## Prompt wording (pilot-0.3-initiative)

The shared prompt is defined in `app.py` as `BASE`; only the difference in conversational initiative is specified in `prompts.json`. P1 is responsive; P2 is proactively inquisitive. Freeze all prompts before collecting study data. The default synthetic voice is already `marin` (`SS4T_TTS_VOICE`).
