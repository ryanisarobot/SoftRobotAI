"""Assemble Willow's verified instruction library for controlled Promptfoo tests.

Reads canonical instruction text directly from committed evaluation rubrics.
Never treats an evaluator description or CAPS working paraphrase as a prompt.
"""

from functools import lru_cache
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TRAITS = {'O': 'Openness', 'C': 'Conscientiousness', 'E': 'Extraversion',
          'A': 'Agreeableness', 'N': 'Neuroticism'}
VERIFIED_CAPS = ('CAPS-001',)
INCOMPLETE_CAPS = ('CAPS-002', 'CAPS-003', 'CAPS-004')


def _read(path):
    return path.read_text(encoding='utf-8-sig')


def original_instruction(folder, identifier):
    path = ROOT / 'rubrics' / folder / f'{identifier}.txt'
    source = _read(path)
    if 'RULE ID: ' + identifier not in source.splitlines()[:4]:
        raise ValueError(f'Rule identifier does not match file: {path}')
    if re.search(r'(?im)^STATUS:.*(?:REVIEW DRAFT|NOT APPROVED|PROVISIONAL)', source):
        raise ValueError(f'Unapproved instruction: {path}')
    match = re.search(
        r'(?m)^ORIGINAL INSTRUCTION:[ \t]*\r?\n(.*?)\r?\n[ \t]*EVALUATION OBJECTIVE\b',
        source, re.DOTALL,
    )
    if not match:
        raise ValueError(f'Missing exact ORIGINAL INSTRUCTION in {path}')
    instruction = match.group(1).strip()
    if not instruction or any(token in instruction.casefold() for token in (
        'working paraphrase', 'exact locked instruction wording not recovered',
        'insert the verbatim', 'provisional behavioral target',
    )):
        raise ValueError(f'Noncanonical instruction in {path}')
    return instruction


@lru_cache(maxsize=1)
def common_rules():
    """Return verified FOUND-001..005, CONV-001..020 and CAPS-001 in order."""
    entries = []
    for family, number in (('FOUND', 5), ('CONV', 20)):
        for i in range(1, number + 1):
            key = f'{family}-{i:03d}'
            entries.append((key, original_instruction(family, key)))
    for key in VERIFIED_CAPS:
        entries.append((key, original_instruction('CAPS', key)))
    return tuple(entries)


@lru_cache(maxsize=1)
def ocean_levels():
    """Read all 25 OCEAN definitions verbatim from approved trait rubrics."""
    output = {}
    for trait in TRAITS:
        source = _read(ROOT / 'rubrics' / 'OCEAN' / f'OCEAN-{trait}.txt')
        if 'ORIGINAL INSTRUCTIONS' not in source or 'EVALUATION OBJECTIVE' not in source:
            raise ValueError(f'Missing OCEAN-{trait} section delimiters')
        section = source.split('ORIGINAL INSTRUCTIONS', 1)[1].split('EVALUATION OBJECTIVE', 1)[0]
        found = dict(re.findall(rf'(?m)^({trait}-[1-5]):[ \t]*(.+?)[ \t]*$', section))
        if set(found) != {f'{trait}-{i}' for i in range(1, 6)}:
            raise ValueError(f'Incomplete OCEAN-{trait} locked definitions')
        output[trait] = found
    return output


def build_system_prompt(trait, target_level, trait_instruction, *, fixed_level=3,
                        active_caps=VERIFIED_CAPS):
    """Change only one OCEAN trait; hold the other four at fixed_level.

    CAPS-001 is conditional inside its own instruction and is supplied unchanged
    to every comparison. CAPS-002..004 cannot be enabled until their verbatim
    original instructions are recovered and reviewed.
    """
    if trait not in TRAITS or target_level not in {f'{trait}-{i}' for i in range(1, 6)}:
        raise ValueError('Invalid target OCEAN trait/level')
    if type(fixed_level) is not int or fixed_level not in range(1, 6):
        raise ValueError('Invalid fixed personality level')
    if not isinstance(trait_instruction, str):
        raise ValueError('Missing target trait instruction')
    if any(x not in VERIFIED_CAPS for x in active_caps) or len(set(active_caps)) != len(active_caps):
        raise ValueError('Unverified or duplicated CAPS selection; CAPS-002..004 are blocked')
    definitions = ocean_levels()
    if definitions[trait][target_level] != trait_instruction:
        raise ValueError('Target OCEAN wording differs from committed locked definition')
    entries = common_rules()
    parts = [
        'You are Willow, a soft conversational companion robot for older adults.',
        'Instruction priority: FOUND > CONV > OCEAN > CAPS. Follow explicit user requests when compatible with these instructions.',
        '\nFOUNDATIONAL RULES:',
    ]
    parts += [f'{key}: {text}' for key, text in entries if key.startswith('FOUND-')]
    parts += ['\nCONVERSATIONAL RULES:']
    parts += [f'{key}: {text}' for key, text in entries if key.startswith('CONV-')]
    parts += ['\nPERSONALITY RULES:']
    for key in TRAITS:
        selected = target_level if key == trait else f'{key}-{fixed_level}'
        definition = definitions[key][selected]
        parts.append(f'OCEAN {TRAITS[key]} ({selected}): {definition}')
    if active_caps:
        parts += ['\nCONDITIONAL EXPRESSIVE ADAPTATIONS:']
        parts += [f'{key}: {dict(entries)[key]}' for key in active_caps]
    return '\n'.join(parts)


def create_messages(variables, *, trait=None):
    trait = trait or variables.get('trait')
    target_level = variables['target_level']
    target_text = variables.get('trait_instruction', variables.get('openness_instruction'))
    if not isinstance(target_text, str):
        raise ValueError('Missing OCEAN target instruction')
    system = build_system_prompt(trait, target_level, target_text)
    history = variables.get('history', [])
    if not isinstance(history, list) or any(
        not isinstance(m, dict) or m.get('role') not in ('user', 'assistant')
        or not isinstance(m.get('content'), str) for m in history
    ):
        raise ValueError('Invalid conversation history')
    if not isinstance(variables.get('message'), str):
        raise ValueError('Missing user message')
    return [{'role': 'system', 'content': system}, *history,
            {'role': 'user', 'content': variables['message']}]