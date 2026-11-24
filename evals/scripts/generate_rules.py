"""Generate individual FOUND, CONV, or CAPS Promptfoo cases from approved rubrics.

From evals/: python scripts/generate_rules.py --family FOUND [--rule FOUND-001]
No model calls. Requires PyYAML.
"""

import argparse
import json
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
COUNTS = {'FOUND': 5, 'CONV': 20, 'CAPS': 4}


def build_tests(family, *, rule=None, root=ROOT):
    if family not in COUNTS:
        raise ValueError(f'Unknown family: {family}')
    expected = [f'{family}-{i:03d}' for i in range(1, COUNTS[family]+1)]
    if rule is not None and rule not in expected:
        raise ValueError(f'{rule} does not belong to {family}')
    scenarios = yaml.safe_load((root / 'tests' / 'rules' / f'{family.lower()}.yaml').read_text(encoding='utf-8'))
    if not isinstance(scenarios, list) or len(scenarios) != 2 * len(expected):
        raise ValueError(f'Expected {2*len(expected)} {family} scenarios')
    ids = [x['metadata']['scenario_id'] for x in scenarios]
    all_ids = [f'{name}-{suffix:02d}' for name in expected for suffix in (1,2)]
    if ids != all_ids:
        raise ValueError(f'{family} scenario identifiers/order do not match the approved rule set')
    result = []
    for scenario in scenarios:
        meta = scenario['metadata']
        rid, sid = meta['rule_id'], meta['scenario_id']
        if meta['family'] != family or meta['kind'] not in ('diagnostic','boundary'):
            raise ValueError(f'Invalid scenario metadata for {sid}')
        if rule and rid != rule:
            continue
        variables = scenario['vars']
        message = variables.get('message')
        history = variables.get('history', [])
        if not isinstance(message, str) or not message.strip():
            raise ValueError(f'Missing message for {sid}')
        if not isinstance(history, list) or any(
            not isinstance(x, dict) or x.get('role') not in ('user','assistant')
            or not isinstance(x.get('content'), str)
            for x in history
        ):
            raise ValueError(f'Invalid history for {sid}')
        rubric = (root / 'rubrics' / family / f'{rid}.txt').read_text(encoding='utf-8')
        if f'RULE ID: {rid}' not in rubric.splitlines()[:4] or 'EVALUATION OBJECTIVE' not in rubric:
            raise ValueError(f'Invalid approved rubric for {rid}')
        if 'Exact locked instruction wording not recovered' in rubric:
            raise ValueError(f'Unresolved original instruction for {rid}')
        history_text = '\n'.join(f"{x['role']}: {x['content']}" for x in history) or '(No prior conversation)'
        value = (rubric + '\n\nSCENARIO CONTEXT\n'
                 f'RULE UNDER TEST: {rid}\nSCENARIO ID: {sid}\n'
                 f'SCENARIO CATEGORY: {meta["kind"]}\n'
                 f'OPPORTUNITY: {meta["opportunity"]}\n'
                 f'FIXED PRIOR MESSAGES:\n{history_text}\n')
        result.append({
            'description': scenario['description'],
            'metadata': {**meta, 'suite': f'{family}-INDIVIDUAL', 'profile': 'willow-all-rules-ocean-3'},
            'vars': {'message': message, 'history': history, 'target_rule': rid,
                     'scenario_id': sid, 'profile': 'willow-all-rules-ocean-3'},
            'options': {'disableVarExpansion': True},
            'assert': [{'type': 'llm-rubric', 'metric': rid.replace('-', '_')+'_Fidelity',
                        'threshold': 0.75, 'value': value}],
        })
    if len(result) != (2 if rule else 2 * len(expected)):
        raise ValueError(f'Invalid selected scenario count for {family}/{rule}')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', choices=list(COUNTS), required=True)
    parser.add_argument('--rule', help='Optional single rule, e.g. CONV-005')
    parser.add_argument('--output', type=Path, default=ROOT/'output'/'rules_tests.json')
    args = parser.parse_args(argv)
    tests = build_tests(args.family, rule=args.rule)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(tests, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Generated {len(tests)} {args.family} individual-rule cases: {args.output}')


if __name__ == '__main__':
    main()