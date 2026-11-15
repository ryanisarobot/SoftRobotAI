-- Run in Supabase SQL Editor once before testing the updated questionnaire.
-- Does not modify existing participant, session, or conversation records.
CREATE TABLE IF NOT EXISTS public.design_questionnaires (
    participant_id text PRIMARY KEY REFERENCES public.participants(participant_id) ON DELETE CASCADE,
    questionnaire_version text NOT NULL,
    answers_json jsonb NOT NULL,
    submitted_at double precision NOT NULL
);
ALTER TABLE public.design_questionnaires ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.design_questionnaires FROM anon, authenticated;
