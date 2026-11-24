"""Generate one controlled five-level OCEAN Promptfoo matrix.

Example: python scripts/generate_ocean.py --trait C
Requires PyYAML. No model or network calls are made.
"""

import argparse
import json
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
TRAITS = {'O': 'openness', 'C': 'conscientiousness', 'E': 'extraversion',
          'A': 'agreeableness', 'N': 'neuroticism'}


def locked_instructions(trait, text):
    if 'ORIGINAL INSTRUCTIONS' not in text or 'EVALUATION OBJECTIVE' not in text:
        raise ValueError(f'OCEAN-{trait} rubric has missing section markers')
    section = text.split('ORIGINAL INSTRUCTIONS', 1)[1].split('EVALUATION OBJECTIVE', 1)[0]
    found = dict(re.findall(rf'(?m)^({trait}-[1-5]):\s*(.+?)\s*$', section))
    expected = {f'{trait}-{i}' for i in range(1, 6)}
    if set(found) != expected:
        raise ValueError(f'Expected locked {trait}-1..5, got {list(found)}')
    return found


def build_tests(trait, root=ROOT):
    if trait not in TRAITS:
        raise ValueError(f'Invalid trait: {trait}')
    scenarios = yaml.safe_load((root / 'tests' / 'ocean' /
                                f'{TRAITS[trait]}.yaml').read_text(encoding='utf-8'))
    rubric = (root / 'rubrics' / 'OCEAN' / f'OCEAN-{trait}.txt').read_text(encoding='utf-8')
    instructions = locked_instructions(trait, rubric)
    judge = (root / 'graders' / 'judge-prompt.txt').read_text(encoding='utf-8')
    if not isinstance(scenarios, list) or len(scenarios) != 8:
        raise ValueError(f'Expected eight scenarios for {trait}')
    ids = [s['metadata']['scenario_id'] for s in scenarios]
    expected = [f'{trait}-{i:03d}' for i in range(1, 9)]
    if ids != expected:
        raise ValueError(f'Scenario IDs must be {expected}, got {ids}')

    tests = []
    for i, scenario in enumerate(scenarios, 1):
        meta = scenario['metadata']
        sid = meta['scenario_id']
        if meta.get('trait') != trait or meta.get('family') != 'OCEAN':
            raise ValueError(f'Invalid metadata for {sid}')
        kind = 'diagnostic' if i <= 6 else 'constraint'
        if meta.get('kind') != kind:
            raise ValueError(f'Expected {kind} for {sid}')
        variables = scenario['vars']
        message = variables.get('message')
        history = variables.get('history', [])
        if not isinstance(message, str) or not message.strip():
            raise ValueError(f'Empty user message: {sid}')
        if not isinstance(history, list) or any(
            not isinstance(turn, dict) or turn.get('role') not in ('user','assistant')
            or not isinstance(turn.get('content'), str) for turn in history
        ):
            raise ValueError(f'Invalid history: {sid}')
        history_text = '\n'.join(f"{x['role']}: {x['content']}" for x in history) or '(No history)'
        for level in (f'{trait}-{k}' for k in range(1, 6)):
            value = (rubric + '\n\nTEST CONFIGURATION\n'
                     f'ASSIGNED TARGET LEVEL: {level}\nSCENARIO ID: {sid}\n'
                     f'SCENARIO TYPE: {kind}\nFIXED CONVERSATION HISTORY:\n{history_text}\n')
            tests.append({
                'description': f"{sid} | {level} | {scenario['description']}",
                'metadata': {**meta, 'target_level': level, 'suite': f'OCEAN-{trait}'},
                'vars': {'message': message, 'history': history, 'trait': trait,
                         'trait_name': TRAITS[trait].capitalize(),
                         'trait_instruction': instructions[level],
                         'target_level': level, 'scenario_id': sid},
                'options': {'disableVarExpansion': True},
                'assert': [{'type': 'llm-rubric', 'metric': f'OCEAN_{trait}_Fidelity',
                            'threshold': 0.75, 'value': value,
                            'rubricPrompt': judge}],
            })
    return tests


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trait', required=True, choices=list(TRAITS))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    target = args.output or ROOT / 'output' / f'ocean_{args.trait.lower()}_tests.json'
    matrix = build_tests(args.trait)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Generated {len(matrix)} matched cases for OCEAN-{args.trait}: {target}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())