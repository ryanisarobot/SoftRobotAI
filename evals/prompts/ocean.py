"""Construct a matched OCEAN chat prompt using the same fixed Willow baseline.

The one manipulated variable is the selected OCEAN trait instruction. All
other trait modules are still pending full-runtime prompt integration.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = json.loads((ROOT / 'willow.json').read_text(encoding='utf-8'))[0]['content']


def create_prompt(context):
    variables = context['vars']
    trait_name = variables['trait_name']
    level = variables['target_level']
    text = variables['trait_instruction']
    if not level.startswith(variables['trait'] + '-'):
        raise ValueError('Target level does not match assigned trait')
    messages = [{'role': 'system', 'content': BASELINE + f'\n\nOCEAN {trait_name} ({level}): {text}'}]
    messages.extend(variables.get('history', []))
    messages.append({'role': 'user', 'content': variables['message']})
    return json.dumps(messages, ensure_ascii=False)