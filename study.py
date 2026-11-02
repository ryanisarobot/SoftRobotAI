import hashlib
import json
import random
import sqlite3
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'study.db'
DURATION = 300
FINAL_TURN_GRACE = 60
QUESTIONS = [
 ('natural','The conversation felt natural.'),
 ('understood','I felt that the AI understood what I was saying.'),
 ('comfortable','I felt comfortable speaking with the AI.'),
 ('engaging','I found the conversation engaging.'),
 ('relevant',"The AI's responses were relevant and easy to follow."),
 ('again','I would like to have another conversation with this AI.')
]

def config():
    return json.loads((ROOT/'prompts.json').read_text(encoding='utf-8'))

def conditions(cfg):
    return [{'prompt':p['id'],'temperature':t} for p in cfg['prompts'] for t in cfg['temperatures']]

def prompt_for(cfg, pid):
    return next(p for p in cfg['prompts'] if p['id']==pid)

def database():
    conn=sqlite3.connect(DB,timeout=20)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('''CREATE TABLE IF NOT EXISTS participants (
       participant_id TEXT PRIMARY KEY, age_range TEXT, gender TEXT,
       ai_experience TEXT, created_at REAL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS assignments (
       participant_id TEXT PRIMARY KEY, sequence_json TEXT, created_at REAL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS sessions (
       session_id TEXT PRIMARY KEY, participant_id TEXT, ordinal INTEGER,
       assigned_prompt TEXT, temperature REAL, prompt_hash TEXT, config_version TEXT,
       model TEXT, voice TEXT, started_at REAL, finished_at REAL, ended_reason TEXT,
       turns INTEGER, voice_turns INTEGER, voluntary_continue TEXT,
       technical_errors INTEGER, final_turn_used INTEGER,
       natural INTEGER, understood INTEGER, comfortable INTEGER,
       engaging INTEGER, relevant INTEGER, again INTEGER, feedback TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS turns (
       session_id TEXT, turn_number INTEGER, user_text TEXT, ai_text TEXT,
       mode TEXT, response_seconds REAL, created_at REAL,
       PRIMARY KEY(session_id,turn_number))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS turn_reviews (
       session_id TEXT, turn_number INTEGER, rating TEXT, stood_out INTEGER,
       PRIMARY KEY(session_id,turn_number))''')
    conn.commit()
    return conn

def assign(participant_id,cfg):
    # Balanced condition appearances over cycles; order alternates. Pilot assignment,
    # not an inferentially optimized balanced incomplete-block design.
    with database() as db:
        row=db.execute('SELECT sequence_json FROM assignments WHERE participant_id=?',(participant_id,)).fetchone()
        if row: return json.loads(row[0])
        db.execute('BEGIN IMMEDIATE')
        count=db.execute('SELECT count(*) FROM assignments').fetchone()[0]
        cs=conditions(cfg)
        n=len(cs)
        order=list(range(n))
        random.Random(count//n).shuffle(order)
        i=count%n
        pair=[cs[order[i]],cs[order[(i+1)%n]]]
        if (count//n)%2: pair.reverse()
        db.execute('INSERT INTO assignments VALUES (?,?,?)',(participant_id,json.dumps(pair),time.time()))
        return pair

def participant(age, gender, experience):
    pid=str(uuid.uuid4())
    with database() as db:
        db.execute('INSERT INTO participants VALUES (?,?,?,?,?)',(pid,age,gender,experience,time.time()))
    return pid

def new_session(pid,ordinal,cond,cfg):
    return dict(id=str(uuid.uuid4()),participant=pid,ordinal=ordinal,condition=cond,
      cfg=cfg,started=time.time(),messages=[],turn_data=[],turns=0,
      voice_turns=0,errors=0,final_used=False,closed=False,end_reason='',last_audio=None)

def phase(s,now=None):
    if s['closed']: return 'closed'
    elapsed=(time.time() if now is None else now)-s['started']
    if elapsed < DURATION: return 'active'
    if elapsed <= DURATION+FINAL_TURN_GRACE and not s['final_used']: return 'final'
    return 'expired'

def save_session(s,ratings,feedback,continuation,model,voice):
    prompt=prompt_for(s['cfg'],s['condition']['prompt'])['instructions']
    values=[s['id'],s['participant'],s['ordinal'],s['condition']['prompt'],
      s['condition']['temperature'],hashlib.sha256(prompt.encode()).hexdigest(),
      s['cfg']['version'],model,voice,s['started'],time.time(),s['end_reason'],
      s['turns'],s['voice_turns'],continuation,s['errors'],int(s['final_used']),
      *[ratings[k] for k,_ in QUESTIONS],feedback]
    with database() as db:
        db.execute('INSERT OR REPLACE INTO sessions VALUES ('+','.join(['?']*len(values))+')',values)
        for t in s['turn_data']:
            db.execute('INSERT OR REPLACE INTO turns VALUES (?,?,?,?,?,?,?)',(
             s['id'],t['n'],t['user'],t['ai'],t['mode'],t['latency'],t['timestamp']))

def save_reviews(s, reviews):
    with database() as db:
        for n,rec in reviews.items():
            db.execute('INSERT OR REPLACE INTO turn_reviews VALUES (?,?,?,?)',
                       (s['id'],int(n),rec.get('rating'),int(rec.get('standout',False))))
