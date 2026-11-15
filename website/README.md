# SS4T — hosted Streamlit + Supabase version

This package preserves the GitHub repository's `pilot-0.4-listening` prompts, two conversations per participant, 5-minute limit with 60-second final-message window, speech input/output, ratings, and password-protected admin CSV exports. It replaces local SQLite with persistent Supabase PostgreSQL.

## 1. Create database (one-time)

1. Go to https://supabase.com/dashboard, create a project, choose its region, and save its *database password* securely.
2. Open **SQL Editor** and run the complete `schema.sql` file (this creates five tables and restricts Data API access).
3. Open **Connect**, choose **Session pooler**, and copy the URI (port **5432**). Do **not** use the direct IPv6 URI when your app cannot reach IPv6; do not use the transaction pooler on 6543 for this code. Replace `[YOUR-PASSWORD]` with your database password; percent-encode reserved URI characters if needed. The URI must be in the form `postgresql://...`.
4. Check **Table Editor**: `participants`, `assignments`, `sessions`, `turns`, `turn_reviews` should exist. Leave public Data API permissions restricted.

## 2. Prepare OpenAI and GitHub

1. Obtain an OpenAI API key with available API billing/credits. This key is separate from ChatGPT subscriptions.
2. In GitHub, open `ryanisarobot/SoftRobotAI`. Upload the contents of this package to the repository root, **replacing the old files**. Include `schema.sql`, and retain the `.gitignore` entry for `.streamlit/secrets.toml`.
3. Keep the GitHub repository **private** if preferred. Connect GitHub authorization to Streamlit; do not upload any secrets or the `study.db` file to GitHub.

## 3. Deploy Streamlit

1. Visit https://share.streamlit.io and sign in with GitHub. Click **Create app**, choose `ryanisarobot/SoftRobotAI`, branch `main`, entry point `app.py`.
2. Open **Advanced settings → Secrets**. Paste this TOML with YOUR real values (do not commit it):

```toml
OPENAI_API_KEY = "sk-your-real-api-key"
DATABASE_URL = "postgresql://postgres.PROJECT_REF:URL_ENCODED_PASSWORD@YOUR_POOLER_HOST:5432/postgres"
ROBOT_ADMIN_PASSWORD = "A-LONG-RANDOM-UNIQUE-PASSWORD"
SS4T_MODEL = "gpt-4o-mini"
SS4T_STT_MODEL = "gpt-4o-mini-transcribe"
SS4T_TTS_MODEL = "gpt-4o-mini-tts"
SS4T_TTS_VOICE = "marin"
```

Root-level Streamlit secrets are exposed to the app as environment variables. Do not share these values with participants. Paste the exact URI from Supabase **Connect / Session pooler**. If the password has `@`, `#`, `?`, or other reserved characters, percent-encode it in the URI; alternately use a generated password without these characters.

3. Choose the desired `*.streamlit.app` subdomain, then deploy. App setup requires a working Supabase connection; see **Manage app → Logs** for database errors.
4. Participants use your public main app URL. Admin page: `https://YOUR-SUBDOMAIN.streamlit.app/1_Admin` (or select Admin from the Streamlit multipage navigation). Enter your `ROBOT_ADMIN_PASSWORD` to view and export CSV results.

## 4. Test before recruiting

1. Visit the main page in a private/incognito browser, confirm consent checkbox, start the study.
2. Test a text exchange and a recorded audio exchange (allow microphone permission), then **End conversation early** and submit the six ratings and continuation question.
3. Open Supabase Table Editor; verify there is one new participant, one assignment, one session row, and turns. Verify admin dashboard and all four CSV exports.
4. Refresh / restart the hosted app and verify that the saved rows remain in Supabase.
5. Test completing the second conversation, the final-message grace window, and two simultaneous browser sessions. Test on your participants' target devices.
6. Check OpenAI API usage/cost limits before publishing the link.

## 5. Important limits

- This remains a *pilot*, **not** a verified or IRB-approved research deployment. Obtain applicable research oversight/consent approval before recruitment, especially for older or vulnerable participants.
- **Completion-only saving**: transcripts/ratings are saved only once the participant submits the overall survey. If they abandon the tab, the unsaved conversation is lost. The server keeps the active conversation in browser session state, not Supabase.
- Your 2-condition assignment heuristic is preliminary, not a statistically validated counterbalancing design. Freeze study prompts/model/temperatures before analysis.
- The database credential in Streamlit has broad table access. RLS blocks anonymous browser Data API users, but the server's database login bypasses those anonymous permissions. Do not expose `DATABASE_URL` to the browser.
- Admin page has per-session password attempt throttling, not IP-wide protection or MFA. If your study needs stronger controls, require an authenticated identity provider or separate the admin service from the public app.
- Community Cloud apps may hibernate after 12 hours with no visits and require visitors to wake them. For a completely uninterrupted service, use an always-on provider.
- `study.db` from the old local version is **not** migrated automatically. Export/retain it separately if it contains prior pilot data.
- No persistent raw audio is stored, but speech is sent to OpenAI APIs for transcription; textual conversations are stored in Supabase and may contain participant-provided sensitive content. Disclose third-party processing and the retention policy to participants.
- Never commit secrets to the repository, even if private.

## Local development

```powershell
py -m pip install -r requirements.txt
$env:OPENAI_API_KEY="..."
$env:DATABASE_URL="postgresql://..."
$env:ROBOT_ADMIN_PASSWORD="..."
py -m streamlit run app.py
```

Or use `.streamlit/secrets.toml` locally (already gitignored). The Supabase schema must already be created.
