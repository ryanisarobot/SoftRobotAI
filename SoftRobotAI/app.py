import io
import logging
import os
import time
import wave

import streamlit as st
from openai import OpenAI
from study import (DURATION, FINAL_TURN_GRACE, QUESTIONS, config, database,
                   assign, participant, new_session, phase, prompt_for,
                   save_session, save_reviews)

st.set_page_config(page_title='SS4T Conversation Study', page_icon='💬', layout='centered')

# Validate database connection before accepting participants.
try:
    with database() as db:
        db.execute('SELECT 1')
except Exception:
    logging.exception('Database connection failed')
    st.error('Study database is unavailable. Contact the administrator.')
    st.stop()

CFG = config()
MODEL = os.getenv('SS4T_MODEL', 'gpt-4o-mini')
STT_MODEL = os.getenv('SS4T_STT_MODEL', 'gpt-4o-mini-transcribe')
TTS_MODEL = os.getenv('SS4T_TTS_MODEL', 'gpt-4o-mini-tts')
VOICE = os.getenv('SS4T_TTS_VOICE', 'marin')


def api():
    if not os.getenv('OPENAI_API_KEY'):
        st.error('Missing OpenAI API configuration. Contact the study administrator.')
        st.stop()
    return OpenAI(timeout=45, max_retries=1)


def transcribe(raw):
    f = io.BytesIO(raw)
    f.name = 'speech.wav'
    result = api().audio.transcriptions.create(model=STT_MODEL, file=f)
    return (result.text or '').strip()


def audio_for(text):
    return api().audio.speech.create(
        model=TTS_MODEL, voice=VOICE, input=text, response_format='mp3').content


def show_error(stage, exc):
    # Do not expose API keys, server URLs, or error details to public users.
    logging.exception('%s failed', stage, exc_info=exc)
    st.error(f'{stage} failed. Please try again or contact the administrator.')


def respond(s, text, mode):
    if not text.strip():
        st.warning('No speech detected. Please try again.')
        return
    state = phase(s)
    if state in ('expired', 'closed'):
        st.warning('The conversation has ended.')
        return
    ending = state == 'final'
    before = time.perf_counter()
    try:
        settings = {
            'model': MODEL,
            'input': s['messages'] + [{'role': 'user', 'content': text}],
            'temperature': s['condition']['temperature'],
            'max_output_tokens': 230,
        }
        instructions = prompt_for(s['cfg'], s['condition']['prompt'])['instructions']
        if instructions:
            settings['instructions'] = instructions
        with st.spinner('Companion responding...'):
            result = api().responses.create(**settings)
            answer = (result.output_text or '').strip()
            if not answer:
                raise RuntimeError('The model returned no text.')
    except Exception as exc:
        s['errors'] += 1
        show_error('AI message', exc)
        return
    sound = None
    try:
        sound = audio_for(answer)
    except Exception as exc:
        s['errors'] += 1
        show_error('Speech synthesis', exc)
    elapsed = time.perf_counter() - before
    s['messages'] += [
        {'role': 'user', 'content': text},
        {'role': 'assistant', 'content': answer},
    ]
    s['turns'] += 1
    s['voice_turns'] += int(mode == 'voice')
    s['turn_data'].append({
        'n': s['turns'], 'user': text, 'ai': answer, 'mode': mode,
        'latency': elapsed, 'timestamp': time.time(),
    })
    s['last_audio'] = sound
    if ending or phase(s) != 'active':
        s['final_used'] = True
        s['closed'] = True
        s['end_reason'] = 'final_reply'
    st.rerun()


for field, value in [
    ('participant', None), ('ordinal', 0), ('session', None),
    ('survey_done', False), ('reviews_done', False), ('reviews', {}),
]:
    if field not in st.session_state:
        st.session_state[field] = value

with st.sidebar:
    st.subheader('Study controls')
    if st.button('Start over / New participant', use_container_width=True):
        for key in ('participant', 'ordinal', 'session', 'survey_done',
                    'reviews_done', 'reviews'):
            st.session_state.pop(key, None)
        st.rerun()
    st.caption('Start over before testing a new participant. Saved data is not deleted.')

