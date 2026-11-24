"""Promptfoo entry point for the shared O/C/E/A/N matched evaluation suite."""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from willow_library import create_messages


def create_prompt(context):
    return json.dumps(create_messages(context['vars']), ensure_ascii=False)