"""Backward-compatible Openness pilot using the verified full-library assembler."""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from willow_library import create_messages


def create_prompt(context):
    return json.dumps(create_messages(context['vars'], trait='O'), ensure_ascii=False)