CONSENT_VERSION = '2026-11-08-draft-1'
RESEARCH_CONTACT = os.getenv(
    'SS4T_RESEARCH_CONTACT', '[Researcher name and email: to be provided before recruitment]')
RESEARCH_OVERSIGHT = os.getenv(
    'SS4T_RESEARCH_OVERSIGHT', '[Supervising adult/institutional contact: to be provided before recruitment]')

CONSENT_TEXT = f"""SS4T — Conversation Study
PARTICIPANT INFORMATION AND CONSENT — DRAFT ({CONSENT_VERSION})

Key information
You are being invited to take part in a research study about how different AI conversational styles affect people's experiences. Participation is voluntary. If you agree, you will complete two short conversations with an AI companion prototype and answer questions about them. Each conversation lasts up to five minutes, with a possible final-message period of up to one additional minute. Allow approximately 15–25 minutes for the full activity, including ratings. This is experimental research, not medical care, counseling, or a diagnostic assessment.

What you will do
You will answer optional background questions about age range, gender, and prior experience with conversational AI. You may type or record messages to the AI. Different participants and conversations receive different AI instructions and model settings by assignment. After each conversation, you will rate the overall experience on 1–7 scales, indicate whether you would continue the conversation, and may leave comments. You can also review individual exchanges and rate the AI's appropriateness, understanding, and naturalness on 1–7 scales, mark noteworthy responses, and provide optional comments.

What information is collected
The study database stores a randomly generated participant ID; any background categories you choose; assigned AI conditions and model settings; session times, turn counts and technical-error counts; your typed messages and transcripts of spoken messages; the AI's written replies; response timing; and your survey answers, individual-response ratings and optional comments. We do not ask for your name in this form.

Voice processing and external services
If you use the microphone, your recorded audio is sent to OpenAI's speech-transcription service for processing. The study application does not intentionally save the original microphone recordings to its Supabase research database. It does save the text transcript and the AI's written reply. Conversations are processed using OpenAI services; research records are stored in Supabase; and the website runs on Streamlit Community Cloud. These external services may process or temporarily retain information under their own policies. Do not share names, addresses, passwords, medical records or other sensitive personal information.

Privacy and use of results
Researchers with database access may read transcripts and survey responses. Because free-text messages can contain identifying details, the records cannot be guaranteed to be anonymous, despite using participant IDs. Results may be analyzed in aggregate or described in research reports; identifiable quotations should not be publicly shared without separate permission or suitable de-identification. No internet-based storage or transmission is completely risk-free. Data retention, access controls and deletion procedures must be finalized by the study supervisor before recruitment.

Potential risks and benefits
Risks include discomfort with an AI response, frustration, fatigue, disclosure of personal information, and a possible breach of confidentiality. There may be no direct benefit to you. Findings may inform the design of future companion robots. This AI is not a human, healthcare provider or emergency service.

Voluntary participation
Taking part is your choice. You can decline to participate, skip optional background questions or comments, and end a conversation early. You can withdraw from the study at any time without penalty. Ending early will not automatically delete information already saved; contact the researcher to discuss any request concerning your data. If you prefer not to participate, simply do not begin the study.

Questions and contacts
Study researcher: {RESEARCH_CONTACT}
Study supervisor / research-rights contact: {RESEARCH_OVERSIGHT}
Please ask the researcher any questions before agreeing.

Consent acknowledgment
By checking the agreement box and starting, you confirm that you are at least 18 years old, have read or had this information explained to you, had an opportunity to ask questions, and voluntarily agree to participate. This checkbox is an electronic acknowledgment, not a substitute for any consent documentation or research approval required by the supervising institution.

DRAFT — The study's supervisor must review and finalize this information and the consent procedure before external participant recruitment.
"""

