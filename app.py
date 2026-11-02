import io
import os
import time
import wave
import logging
import hashlib
import streamlit as st
from openai import OpenAI
from study import (DURATION,FINAL_TURN_GRACE,QUESTIONS,config,database,
                   assign,participant,new_session,phase,prompt_for,save_session,save_reviews)

st.set_page_config(page_title='SS4T Conversation Study',page_icon='💬',layout='centered')
database()
CFG=config()
MODEL=os.getenv('SS4T_MODEL','gpt-4o-mini')
STT_MODEL=os.getenv('SS4T_STT_MODEL','gpt-4o-mini-transcribe')
TTS_MODEL=os.getenv('SS4T_TTS_MODEL','gpt-4o-mini-tts')
VOICE=os.getenv('SS4T_TTS_VOICE','marin')

# IMPORTANT: No hidden companion instructions. P1 really has no custom system message.
def messages_for(s,text):
    inst=prompt_for(s['cfg'],s['condition']['prompt'])['instructions']
    m=[] if not inst else [{'role':'system','content':inst}]
    return m+s['messages']+[{'role':'user','content':text}]

def api():
    if not os.getenv('OPENAI_API_KEY'):
        st.error('Missing OPENAI_API_KEY. Contact the study administrator.')
        st.stop()
    return OpenAI(timeout=45,max_retries=1)

def transcribe(raw):
    f=io.BytesIO(raw); f.name='speech.wav'
    result=api().audio.transcriptions.create(model=STT_MODEL,file=f)
    return (result.text or '').strip()

def audio_for(text):
    return api().audio.speech.create(model=TTS_MODEL,voice=VOICE,input=text,response_format='mp3').content

def show_error(stage, exc):
    # Local development: expose API and microphone errors rather than masking them.
    logging.exception("SS4T %s failed", stage, exc_info=exc)
    st.error(f"{stage} failed: {type(exc).__name__}: {exc}")

def respond(s,text,mode):
    if not text.strip():
        st.warning('No speech detected. Please try again.'); return
    state=phase(s)
    if state in ('expired','closed'):
        st.warning('The conversation has ended.'); return
    ending=state=='final'
    before=time.perf_counter()
    try:
        # Same Responses endpoint as the original working site, without injecting
        # any hidden instructions into the P1 control condition.
        settings={'model':MODEL,'input':s['messages']+[{'role':'user','content':text}],
                  'temperature':s['condition']['temperature'],'max_output_tokens':230}
        instructions=prompt_for(s['cfg'],s['condition']['prompt'])['instructions']
        if instructions:
            settings['instructions']=instructions
        with st.spinner('Companion responding...'):
            result=api().responses.create(**settings)
            answer=(result.output_text or '').strip()
            if not answer: raise RuntimeError('The model returned no text.')
    except Exception as exc:
        s['errors']+=1
        show_error('AI message',exc)
        return

    sound=None
    try:
        sound=audio_for(answer)
    except Exception as exc:
        s['errors']+=1
        show_error('Speech synthesis (text response was saved)',exc)

    elapsed=time.perf_counter()-before
    s['messages'] += [{'role':'user','content':text},{'role':'assistant','content':answer}]
    s['turns']+=1
    s['voice_turns']+=int(mode=='voice')
    s['turn_data'].append({'n':s['turns'],'user':text,'ai':answer,'mode':mode,
                           'latency':elapsed,'timestamp':time.time()})
    s['last_audio']=sound
    if ending or phase(s)!='active':
        s['final_used']=True; s['closed']=True; s['end_reason']='final_reply'
    st.rerun()

for field,value in [('participant',None),('ordinal',0),('session',None),('survey_done',False),
                    ('reviews_done',False),('reviews',{})]:
    if field not in st.session_state: st.session_state[field]=value

# Study state survives Streamlit source-code reloads in the same browser tab.
# Give the study administrator an explicit way to restart a local test.
with st.sidebar:
    st.subheader('Study controls')
    if st.button('Start over / New participant', use_container_width=True):
        for key in ('participant', 'ordinal', 'session', 'survey_done',
                    'reviews_done', 'reviews'):
            st.session_state.pop(key, None)
        st.rerun()
    st.caption('Use Start over before testing a new participant. Existing saved data is not deleted.')

st.title('SS4T — Conversation Study')
st.caption('AI conversational research prototype · Spoken replies are artificially generated.')
if st.session_state.participant is None:
    st.write('Talk about anything you naturally want to discuss. No required subjects. '
             'You may stop at any time. Avoid sharing private or sensitive information.')
    st.warning('For supervised testing only. Research approval and an approved consent process are required before participant recruitment.')
    with st.form('intro'):
        age=st.selectbox('Age range (optional)', ['Prefer not to say','Under 60','60–69','70–79','80–89','90+'])
        gender=st.selectbox('Gender (optional)', ['Prefer not to say','Woman','Man','Nonbinary','Self-describe'])
        experience=st.selectbox('Previous conversational AI experience (optional)',
                                ['Prefer not to say','None','A little','Some','A lot'])
        consent=st.checkbox('I have completed the study administrator’s approved consent process.')
        agreed=st.form_submit_button('Begin study',type='primary')
    if agreed:
        if not consent: st.error('Consent confirmation is required.')
        else:
            st.session_state.participant=participant(age,gender,experience)
            st.rerun()
    st.stop()

assignment=assign(st.session_state.participant,CFG)
if st.session_state.ordinal>=len(assignment):
    st.success('Study complete. Thank you.'); st.stop()

