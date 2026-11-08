"""Pre-conversation MVP design questionnaire; optional responses only."""
import json
import time

import streamlit as st

from study import database

VERSION = 'mvp-prestudy-1.0'

# These questions concern a hypothetical soft companion robot, not the
# conversational AI's demonstrated capabilities.
SECTIONS = [
    ('Use and setting', [
        ('use_cases', 'In which situations might you want to use a soft companion robot? (Select all that apply.)',
         'multi', ['Relaxing alone', 'Talking or storytelling', 'During a difficult or stressful moment', 'As part of a daily routine', 'Entertainment or hobbies', 'I would not want one', 'Not sure']),
        ('location', 'Where would you most likely keep or use it?', 'single',
         ['Living room / chair', 'Bedroom / bedside', 'On my lap', 'Shared room / common area', 'I would not use it', 'Not sure', 'Other']),
        ('primary_value', 'Which single feature would matter most to you?', 'single',
         ['Conversation', 'Comforting physical presence', 'Helpful reminders or information', 'Entertainment', 'Ease of use and control', 'None of these', 'Not sure']),
    ]),
    ('Relationship and interaction', [
        ('role', 'How would you prefer the robot to present its role?', 'single',
         ['A friendly companion', 'A practical assistant', 'A pet-like companion', 'A mix of companion and assistant', 'I would not use one', 'No preference']),
        ('initiation', 'When should the robot start a conversation on its own?', 'single',
         ['Never unless I ask', 'Only at times I have chosen', 'Occasionally when I appear available, with an easy way to decline', 'Whenever it has something relevant to share', 'Not sure']),
        ('interaction_style', 'If you seem upset, what should the robot generally do first?', 'single',
         ['Listen and acknowledge what I say', 'Ask whether I want to talk more', 'Offer a practical suggestion', 'Offer quiet company without asking questions', 'Wait for me to say what I want', 'Not sure']),
        ('humor', 'How much humor would you want from the robot?', 'single',
         ['None', 'A little when appropriate', 'Moderate', 'Often', 'Depends on my mood', 'Not sure']),
    ]),
    ('Memory and privacy', [
        ('memory_categories', 'What could the robot remember between conversations, with your permission? (Select all that apply.)',
         'multi', ['Hobbies and interests', 'Preferred voice and conversation settings', 'Names or details about family and friends', 'Stories or past experiences', 'Daily routines or planned activities', 'Personal feelings or worries', 'None: do not remember personal information', 'Not sure']),
        ('memory_permission', 'How should the robot obtain permission to remember new personal details?', 'single',
         ['Ask each time', 'Let me approve a list of memories later', 'Remember only categories I enabled in settings', 'Do not save any memories', 'Not sure']),
        ('memory_control', 'Which control would be most important to you?', 'single',
         ['See what is remembered', 'Correct an inaccurate memory', 'Delete a memory', 'Turn off future remembering', 'All are equally important', 'Not sure']),
        ('data_sharing', 'Who, if anyone, should be able to see what you discuss with the robot?', 'single',
         ['Only me', 'People I explicitly approve, on a case-by-case basis', 'A caregiver or family member I designate', 'No one should be able to save or view transcripts', 'Not sure']),
    ]),
    ('Physical comfort and appearance', [
        ('form', 'Which overall appearance would you be most willing to interact with?', 'single',
         ['Soft cat-like plush', 'Soft dog-like plush', 'Soft bear-like plush', 'Other animal-like plush', 'Non-animal soft object', 'None of these', 'Not sure']),
        ('touch', 'Which physical interactions would you consider trying? (Select all that apply.)',
         'multi', ['Holding it on my lap', 'Petting or stroking it', 'Holding its paw/hand', 'A gentle hug that I initiate', 'A gentle hug after it asks permission', 'None', 'Not sure']),
        ('hug_permission', 'If the robot could hug, how should a hug begin?', 'single',
         ['Only when I explicitly request it', 'It may offer verbally, but must wait for my permission', 'It may use a subtle gesture to offer, but must wait for permission', 'I would not want hugs', 'Not sure']),
        ('stop_control', 'How would you most want to stop a robot movement immediately?', 'single',
         ['A large physical stop button', 'A spoken stop command', 'A light touch or squeeze gesture', 'More than one of these controls', 'Not sure']),
        ('appearance_concern', 'What, if anything, would make a soft robot uncomfortable to hold or use?', 'text', None),
    ]),
    ('Access and ongoing use', [
        ('interaction_mode', 'Which way of interacting would be easiest for you?', 'single',
         ['Talking aloud', 'Physical buttons', 'Touchscreen or app', 'A combination of voice and simple physical controls', 'Not sure']),
        ('adjustments', 'Which adjustable settings would be useful? (Select all that apply.)',
         'multi', ['Speaking volume', 'Speaking speed', 'Length of responses', 'How often it starts conversations', 'Amount of physical movement', 'None', 'Not sure']),
        ('barrier', 'What would be the biggest barrier to using it regularly?', 'single',
         ['Privacy concerns', 'Difficulty hearing or understanding it', 'Complexity or upkeep', 'Discomfort with touch or appearance', 'Unhelpful or repetitive conversations', 'Too much interaction or interruption', 'No personal need for it', 'Not sure']),
        ('lasting_value', 'What would make you continue using it after the initial novelty wears off?', 'text', None),
        ('other_needs', 'Is there anything else you would want the designers to know? (Optional)', 'text', None),
    ]),
]


def display_questionnaire(participant_id):
    st.header('Part 1 — Companion robot design questionnaire')
    st.write('This section asks about your preferences for a **proposed** soft companion robot. '
             'The physical robot is not being tested here. There are no right or wrong answers. '
             'Every question is optional, and you may choose “Not sure” where available.')
    with st.form('mvp_design_questionnaire'):
        answers = {}
        for section_title, questions in SECTIONS:
            st.subheader(section_title)
            for key, question, kind, options in questions:
                if kind == 'multi':
                    answers[key] = st.multiselect(question, options, key='design_'+key)
                elif kind == 'single':
                    answers[key] = st.radio(question, options, index=None, key='design_'+key)
                else:
                    answers[key] = st.text_area(question, key='design_'+key,
                                                max_chars=1200)
        submitted = st.form_submit_button('Save questionnaire and continue to AI conversations',
                                           type='primary')
    if submitted:
        try:
            with database() as db:
                db.execute(
                    """INSERT INTO design_questionnaires
                       (participant_id, questionnaire_version, answers_json, submitted_at)
                       VALUES (%s,%s,%s,%s)
                       ON CONFLICT (participant_id) DO UPDATE SET
                       questionnaire_version=EXCLUDED.questionnaire_version,
                       answers_json=EXCLUDED.answers_json,
                       submitted_at=EXCLUDED.submitted_at""",
                    (participant_id, VERSION, json.dumps(answers), time.time()))
        except Exception:
            # app.py handles logging without disclosing connection secrets
            raise
        return True
    return False
