-- Run once in your Supabase project's SQL Editor.
-- Do not enable public access to these tables through the Supabase Data API.
CREATE TABLE IF NOT EXISTS public.participants (
    participant_id text PRIMARY KEY,
    age_range text, gender text, ai_experience text, created_at double precision
);
CREATE TABLE IF NOT EXISTS public.assignments (
    participant_id text PRIMARY KEY REFERENCES public.participants(participant_id),
    sequence_json jsonb NOT NULL, created_at double precision
);
CREATE TABLE IF NOT EXISTS public.sessions (
    session_id text PRIMARY KEY,
    participant_id text REFERENCES public.participants(participant_id),
    ordinal integer, assigned_prompt text, temperature double precision,
    prompt_hash text, config_version text, model text, voice text,
    started_at double precision, finished_at double precision, ended_reason text,
    turns integer, voice_turns integer, voluntary_continue text,
    technical_errors integer, final_turn_used boolean,
    "natural" integer, understood integer, comfortable integer,
    engaging integer, relevant integer, again integer, feedback text
);
CREATE TABLE IF NOT EXISTS public.turns (
    session_id text REFERENCES public.sessions(session_id) ON DELETE CASCADE,
    turn_number integer, user_text text, ai_text text, mode text,
    response_seconds double precision, created_at double precision,
    PRIMARY KEY(session_id, turn_number)
);
CREATE TABLE IF NOT EXISTS public.turn_reviews (
    session_id text, turn_number integer, rating text, stood_out boolean,
    PRIMARY KEY(session_id,turn_number),
    FOREIGN KEY (session_id,turn_number)
        REFERENCES public.turns(session_id,turn_number) ON DELETE CASCADE
);
-- Defense in depth: even if someone gets a Supabase public/anon API key,
-- these tables must not expose experiment responses.
ALTER TABLE public.participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.turn_reviews ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.participants,public.assignments,public.sessions,
    public.turns,public.turn_reviews FROM anon,authenticated;
