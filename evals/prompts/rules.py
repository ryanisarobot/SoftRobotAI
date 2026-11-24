"""Promptfoo chat template for individual FOUND/CONV/CAPS rule compliance."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from willow_library import build_system_prompt, ocean_levels


def create_prompt(context):
    variables = context['vars']
    # All prompt modules are held constant for individual-rule grading.
    system = build_system_prompt('O', 'O-3', ocean_levels()['O']['O-3'])
    history = variables.get('history', [])
    if not isinstance(history, list) or any(
        not isinstance(m, dict) or m.get('role') not in ('user', 'assistant')
        or not isinstance(m.get('content'), str) for m in history
    ):
        raise ValueError('Invalid fixed conversation history')
    message = variables.get('message')
    if not isinstance(message, str):
        raise ValueError('Missing user message')
    return json.dumps([{'role': 'system', 'content': system}, *history,
                       {'role': 'user', 'content': message}], ensure_ascii=False)