st.title('SS4T — Conversation Study')
st.caption('AI conversational research prototype · Spoken replies are artificially generated.')
if st.session_state.participant is None:
    st.subheader('Participant information and consent')
    st.info('Please read this information before deciding whether to participate.')
    if RESEARCH_CONTACT.startswith('[') or RESEARCH_OVERSIGHT.startswith('['):
        st.warning('Researcher and supervisor contact details have not yet been configured. '
                   'This consent form is a draft for supervised testing, not recruitment.')
    st.markdown('**Overview:** Two short AI conversations, followed by surveys. Your message '
                'text, AI replies, optional demographic categories and ratings are stored. '
                'Microphone recordings are transmitted for transcription but are not '
                'stored in the study database. Participation is voluntary.')
    with st.expander('Full participant information and consent form', expanded=True):
        st.text(CONSENT_TEXT)
    st.download_button('Download consent information (text)',
                       data=CONSENT_TEXT, file_name='SS4T_consent_information.txt',
                       mime='text/plain')
    with st.form('intro'):
        age = st.selectbox('Age range (optional)',
                           ['Prefer not to say', 'Under 60', '60–69', '70–79', '80–89', '90+'])
        gender = st.selectbox('Gender (optional)',
                              ['Prefer not to say', 'Woman', 'Man', 'Nonbinary', 'Self-describe'])
        experience = st.selectbox('Previous conversational AI experience (optional)',
                                  ['Prefer not to say', 'None', 'A little', 'Some', 'A lot'])
        adult = st.checkbox('I confirm that I am at least 18 years old.')
        consent = st.checkbox('I have read the study information, understand participation '
                              'is voluntary, and agree to take part.')
        agreed = st.form_submit_button('Agree and begin study', type='primary')
    if agreed:
        if not adult or not consent:
            st.error('You must confirm you are at least 18 and agree to participate.')
        else:
            try:
                # Participant rows are created only after affirmative acknowledgment.
                st.session_state.participant = participant(age, gender, experience)
            except Exception as exc:
                show_error('Participant setup', exc)
            else:
                st.rerun()
    st.stop()

try:
    assignment = assign(st.session_state.participant, CFG)
except Exception as exc:
    show_error('Assignment', exc)
    st.stop()
if st.session_state.ordinal >= len(assignment):
    st.success('Study complete. Thank you.')
    st.stop()

s = st.session_state.session
if s is None:
    st.subheader(f'Conversation {st.session_state.ordinal + 1} of {len(assignment)}')
    st.write('Speak naturally about any topic you choose. This conversation lasts up to '
             'five minutes. At the end, you may finish one final thought and hear one final reply.')
    st.write('Use the microphone recorder or type. The AI will respond aloud when audio playback is available.')
    if st.button('Start conversation', type='primary'):
        st.session_state.session = new_session(
            st.session_state.participant, st.session_state.ordinal + 1,
            assignment[st.session_state.ordinal], CFG)
        st.rerun()
    st.stop()


@st.fragment(run_every='1s')
def countdown():
    status = phase(s)
    if status == 'active':
        remaining = max(0, DURATION - int(time.time() - s['started']))
        st.progress(remaining / DURATION)
        st.write(f'Time remaining: {remaining // 60}:{remaining % 60:02d}')
    elif status == 'final':
        remaining = max(0, int(DURATION + FINAL_TURN_GRACE - (time.time() - s['started'])))
        st.warning(f'Five minutes reached. You may submit one final message ({remaining}s remaining).')
    else:
        st.info('Conversation complete.')


countdown()
for m in s['messages']:
    with st.chat_message('assistant' if m['role'] == 'assistant' else 'user'):
        st.write(m['content'])
if s['last_audio'] and s['messages'] and s['messages'][-1]['role'] == 'assistant':
    st.audio(s['last_audio'], format='audio/mp3', autoplay=True)

if phase(s) == 'expired' and not s['closed']:
    s['closed'] = True
    s['end_reason'] = 'grace_expired'
