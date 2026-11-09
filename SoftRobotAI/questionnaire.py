"""Optional, plain-language companion-robot MVP questionnaire, divided into short steps."""
import json
import time
import random
import hashlib
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from study import database

VERSION = 'mvp-prestudy-2.1'
ASSET_DIR = Path(__file__).resolve().parent / 'appearance_assets'
APPEARANCE_VARIANTS = {
    'cat': 'Cat', 'dog': 'Dog', 'bear': 'Bear', 'neutral': 'Non-animal',
}

# Each question maps to a distinct MVP design choice. Questions deliberately avoid
# presuming that someone has previously encountered an AI companion robot.
# (id, question, format, choices); format: single, multi, text.
SECTIONS = [
    (
        'A little about your day',
        'First, a few questions about everyday experiences. You do not need to know anything about robots.',
        [
            ('quiet_times', 'When you have some quiet time, what do you most often enjoy doing?', 'multi',
             ['Talking with someone', 'Watching TV or listening to music', 'Reading or doing a hobby',
              'Resting quietly', 'Spending time with a pet', 'Something else', 'Prefer not to say']),
            ('conversation_time', 'Are there times when you especially enjoy having someone to talk with?', 'multi',
             ['In the morning', 'In the afternoon', 'In the evening', 'When I have had a difficult day',
              'There is no particular time', 'I generally prefer quiet time', 'Not sure']),
            ('social_pace', 'When you are talking with someone, how do you usually prefer the conversation to go?', 'single',
             ['I enjoy frequent questions and back-and-forth conversation',
              'I enjoy talking but also like some quiet pauses',
              'I prefer to lead the conversation myself', 'It depends on the situation', 'Not sure']),
            ('comfort_object', 'Do you ever enjoy holding something soft, such as a pillow, blanket, or stuffed animal?', 'single',
             ['Often', 'Sometimes', 'Rarely', 'Never', 'Not sure']),
            ('everyday_challenge', 'Is there an everyday activity you wish were a little easier or more enjoyable?', 'text', None),
        ],
    ),
    (
        'Getting to know the idea',
        'Imagine a small, soft, animal-shaped robot you could keep nearby. It could talk with you, '
        'listen, and make gentle movements. It would be a machine, not a person or a real pet. '
        'These are ideas for a future design, not features you will try in this online study.',
        [
            ('first_reaction', 'How interested would you be in trying something like this?', 'single',
             ['Very interested', 'Somewhat interested', 'Neither interested nor uninterested',
              'Not very interested', 'Not at all interested', 'Not sure']),
            ('potential_use', 'Which of these would you be interested in using it for, if any?', 'multi',
             ['Having a conversation', 'Listening to stories or music', 'Holding or hugging it',
              'Getting reminders or everyday information', 'Relaxing quietly with it nearby',
              'I would not be interested in using it', 'Not sure']),
            ('likely_place', 'Where could you imagine keeping something like this?', 'single',
             ['In a living room', 'Near my bed', 'On a favorite chair or couch',
              'In a shared/common room', 'I would not want one nearby', 'Not sure', 'Somewhere else']),
            ('robot_role', 'Would you rather it feel more like a friendly companion or a practical helper?', 'single',
             ['Mostly a friendly companion', 'Mostly a practical helper', 'A little of both',
              'Neither', 'Not sure']),
            ('first_concern', 'What would concern you most about having something like this?', 'single',
             ['Privacy', 'It talking or moving when I do not want it to',
              'It being hard to use', 'It not understanding me',
              'It not feeling comfortable to hold', 'I would not expect any major concern',
              'Not sure']),
        ],
    ),
    (
        'Talking and listening',
        'The following questions concern how you would want a talking robot to behave.',
        [
            ('robot_start', 'When would you want it to begin talking to you?', 'single',
             ['Only when I speak first', 'At times I choose ahead of time',
              'It could occasionally ask if I want to talk', 'I would be happy for it to start conversations on its own',
              'Not sure']),
            ('response_length', 'When you ask an everyday question, what kind of answer would you usually prefer?', 'single',
             ['A short answer', 'A medium-length answer', 'A detailed answer',
              'It depends on what I asked', 'Not sure']),
            ('pause_behavior', 'If you pause while speaking to think of what to say next, what should it do?', 'single',
             ['Stay quiet until I clearly finish', 'Give a brief sign it is listening',
              'Ask if I am finished after a moment', 'Not sure']),
            ('repair', 'If it did not understand something you said, what would you prefer?', 'single',
             ['Ask me to repeat it', 'Tell me what it thinks I meant and ask if that is right',
              'Ask a short, specific question about the unclear part', 'Not sure']),
            ('difficult_moment', 'Imagine you tell it you have had a hard day. What would you want it to do first?', 'single',
             ['Listen without trying to solve the problem', 'Ask whether I want to talk about it',
              'Offer a helpful suggestion', 'Change to a lighter topic',
              'Wait for me to tell it what I want', 'Not sure']),
            ('humor', 'Would you enjoy the robot occasionally making lighthearted jokes?', 'single',
             ['Yes', 'Sometimes, depending on my mood', 'No', 'Not sure']),
            ('voice_controls', 'What would you want to change about how it talks? (Choose any.)', 'multi',
             ['Loudness', 'Speaking speed', 'Length of answers', 'How often it asks questions',
              'Its voice', 'I would not want to adjust anything', 'Not sure']),
        ],
    ),
    (
        'Remembering and privacy',
        'Some devices can remember information between conversations. These questions ask what '
        'you would be comfortable with. The proposed robot would not need to remember everything.',
        [
            ('garden_scenario', 'Imagine you mention that you enjoy gardening. The next day, the robot remembers that. How would you feel?', 'single',
             ['Comfortable', 'Somewhat comfortable', 'Somewhat uncomfortable', 'Uncomfortable',
              'It would depend on whether I gave permission', 'Not sure']),
            ('memory_permission', 'Before saving something personal to remember later, what should it do?', 'single',
             ['Ask me each time', 'Let me choose in advance what kinds of things it can remember',
              'Only save something when I specifically tell it to',
              'Never save personal information', 'Not sure']),
            ('memory_categories', 'Which things, if any, would you be comfortable letting it remember with your permission?', 'multi',
             ['Favorite activities and hobbies', 'How I like the robot to speak',
              'Stories I have told', 'Information about family and friends',
              'My daily plans', 'Personal worries or feelings',
              'Nothing about me', 'Not sure']),
            ('memory_control', 'If it remembered something incorrectly, what would you want to be able to do?', 'multi',
             ['See what it remembers', 'Correct it', 'Delete it',
              'Turn off remembering', 'Not sure']),
            ('sharing', 'If you told it something personal, who should be able to see that conversation?', 'single',
             ['Only me', 'Someone I choose', 'A trusted family member or caregiver I approve',
              'I would not want conversations stored at all', 'Not sure']),
        ],
    ),
    (
        'Holding, moving, and using it',
        'Think about a soft, animal-shaped robot that might move its arms gently. There is no '
        'physical robot to touch during this study, so it is fine to choose “Not sure.”',
        [
            ('appearance_image', 'Which of these designs would you most like to have nearby?', 'visual', None),
            ('touch', 'What would you be willing to try with it?', 'multi',
             ['Keeping it on my lap', 'Petting it', 'Holding its paw',
              'Hugging it', 'None of these', 'Not sure']),
            ('hug_permission', 'If it could give a gentle hug, how should that happen?', 'single',
             ['Only if I ask for one', 'It could offer, but it should wait for me to say yes',
              'I would rather it not hug me', 'Not sure']),
            ('movement_stop', 'How would you most like to stop it from moving?', 'single',
             ['Press a button', 'Say “stop”', 'Either a button or my voice',
              'Another simple way', 'Not sure']),
            ('interaction_method', 'How would you most like to tell it what you want?', 'single',
             ['By speaking', 'By pressing simple buttons',
              'By using a screen', 'By speaking or using buttons', 'Not sure']),
            ('comfort_concern', 'Is there anything about the way it looks, feels, or moves that you might dislike?', 'text', None),
        ],
    ),
    (
        'Final thoughts',
        'These final questions help us prioritize what would actually make the design useful.',
        [
            ('biggest_benefit', 'If you could choose just one thing it should do well, what would that be?', 'single',
             ['Have enjoyable conversations', 'Be comfortable to hold',
              'Provide everyday help', 'Be simple to use', 'Respect my privacy and choices',
              'None of these', 'Not sure']),
            ('continued_use', 'What might make you stop using something like this after trying it for a while?', 'multi',
             ['Conversations become repetitive', 'It interrupts too often',
              'It is uncomfortable to hold', 'It is hard to operate',
              'Privacy concerns', 'It does not do anything I need',
              'I would need to try it to know', 'Not sure']),
            ('final_comment', 'Is there something else you would want the people designing this robot to know?', 'text', None),
        ],
    ),
]

