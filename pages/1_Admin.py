import csv
import io
import os
import sqlite3
import hmac
from pathlib import Path
import streamlit as st
st.set_page_config(page_title='SS4T Study Admin',page_icon='📋')
st.title('SS4T Study Results — Admin')
secret=os.getenv('ROBOT_ADMIN_PASSWORD','')
if not secret:
    st.error('Admin dashboard disabled. Set ROBOT_ADMIN_PASSWORD.'); st.stop()
if not st.session_state.get('admin_authorized',False):
    with st.form('login'):
        attempt=st.text_input('Password',type='password')
        submit=st.form_submit_button('Sign in')
    if submit:
        if hmac.compare_digest(secret,attempt):
            st.session_state.admin_authorized=True;st.rerun()
        else:st.error('Incorrect password')
    st.stop()
if st.button('Sign out'):
    st.session_state.admin_authorized=False;st.rerun()
path=Path(__file__).resolve().parents[1]/'study.db'
if not path.exists(): st.info('No study data yet.');st.stop()
with sqlite3.connect(path) as db:
    db.row_factory=sqlite3.Row
    tables={
    'Sessions & surveys':'''SELECT s.*,p.age_range,p.gender,p.ai_experience FROM sessions s
                            LEFT JOIN participants p USING (participant_id) ORDER BY s.started_at DESC''',
    'Transcripts':'''SELECT * FROM turns ORDER BY session_id,turn_number''',
    'Individual response ratings':'''SELECT * FROM turn_reviews ORDER BY session_id,turn_number''',
    'Participant assignments':'''SELECT * FROM assignments ORDER BY created_at'''
    }
    selection=st.selectbox('Dataset',list(tables))
    rows=[dict(r) for r in db.execute(tables[selection])]
st.metric('Rows',len(rows))
if rows:
    st.dataframe(rows,use_container_width=True)
    buffer=io.StringIO()
    writer=csv.DictWriter(buffer,fieldnames=list(rows[0]))
    writer.writeheader();writer.writerows(rows)
    st.download_button('Download selected CSV',buffer.getvalue().encode('utf-8-sig'),
       file_name=selection.lower().replace(' ','_')+'.csv',mime='text/csv')
st.warning('Transcripts can contain sensitive personal information. Restrict admin access and follow your approved retention/deletion policy.')