s=st.session_state.session
if s is None:
    st.subheader(f'Conversation {st.session_state.ordinal+1} of {len(assignment)}')
    st.write('Speak naturally about any topic you choose. This conversation lasts up to five minutes. '
             'At the end, you may finish one final thought and hear one final reply.')
    st.write('Use the microphone recorder or type. The AI will respond aloud when audio playback is available.')
    if st.button('Start conversation',type='primary'):
        st.session_state.session=new_session(st.session_state.participant,
             st.session_state.ordinal+1,assignment[st.session_state.ordinal],CFG)
        st.rerun()
    st.stop()

@st.fragment(run_every='1s')
def countdown():
    status=phase(s)
    if status=='active':
        remaining=max(0,DURATION-int(time.time()-s['started']))
        st.progress(remaining/DURATION)
        st.write(f'Time remaining: {remaining//60}:{remaining%60:02d}')
    elif status=='final':
        remaining=max(0,int(DURATION+FINAL_TURN_GRACE-(time.time()-s['started'])))
        st.warning(f'Five minutes reached. You may submit one final message ({remaining}s remaining).')
    else: st.info('Conversation complete.')
countdown()

for m in s['messages']:
    with st.chat_message('assistant' if m['role']=='assistant' else 'user'):
        st.write(m['content'])
if s['last_audio'] and s['messages'] and s['messages'][-1]['role']=='assistant':
    st.audio(s['last_audio'],format='audio/mp3',autoplay=True)

if phase(s)=='expired' and not s['closed']:
    s['closed']=True; s['end_reason']='grace_expired'
if not s['closed']:
    st.caption('Microphone mode is record-and-submit; continuous silence detection is not yet implemented.')
    sound=st.audio_input('Record your message (stops when you click Stop)',
                         key=f'audio_{s["id"]}_{s["turns"]}')
    if sound is not None:
        raw=sound.getvalue()
        # Submit automatically once the browser recorder is stopped. The cache
        # prevents the same audio being resubmitted on Streamlit reruns.
        fingerprint=hashlib.sha256(raw).hexdigest()
        attempt_key=f'audio_attempt_{s["id"]}_{s["turns"]}'
        if st.session_state.get(attempt_key)!=fingerprint:
            st.session_state[attempt_key]=fingerprint
            try:
                with wave.open(io.BytesIO(raw),'rb') as w:
                    recorded_seconds=w.getnframes()/w.getframerate()
                if phase(s)=='final' and recorded_seconds>FINAL_TURN_GRACE:
                    st.error('Final recording is too long. Please record a shorter final thought.')
                else:
                    with st.spinner('Transcribing speech...'):
                        text=transcribe(raw)
                    if not text:
                        st.warning('No speech recognized. Record another message or type below.')
                    else:
                        st.caption('Recognized speech: '+text)
                        respond(s,text,'voice')
            except Exception as exc:
                s['errors']+=1
                show_error('Microphone transcription',exc)
        else:
            st.caption('Recording already processed. To try again, select Clear on the microphone widget or type below.')
    typed=st.chat_input('Or type a message')
    if typed: respond(s,typed,'text')
    if st.button('End conversation early'):
        s['closed']=True; s['end_reason']='participant_ended'; st.rerun()

if s['closed'] and not st.session_state.survey_done:
    st.divider(); st.subheader('Overall conversation review')
    st.write('1 = strongly disagree; 7 = strongly agree. Please rate the conversation overall.')
    with st.form('overall_'+s['id']):
        ratings={k:st.radio(q,list(range(1,8)),horizontal=True,index=None,key='rating_'+s['id']+k)
                 for k,q in QUESTIONS}
        continuation=st.radio('Would you voluntarily continue this conversation?',
                              ['Yes','No','Unsure'],index=None)
        feedback=st.text_area('What did you like or dislike? (optional)')
        submitted=st.form_submit_button('Submit overall review',type='primary')
    if submitted:
        if any(v is None for v in ratings.values()) or continuation is None:
            st.error('Complete all six ratings and the continuation question.')
        else:
            save_session(s,ratings,feedback,continuation,MODEL,VOICE)
            st.session_state.survey_done=True; st.rerun()

if s['closed'] and st.session_state.survey_done and not st.session_state.reviews_done:
    st.divider(); st.subheader('Optional individual-response review')
    st.write('You may review any or all replies, or skip this step. Your overall evaluation is already saved.')
    reviews=st.session_state.reviews
    for turn in s['turn_data']:
        n=turn['n']
        with st.expander(f'Exchange {n}',expanded=(n==1)):
            st.markdown('**You said:**'); st.write(turn['user'])
            st.markdown('**AI replied:**'); st.write(turn['ai'])
            rating=st.radio('How was this AI response?',
                ['Skip','Poor','Okay','Good'],horizontal=True,
                index=['Skip','Poor','Okay','Good'].index(reviews.get(n,{}).get('rating') or 'Skip'),
                key=f'rating_turn_{s["id"]}_{n}')
            stand=st.checkbox('This response stood out to me',
                 value=reviews.get(n,{}).get('standout',False),key=f'stand_{s["id"]}_{n}')
            reviews[n]={'rating':None if rating=='Skip' else rating,'standout':stand}
    if st.button('Save response review / Finish',type='primary'):
        save_reviews(s,reviews)
        st.session_state.reviews_done=True; st.rerun()

if s['closed'] and st.session_state.survey_done and st.session_state.reviews_done:
    st.success('Reviews saved.')
    if st.button('Next conversation / Finish',type='primary'):
        st.session_state.ordinal+=1
        st.session_state.session=None
        st.session_state.survey_done=False
        st.session_state.reviews_done=False
        st.session_state.reviews={}
        st.rerun()