QUESTION_COUNT = sum(len(questions) for _, _, questions in SECTIONS)


def _scroll_to_top():
    """Best effort reset after consent and between questionnaire pages.

    Streamlit often preserves the main page's vertical scroll position after
    st.rerun. This iframe is same-origin in compatible Streamlit deployments;
    failure to access its parent should never interrupt the survey.
    """
    components.html("""<script>
      try {
        const p = window.parent;
        p.scrollTo({top: 0, behavior: 'instant'});
        const main = p.document.querySelector('[data-testid="stMain"]');
        if (main) main.scrollTo({top: 0, behavior: 'instant'});
      } catch (e) {}
    </script>""", height=0)


def display_questionnaire(participant_id):
    page_key = 'design_questionnaire_page'
    answers_key = 'design_questionnaire_answers'
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
        st.session_state[answers_key] = {}
        st.session_state['design_scroll_reset'] = True

    if st.session_state.pop('design_scroll_reset', False):
        _scroll_to_top()

    page = st.session_state[page_key]
    title, intro, questions = SECTIONS[page]

    st.header('Part 1 — Getting to know your preferences')
    st.progress((page + 1) / len(SECTIONS), text=f'Section {page + 1} of {len(SECTIONS)}')
    st.subheader(title)
    st.write(intro)
    st.caption('There are no right or wrong answers. All questions are optional; '
               'you may leave any blank. Your answers help guide a future design.')

    # Persist answers when moving between sections, independent of widget lifetime.
    saved = st.session_state[answers_key]
    with st.form(f'design_form_{page}'):
        page_answers = {}
        for key, question, kind, options in questions:
            prev = saved.get(key)
            if kind == 'visual':
                order_key = 'appearance_order_' + participant_id
                if order_key not in st.session_state:
                    options = list(APPEARANCE_VARIANTS)
                    random.Random(int(hashlib.sha256(participant_id.encode()).hexdigest(), 16)).shuffle(options)
                    st.session_state[order_key] = options
                order = st.session_state[order_key]
                st.write(question)
                st.caption('All pictures are design illustrations, not photographs of a working robot.')
                if all((ASSET_DIR / (name + '.webp')).is_file() for name in order):
                    for start in (0, 2):
                        cols = st.columns(2)
                        for col, name in zip(cols, order[start:start+2]):
                            with col:
                                st.image(str(ASSET_DIR / (name + '.webp')),
                                         caption=APPEARANCE_VARIANTS[name],
                                         use_container_width=True)
                else:
                    st.warning('Appearance images have not been added to this deployment yet.')
                answer_options = [APPEARANCE_VARIANTS[name] for name in order] + ['None of these', 'Not sure']
                index = answer_options.index(prev) if prev in answer_options else None
                page_answers[key] = st.radio(
                    'Select your preferred design', answer_options, index=index,
                    key=f'v2_design_{page}_{key}')
                page_answers['appearance_order'] = order
                page_answers['appearance_version'] = 'matched-lineup-v1'
            elif kind == 'multi':
                page_answers[key] = st.multiselect(
                    question, options, default=prev or [], key=f'v2_design_{page}_{key}')
            elif kind == 'single':
                index = options.index(prev) if prev in options else None
                page_answers[key] = st.radio(
                    question, options, index=index, key=f'v2_design_{page}_{key}')
            else:
                page_answers[key] = st.text_area(
                    question, value=prev or '', max_chars=1000,
                    key=f'v2_design_{page}_{key}', height=80)
        c1, c2 = st.columns([1, 2])
        with c1:
            back = st.form_submit_button('Previous section', disabled=page == 0)
        with c2:
            label = ('Save and continue to AI conversations'
                     if page == len(SECTIONS) - 1 else 'Next section')
            next_page = st.form_submit_button(label, type='primary')

    if not back and not next_page:
        return False

    saved.update(page_answers)
    if back:
        st.session_state[page_key] = page - 1
        st.session_state['design_scroll_reset'] = True
        st.rerun()

    if page < len(SECTIONS) - 1:
        st.session_state[page_key] = page + 1
        st.session_state['design_scroll_reset'] = True
        st.rerun()

    with database() as db:
        db.execute(
            """INSERT INTO design_questionnaires
               (participant_id, questionnaire_version, answers_json, submitted_at)
               VALUES (%s,%s,%s,%s)
               ON CONFLICT (participant_id) DO UPDATE SET
               questionnaire_version=EXCLUDED.questionnaire_version,
               answers_json=EXCLUDED.answers_json,
               submitted_at=EXCLUDED.submitted_at""",
            (participant_id, VERSION, json.dumps(saved), time.time()))
    return True