if not s['closed']:
    st.subheader('Send a message')
    st.caption('Record your message, press Stop to finish recording, then select Send recorded message.')
    sound = st.audio_input('Record your message',
                           key=f'audio_{s["id"]}_{s["turns"]}')
    if sound is not None:
        st.info('Recording ready. Select Send recorded message to submit it.')
    if st.button('Send recorded message', type='primary',
                 disabled=sound is None, use_container_width=True,
                 key=f'send_audio_{s["id"]}_{s["turns"]}'):
        raw = sound.getvalue()
        try:
            with wave.open(io.BytesIO(raw), 'rb') as w:
                recorded_seconds = w.getnframes() / w.getframerate()
            if phase(s) == 'final' and recorded_seconds > FINAL_TURN_GRACE:
                st.error('Final recording is too long. Please record a shorter final thought.')
            else:
                with st.spinner('Transcribing speech...'):
                    text = transcribe(raw)
                if text:
                    respond(s, text, 'voice')
                else:
                    st.warning('No speech recognized. Record another message or type below.')
        except Exception as exc:
            s['errors'] += 1
            show_error('Microphone transcription', exc)
    typed = st.chat_input('Or type a message')
    if typed:
        respond(s, typed, 'text')

    st.divider()
    with st.expander('End conversation early (optional)'):
        st.warning('This ends your current conversation and starts the review. It does not send your recording.')
        if st.button('Confirm end conversation', key=f'end_{s["id"]}'):
            s['closed'] = True
            s['end_reason'] = 'participant_ended'
            st.rerun()

if s['closed'] and not st.session_state.survey_done:
    st.divider()
    st.subheader('Overall conversation review')
    st.write('1 = strongly disagree; 7 = strongly agree. Please rate the conversation overall.')
    with st.form('overall_' + s['id']):
        ratings = {
            k: st.radio(q, list(range(1, 8)), horizontal=True, index=None,
                        key='rating_' + s['id'] + k)
            for k, q in QUESTIONS
        }
        continuation = st.radio('Would you voluntarily continue this conversation?',
                                ['Yes', 'No', 'Unsure'], index=None)
        feedback = st.text_area('What did you like or dislike? (optional)')
        submitted = st.form_submit_button('Submit overall review', type='primary')
    if submitted:
        if any(v is None for v in ratings.values()) or continuation is None:
            st.error('Complete all six ratings and the continuation question.')
        else:
            try:
                save_session(s, ratings, feedback, continuation, MODEL, VOICE)
            except Exception as exc:
                show_error('Saving conversation', exc)
            else:
                st.session_state.survey_done = True
                st.rerun()

if s['closed'] and st.session_state.survey_done and not st.session_state.reviews_done:
    st.divider()
    st.subheader('Individual-response review')
    st.write('Review each exchange below. Rate each statement from 1 (strongly disagree) '
             'to 7 (strongly agree). You can skip an exchange if you do not wish to rate it.')
    reviews = st.session_state.reviews
    for turn in s['turn_data']:
        n = turn['n']
        with st.expander(f'Exchange {n}', expanded=(n == 1)):
            st.markdown('**You said:**')
            st.write(turn['user'])
            st.markdown('**AI replied:**')
            st.write(turn['ai'])
            questions = [
                ('appropriateness', "The AI's response was appropriate to what I said."),
                ('understanding', 'The AI demonstrated understanding of what I said.'),
                ('naturalness', "The AI's response felt natural."),
            ]
            scores = {}
            for name, question in questions:
                scores[name] = st.radio(
                    question, list(range(1, 8)), index=None, horizontal=True,
                    key=f'turn_{name}_{s["id"]}_{n}')
            stand = st.checkbox(
                'This response stood out to me',
                key=f'stand_{s["id"]}_{n}')
            comment = st.text_area(
                'Optional comment about this response',
                key=f'comment_{s["id"]}_{n}')
            reviews[n] = {**scores, 'standout': stand, 'comment': comment}
    if st.button('Save response review / Finish', type='primary'):
        try:
            save_reviews(s, reviews)
        except Exception as exc:
            show_error('Saving response reviews', exc)
        else:
            st.session_state.reviews_done = True
            st.rerun()

if s['closed'] and st.session_state.survey_done and st.session_state.reviews_done:
    st.success('Reviews saved.')
    if st.button('Next conversation / Finish', type='primary'):
        st.session_state.ordinal += 1
        st.session_state.session = None
        st.session_state.survey_done = False
        st.session_state.reviews_done = False
        st.session_state.reviews = {}
        st.rerun()
