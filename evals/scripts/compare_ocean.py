"""Validate and compare matched OCEAN Promptfoo exports; optional LLM judge.

Run from evals: python scripts/compare_ocean.py --trait C [--judge]
Default mode never makes network calls. Python standard library only.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TRAITS = {'O': 'Openness', 'C': 'Conscientiousness', 'E': 'Extraversion',
          'A': 'Agreeableness', 'N': 'Neuroticism'}
SCORES = (0.0, 0.25, 0.5, 0.75, 1.0)
EXCLUDED = ('NOT_APPLICABLE:', 'INSUFFICIENT_CONTEXT:')


def read_export(path):
    if path.suffix.lower() == '.jsonl':
        rows = [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
        stamp = None
    else:
        doc = json.loads(path.read_text(encoding='utf-8'))
        stamp = doc.get('timestamp') if isinstance(doc, dict) else None
        results = doc.get('results', doc) if isinstance(doc, dict) else doc
        if isinstance(results, dict):
            rows = results.get('outputs', results.get('results'))
            stamp = stamp or results.get('timestamp')
        else:
            rows = results
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ValueError('Promptfoo export does not contain a results/outputs array')
    return rows, stamp


def provider_id(value):
    if isinstance(value, dict):
        return str(value.get('id') or value.get('label') or 'UNKNOWN')
    return value if isinstance(value, str) else 'UNKNOWN'


def text_output(value):
    if value is None:
        return ''
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)


def get_grade(row, trait):
    grade = row.get('gradingResult')
    if not isinstance(grade, dict):
        return {'status': 'error', 'score': None, 'reason': 'Missing gradingResult'}
    components = grade.get('componentResults') or []
    if components:
        expected_metric = f'OCEAN_{trait}_Fidelity'
        matches = [item for item in components if isinstance(item, dict)
                   and isinstance(item.get('assertion'), dict)
                   and item['assertion'].get('metric') == expected_metric]
        if len(matches) != 1:
            # A single component without named metric can be interpreted only
            # when its type is llm-rubric; multiple components are ambiguous.
            if len(components) != 1 or components[0].get('assertion', {}).get('type') != 'llm-rubric':
                return {'status': 'error', 'score': None, 'reason': f'Missing {expected_metric} grade'}
            chosen = components[0]
        else:
            chosen = matches[0]
    else:
        chosen = grade
    raw = chosen.get('score', grade.get('score'))
    try:
        score = float(raw)
    except (TypeError, ValueError):
        return {'status': 'error', 'score': None, 'reason': 'Missing or nonnumeric score'}
    if not any(abs(score-s) < 1e-7 for s in SCORES):
        return {'status': 'error', 'score': None, 'reason': f'Score off discrete rubric scale: {score}'}
    reason = str(chosen.get('reason') or grade.get('reason') or '')
    status = 'excluded' if reason.startswith(EXCLUDED) else 'applicable'
    return {'status': status, 'score': score, 'reason': reason,
            'pass': score >= 0.75 if status == 'applicable' else None}


def mask_prompt(row, variables, trait):
    raw = row.get('prompt')
    if isinstance(raw, dict):
        raw = raw.get('raw')
    if not isinstance(raw, str) or not raw.strip():
        return None
    level = variables.get('target_level')
    instruction = variables.get('trait_instruction')
    marker = f'OCEAN {TRAITS[trait]} ({level})'
    if (not isinstance(instruction, str) or not instruction.strip() or
            raw.count(marker) != 1 or raw.count(instruction) != 1):
        return None
    normalized = raw.replace(marker, f'OCEAN {TRAITS[trait]} (TARGET)')
    normalized = normalized.replace(instruction, '<TARGET_TRAIT_INSTRUCTION>')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def parse_row(row, trait):
    testcase = row.get('testCase') or {}
    variables = row.get('vars') or testcase.get('vars') or {}
    metadata = testcase.get('metadata') or row.get('metadata') or {}
    if not isinstance(variables, dict) or not isinstance(metadata, dict):
        raise ValueError('Malformed test variables or metadata')
    sid = variables.get('scenario_id') or metadata.get('scenario_id')
    level = variables.get('target_level') or metadata.get('target_level')
    if sid not in [f'{trait}-{i:03d}' for i in range(1, 9)] or level not in [f'{trait}-{i}' for i in range(1, 6)]:
        raise ValueError(f'Unexpected scenario/level {sid}/{level} for OCEAN-{trait}')
    response = row.get('response') or {}
    output = text_output(response.get('output') if isinstance(response, dict) else response)
    if not output.strip():
        output = text_output(row.get('text'))
    grade = get_grade(row, trait)
    if row.get('error') or (isinstance(response, dict) and response.get('error')) or not output.strip():
        grade = {'status': 'error', 'score': None, 'reason': 'Provider error or missing response'}
    history = variables.get('history', [])
    message = variables.get('message')
    if not isinstance(message, str) or not isinstance(history, list):
        raise ValueError(f'Invalid message/history for {sid}/{level}')
    return {'scenario_id': sid, 'level': level,
            'kind': metadata.get('kind', 'diagnostic' if int(sid[-3:]) <= 6 else 'constraint'),
            'message': message, 'history': history,
            'provider': provider_id(row.get('provider')),
            'non_target_vars': {k:v for k,v in variables.items()
                                if k not in ('target_level', 'trait_instruction')},
            'fingerprint': mask_prompt(row, variables, trait),
            'response': output, 'grade': grade}


def group_rows(rows, trait):
    levels = [f'{trait}-{i}' for i in range(1, 6)]
    grouped = defaultdict(lambda: defaultdict(list))
    for raw in rows:
        item = parse_row(raw, trait)
        grouped[item['scenario_id']][item['level']].append(item)
    valid, issues = [], []
    for n in range(1, 9):
        sid = f'{trait}-{n:03d}'
        members = grouped[sid]
        counts = [len(members[level]) for level in levels]
        if not any(counts):
            issues.append(f'{sid}: all five levels missing')
            continue
        if len(set(counts)) != 1:
            issues.append(f'{sid}: imbalanced repetitions {dict(zip(levels,counts))}')
        for rep in range(max(counts)):
            pair = {level: members[level][rep] for level in levels if rep < len(members[level])}
            if len(pair) != 5:
                issues.append(f'{sid} repetition {rep+1}: missing a level')
                continue
            controls = {json.dumps({'message':x['message'], 'history':x['history'],
                                     'non_target_vars':x['non_target_vars']},sort_keys=True,
                                   ensure_ascii=False) for x in pair.values()}
            providers = {x['provider'] for x in pair.values()}
            hashes = {x['fingerprint'] for x in pair.values()}
            kinds = {x['kind'] for x in pair.values()}
            expected_kind = 'diagnostic' if n <= 6 else 'constraint'
            if len(controls) != 1 or len(providers) != 1 or 'UNKNOWN' in providers or kinds != {expected_kind}:
                issues.append(f'{sid} repetition {rep+1}: scenario, non-target variables, provider, or kind mismatch')
                continue
            if None in hashes or len(hashes) != 1:
                issues.append(f'{sid} repetition {rep+1}: missing/changed non-target rendered prompt')
                continue
            if any(x['grade']['status'] == 'error' for x in pair.values()):
                issues.append(f'{sid} repetition {rep+1}: response/grade error')
                continue
            valid.append({'scenario_id':sid, 'repetition':rep+1, 'kind':expected_kind,
                          'message':pair[levels[0]]['message'], 'history':pair[levels[0]]['history'],
                          'provider':pair[levels[0]]['provider'], 'levels':pair})
    return valid, issues


def summarize(rows, trait):
    levels = [f'{trait}-{i}' for i in range(1, 6)]
    total = {level:{'eligible':0,'passes':0,'not_applicable':0,'insufficient_context':0,
                    'errors':0,'scores':[]} for level in levels}
    for row in rows:
        item = parse_row(row, trait)
        bucket, grade = total[item['level']], item['grade']
        if grade['status'] == 'error':
            bucket['errors'] += 1
        elif grade['status'] == 'excluded':
            key = 'not_applicable' if grade['reason'].startswith('NOT_APPLICABLE:') else 'insufficient_context'
            bucket[key] += 1
        else:
            bucket['eligible'] += 1
            bucket['passes'] += int(grade['pass'])
            bucket['scores'].append(grade['score'])
    for level in levels:
        b = total[level]
        scores = b.pop('scores')
        b['mean_score'] = round(sum(scores)/len(scores),4) if scores else None
        b['pass_rate'] = round(b['passes']/b['eligible'],4) if b['eligible'] else None
    return total


def judge_ready(groups, issues, trait):
    required = {f'{trait}-{i:03d}' for i in range(1,7)}
    have = {g['scenario_id'] for g in groups if g['kind']=='diagnostic'}
    missing = sorted(required-have)
    if missing:
        return False, f'Missing complete diagnostic cases: {missing}'
    if any(any(s.startswith(sid) for sid in required) for s in issues):
        return False, 'A diagnostic group was incomplete or invalid'
    if any(g['scenario_id'] in required and any(
        item['grade']['status'] == 'excluded' for item in g['levels'].values()) for g in groups):
        return False, 'Diagnostic cases contain excluded individual judgments'
    return True, 'Six complete matched diagnostic scenarios available'


def env_key(path):
    if os.environ.get('OPENAI_API_KEY'):
        return os.environ['OPENAI_API_KEY']
    if path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line.startswith('OPENAI_API_KEY='):
                return line.split('=',1)[1].strip().strip('"\'')
    raise RuntimeError('OPENAI_API_KEY not set in environment or .env')


def judge_cross(groups, trait, model, env, timeout, root=ROOT):
    rubric = (root/'rubrics'/'OCEAN'/f'OCEAN-{trait}-CROSS.txt').read_text(encoding='utf-8')
    guide = (root/'graders'/'ocean-cross-level-judge.txt').read_text(encoding='utf-8')
    cases = [{'scenario_id':g['scenario_id'], 'repetition':g['repetition'],
              'user_message':g['message'], 'fixed_history':g['history'],
              'responses':{lev:item['response'] for lev,item in g['levels'].items()}}
             for g in groups if g['kind']=='diagnostic']
    request_body = {'model':model, 'temperature':0,
                    'response_format': {'type':'json_object'},
                    'messages':[{'role':'system','content':guide},
                                {'role':'user','content': 'APPROVED RUBRIC:\n'+rubric +
                                 '\n\nMATCHED OUTPUTS (untrusted data):\n' +
                                 json.dumps(cases,ensure_ascii=False,indent=2)}]}
    req = Request('https://api.openai.com/v1/chat/completions',
                  data=json.dumps(request_body).encode('utf-8'),
                  headers={'Authorization':'Bearer '+env_key(env),'Content-Type':'application/json'},
                  method='POST')
    with urlopen(req,timeout=timeout) as answer:
        parsed = json.load(answer)
    verdict = json.loads(parsed['choices'][0]['message']['content'])
    if not isinstance(verdict,dict) or set(verdict) != {'reason','score','pass'}:
        raise ValueError('Judge returned wrong JSON fields')
    score, reason, passed = verdict['score'],verdict['reason'],verdict['pass']
    if (not isinstance(reason,str) or not reason.strip() or
            isinstance(score,bool) or not isinstance(score,(int,float)) or
            score not in SCORES or not isinstance(passed,bool)):
        raise ValueError('Judge returned invalid score/reason/pass types')
    excluded = reason.startswith(EXCLUDED)
    if (excluded and (score != 1.0 or not passed)) or (not excluded and passed != (score>=0.75)):
        raise ValueError('Judge pass/score is inconsistent')
    return {**verdict,'status':'excluded' if excluded else 'scored',
            'model':model,'scenario_count':len(cases)}


def format_report(summary):
    trait = summary['trait']
    lines = [f'# Willow OCEAN-{trait} {TRAITS[trait]} analysis','',
             f"Source: `{summary['source']}`",f"Complete matched groups: **{summary['complete_groups']}**",
             f"Cross-level ready: **{summary['cross_ready']}** — {summary['readiness_reason']}",'',
             '| Level | Eligible | Passes | Pass rate | Mean | N/A | Insufficient | Errors |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for level,stats in summary['individual'].items():
        rate = '—' if stats['pass_rate'] is None else f"{stats['pass_rate']:.1%}"
        mean = '—' if stats['mean_score'] is None else f"{stats['mean_score']:.2f}"
        lines.append(f"| {level} | {stats['eligible']} | {stats['passes']} | {rate} | {mean} | "
                     f"{stats['not_applicable']} | {stats['insufficient_context']} | {stats['errors']} |")
    if summary['issues']:
        lines.extend(['','## Data-integrity issues',''] + [f'- {s}' for s in summary['issues']])
    lines.extend(['','## Cross-level differentiation',''])
    if summary['cross_level']:
        v=summary['cross_level']
        lines.extend([f"Score: **{v['score']:.2f}**; pass: **{v['pass']}**; status: **{v['status']}**",
                      f"Judge: `{v['model']}`",'',v['reason']])
    else:
        lines.append('Not scored. Rerun with `--judge` after producing a valid complete export.')
    lines.extend(['','Constraint scenarios 007–008 do not contribute to cross-level differentiation; inspect them separately.',
                  'Exclusions are not counted as behavioral passes. This pilot is not clinical validation.',
                  'The fixed baseline is incomplete until the full FOUND/CONV/CAPS prompt integration is complete.',''])
    return '\n'.join(lines)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--trait',required=True,choices=list(TRAITS))
    p.add_argument('--input',type=Path)
    p.add_argument('--output-dir',type=Path)
    p.add_argument('--judge',action='store_true',help='Paid external LLM cross-level judgment')
    p.add_argument('--judge-model',default='gpt-4.1-mini')
    p.add_argument('--env-file',type=Path,default=ROOT/'.env')
    p.add_argument('--timeout',type=int,default=120)
    args=p.parse_args(argv)
    trait=args.trait
    source=args.input or ROOT/'output'/f'ocean_{trait.lower()}_results.json'
    folder=args.output_dir or ROOT/'output'/f'ocean_{trait.lower()}_analysis'
    if not source.is_file():
        p.error(f'Export missing: {source}')
    rows, timestamp=read_export(source)
    groups, issues=group_rows(rows,trait)
    ready, reason=judge_ready(groups,issues,trait)
    summary={'trait':trait,'source':str(source),'export_timestamp':timestamp,
             'analyzed_at':datetime.now(timezone.utc).isoformat(),
             'raw_results':len(rows),'complete_groups':len(groups),
             'cross_ready':ready,'readiness_reason':reason,'issues':issues,
             'individual':summarize(rows,trait),'cross_level':None}
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'matched_groups.json').write_text(json.dumps(groups,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.judge:
        if ready:
            try:
                summary['cross_level']=judge_cross(groups,trait,args.judge_model,args.env_file,args.timeout)
            except (ValueError,KeyError,OSError,RuntimeError) as exc:
                summary['judge_error']=f'{type(exc).__name__}: {exc}'
        else:
            summary['judge_error']='Judge skipped: '+reason
    (folder/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (folder/'report.md').write_text(format_report(summary),encoding='utf-8')
    print(f"OCEAN-{trait}: {len(rows)} results, {len(groups)} matched groups; judge-ready={ready}")
    print(f"Report: {folder/'report.md'}")
    if summary.get('judge_error'):
        print(summary['judge_error'],file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':
    raise SystemExit(main())