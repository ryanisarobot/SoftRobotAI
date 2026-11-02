import hashlib
import json
import os
import random
import time
import uuid
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent
DURATION = 300
FINAL_TURN_GRACE = 60
QUESTIONS = [
    ('natural', 'The conversation felt natural.'),
    ('understood', 'I felt that the AI understood what I was saying.'),
    ('comfortable', 'I felt comfortable speaking with the AI.'),
    ('engaging', 'I found the conversation engaging.'),
    ('relevant', "The AI's responses were relevant and easy to follow."),
    ('again', 'I would like to have another conversation with this AI.'),
]


def config():
    return json.loads((ROOT / 'prompts.json').read_text(encoding='utf-8'))


def conditions(cfg):
    return [{'prompt': p['id'], 'temperature': t}
            for p in cfg['prompts'] for t in cfg['temperatures']]


def prompt_for(cfg, pid):
    return next(p for p in cfg['prompts'] if p['id'] == pid)


def database():
    url = os.getenv('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL is missing. Configure Streamlit secrets.')
    # Use Supabase Session pooler (:5432), not Transaction pooler (:6543).
    # Each call is short-lived; SSL verifies transport encryption.
    return psycopg.connect(url, sslmode='require', connect_timeout=10, row_factory=dict_row)


def assign(participant_id, cfg):
    with database() as db:
        # Serialize assignments globally to prevent concurrent participants
        # receiving a condition allocation based on the same count.
        db.execute('SELECT pg_advisory_xact_lock(8726140)')
        row = db.execute('SELECT sequence_json FROM assignments WHERE participant_id=%s',
                         (participant_id,)).fetchone()
        if row:
            return row['sequence_json']
        count = db.execute('SELECT count(*) AS n FROM assignments').fetchone()['n']
        cs = conditions(cfg)
        n = len(cs)
        order = list(range(n))
        random.Random(count // n).shuffle(order)
        i = count % n
        pair = [cs[order[i]], cs[order[(i + 1) % n]]]
        if (count // n) % 2:
            pair.reverse()
        db.execute('INSERT INTO assignments (participant_id,sequence_json,created_at) '
                   'VALUES (%s,%s,%s)', (participant_id, json.dumps(pair), time.time()))
        return pair


def participant(age, gender, experience):
    pid = str(uuid.uuid4())
    with database() as db:
        db.execute('INSERT INTO participants '
                   '(participant_id,age_range,gender,ai_experience,created_at) '
                   'VALUES (%s,%s,%s,%s,%s)', (pid, age, gender, experience, time.time()))
    return pid


def new_session(pid, ordinal, cond, cfg):
    return dict(id=str(uuid.uuid4()), participant=pid, ordinal=ordinal,
                condition=cond, cfg=cfg, started=time.time(), messages=[],
                turn_data=[], turns=0, voice_turns=0, errors=0,
                final_used=False, closed=False, end_reason='', last_audio=None)


def phase(s, now=None):
    if s['closed']:
        return 'closed'
    elapsed = (time.time() if now is None else now) - s['started']
    if elapsed < DURATION:
        return 'active'
    if elapsed <= DURATION + FINAL_TURN_GRACE and not s['final_used']:
        return 'final'
    return 'expired'


def save_session(s, ratings, feedback, continuation, model, voice):
    prompt = prompt_for(s['cfg'], s['condition']['prompt'])['instructions']
    columns = ['session_id', 'participant_id', 'ordinal', 'assigned_prompt',
               'temperature', 'prompt_hash', 'config_version', 'model', 'voice',
               'started_at', 'finished_at', 'ended_reason', 'turns', 'voice_turns',
               'voluntary_continue', 'technical_errors', 'final_turn_used',
               *[k for k, _ in QUESTIONS], 'feedback']
    values = [s['id'], s['participant'], s['ordinal'], s['condition']['prompt'],
              s['condition']['temperature'], hashlib.sha256(prompt.encode()).hexdigest(),
              s['cfg']['version'], model, voice, s['started'], time.time(), s['end_reason'],
              s['turns'], s['voice_turns'], continuation, s['errors'], s['final_used'],
              *[ratings[k] for k, _ in QUESTIONS], feedback]
    update = ','.join(f'{c}=EXCLUDED.{c}' for c in columns if c != 'session_id')
    q = (f"INSERT INTO sessions ({','.join(columns)}) VALUES "
         f"({','.join(['%s'] * len(columns))}) ON CONFLICT (session_id) DO UPDATE SET {update}")
    with database() as db:
        db.execute(q, values)
        for t in s['turn_data']:
            db.execute('''INSERT INTO turns
                (session_id,turn_number,user_text,ai_text,mode,response_seconds,created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (session_id,turn_number) DO UPDATE SET
                user_text=EXCLUDED.user_text, ai_text=EXCLUDED.ai_text,
                mode=EXCLUDED.mode,response_seconds=EXCLUDED.response_seconds,
                created_at=EXCLUDED.created_at''',
                (s['id'], t['n'], t['user'], t['ai'], t['mode'], t['latency'], t['timestamp']))


def save_reviews(s, reviews):
    with database() as db:
        for n, rec in reviews.items():
            db.execute('''INSERT INTO turn_reviews
                (session_id,turn_number,rating,stood_out) VALUES (%s,%s,%s,%s)
                ON CONFLICT (session_id,turn_number) DO UPDATE SET
                rating=EXCLUDED.rating,stood_out=EXCLUDED.stood_out''',
                (s['id'], int(n), rec.get('rating'), bool(rec.get('standout', False))))
