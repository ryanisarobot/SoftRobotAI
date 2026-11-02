import csv
import hmac
import io
import os
import time

import streamlit as st
from study import database

st.set_page_config(page_title='SS4T Study Admin', page_icon='📋')
st.title('SS4T Study Results — Admin')
secret = os.getenv('ROBOT_ADMIN_PASSWORD', '')
if not secret or len(secret) < 16:
    st.error('Admin disabled: set a strong ROBOT_ADMIN_PASSWORD (16+ characters).')
    st.stop()

if 'admin_authorized' not in st.session_state:
    st.session_state.admin_authorized = False
if 'admin_failures' not in st.session_state:
    st.session_state.admin_failures = 0
if 'admin_lock_until' not in st.session_state:
    st.session_state.admin_lock_until = 0.0

if not st.session_state.admin_authorized:
    if time.time() < st.session_state.admin_lock_until:
        st.error('Too many attempts in this session. Try again later.')
        st.stop()
    with st.form('login'):
        attempt = st.text_input('Administrator password', type='password')
        submit = st.form_submit_button('Sign in')
    if submit:
        if hmac.compare_digest(secret, attempt):
            st.session_state.admin_authorized = True
            st.session_state.admin_failures = 0
            st.rerun()
        else:
            st.session_state.admin_failures += 1
            if st.session_state.admin_failures >= 5:
                st.session_state.admin_lock_until = time.time() + 300
                st.session_state.admin_failures = 0
            st.error('Incorrect password')
    st.stop()

if st.button('Sign out'):
    st.session_state.admin_authorized = False
    st.rerun()

tables = {
    'Sessions & surveys': '''SELECT s.*,p.age_range,p.gender,p.ai_experience
                            FROM sessions s LEFT JOIN participants p
                            USING (participant_id) ORDER BY s.started_at DESC''',
    'Transcripts': '''SELECT * FROM turns ORDER BY session_id,turn_number''',
    'Individual response ratings': '''SELECT * FROM turn_reviews ORDER BY session_id,turn_number''',
    'Participant assignments': '''SELECT * FROM assignments ORDER BY created_at''',
}
selection = st.selectbox('Dataset', list(tables))
try:
    with database() as db:
        rows = db.execute(tables[selection]).fetchall()
except Exception:
    st.error('Could not load study results. Check database configuration and server logs.')
    st.stop()
st.metric('Rows', len(rows))
if rows:
    st.dataframe(rows, use_container_width=True)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    data = buffer.getvalue()
    # CSV may include JSONB arrays; csv.writer stringifies them safely.
    st.download_button('Download selected CSV', data.encode('utf-8-sig'),
                       file_name=selection.lower().replace(' ', '_') + '.csv',
                       mime='text/csv')
st.warning('Transcripts may contain sensitive information. Follow approved consent, retention, and deletion policies.')
