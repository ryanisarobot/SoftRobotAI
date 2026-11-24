"""Promptfoo dynamic chat prompt for the matched Openness pilot.

Uses the existing Willow starter system prompt, plus exactly one locked
Openness-level instruction. The pilot is not yet the complete runtime assembly.
"""

import json
from pathlib import Path

WILLOW_BASELINE = json.loads(
    (Path(__file__).resolve().parent / "willow.json").read_text(encoding="utf-8")
)[0]["content"]


def create_prompt(context):
    variables = context["vars"]
    level = variables["target_level"]
    instruction = variables["openness_instruction"]
    history = variables.get("history", [])
    messages = [
        {
            "role": "system",
            "content": WILLOW_BASELINE + f"\n\nOCEAN Openness ({level}): {instruction}",
        }
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": variables["message"]})
    return json.dumps(messages, ensure_ascii=False)
