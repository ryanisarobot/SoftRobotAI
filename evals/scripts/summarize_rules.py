"""Summarize individual FOUND, CONV, CAPS Promptfoo results; no network calls."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAMILY_COUNTS = {'FOUND': 5, 'CONV': 20, 'CAPS': 4}
SCORES = (0.0, 0.25, 0.50, 0.75, 1.0)
EXCLUSIONS = ('NOT_APPLICABLE:', 'INSUFFICIENT_CONTEXT:')


def load_rows(path):
    if path.suffix.lower() == '.jsonl':
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    else:
        body = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(body, dict):
            body = body.get('results', body)
            if isinstance(body, dict):
                body = body.get('results', body.get('outputs'))
        rows = body
    if not isinstance(rows, list) or not all(isinstance(x, dict) for x in rows):
        raise ValueError('Unsupported Promptfoo JSON export format')
    return rows


def interpret_grade(row, target_rule):
    result = row.get('gradingResult')
    if not isinstance(result, dict):
        return {'status':'error','score':None,'reason':'No gradingResult'}
    expected_metric = target_rule.replace('-', '_')+'_Fidelity'
    components = result.get('componentResults') or []
    if components:
        candidates = [c for c in components if isinstance(c, dict)
                      and isinstance(c.get('assertion'), dict)
                      and c['assertion'].get('metric') == expected_metric]
        if len(candidates) == 1:
            chosen = candidates[0]
        elif len(components) == 1 and components[0].get('assertion',{}).get('type') == 'llm-rubric':
            chosen = components[0]
        else:
            return {'status':'error','score':None,'reason':f'Missing/ambiguous {expected_metric}'}
    else:
        chosen = result
    value = chosen.get('score', result.get('score'))
    try:
        score = float(value)
    except (TypeError,ValueError):
        return {'status':'error','score':None,'reason':'Missing or invalid score'}
    if not any(abs(score - x) < 1e-8 for x in SCORES):
        return {'status':'error','score':None,'reason':f'Non-discrete rubric score: {score}'}
    reason = str(chosen.get('reason') or result.get('reason') or '')
    if not reason.strip():
        return {'status':'error','score':None,'reason':'Missing evidence-based reason'}
    if reason.startswith(EXCLUSIONS):
        return {'status':'excluded','score':score,'reason':reason,'passed':None}
    return {'status':'applicable','score':score,'reason':reason,'passed':score >= 0.75}


def parse_row(row, family):
    case = row.get('testCase') or {}
    variables = row.get('vars') or case.get('vars') or {}
    metadata = case.get('metadata') or row.get('metadata') or {}
    if not isinstance(variables, dict) or not isinstance(metadata, dict):
        raise ValueError('Invalid test case variables / metadata')
    rule = variables.get('target_rule') or metadata.get('rule_id')
    sid = variables.get('scenario_id') or metadata.get('scenario_id')
    allowed = {f'{family}-{i:03d}' for i in range(1,FAMILY_COUNTS[family]+1)}
    if rule not in allowed or sid not in (f'{rule}-01',f'{rule}-02'):
        raise ValueError(f'Unexpected rule/scenario for {family}: {rule}, {sid}')
    response = row.get('response') or {}
    output = response.get('output') if isinstance(response, dict) else response
    if output is None:
        output = row.get('text')
    grade = interpret_grade(row,rule)
    if row.get('error') or (isinstance(response,dict) and response.get('error')) or output is None or output == '':
        grade = {'status':'error','score':None,'reason':'Model error or missing response'}
    return {'rule_id':rule,'scenario_id':sid,'kind':metadata.get('kind'),
            'grade':grade,'output':output}


def aggregate(rows, family, *, rule=None):
    rules = [f'{family}-{i:03d}' for i in range(1,FAMILY_COUNTS[family]+1)]
    if rule is not None:
        if rule not in rules:
            raise ValueError(f'Unknown rule {rule} for {family}')
        rules = [rule]
    stats = {rule:{'eligible':0,'passes':0,'not_applicable':0,'insufficient_context':0,
                   'errors':0,'scores':[],'cases':[]} for rule in rules}
    issues = []
    counts = defaultdict(int)
    for raw in rows:
        item = parse_row(raw, family)
        rule, sid, grade = item['rule_id'],item['scenario_id'],item['grade']
        if rule not in stats:
            raise ValueError(f'Unexpected {rule} in filtered run')
        counts[sid]+=1
        entry = stats[rule]
        entry['cases'].append({'scenario_id':sid, 'status':grade['status'],
                               'score':grade.get('score'), 'reason':grade['reason']})
        if grade['status']=='error':
            entry['errors']+=1
        elif grade['status']=='excluded':
            key='not_applicable' if grade['reason'].startswith('NOT_APPLICABLE:') else 'insufficient_context'
            entry[key]+=1
        else:
            entry['eligible']+=1
            entry['passes']+=int(grade['passed'])
            entry['scores'].append(grade['score'])
    for rule, entry in stats.items():
        scores=entry.pop('scores')
        entry['mean_score']=round(sum(scores)/len(scores),4) if scores else None
        entry['pass_rate']=round(entry['passes']/entry['eligible'],4) if entry['eligible'] else None
        if not counts.get(rule+'-01') or not counts.get(rule+'-02'):
            issues.append(f'{rule}: one or both scenarios missing from the export')
    if any(x['errors'] for x in stats.values()):
        issues.append('One or more cases contain errors or invalid grader scores')
    return stats, issues


def report(summary):
    lines=[f"# Willow {summary['family']} individual rule pilot",'',
           f"Input: `{summary['source']}`",f"Analyzed: {summary['analyzed_at']}",'',
           'Excluded applicability markers are **not** counted as passes.','',
           '| Rule | Eligible | Passes | Pass rate | Mean score | N/A | Insufficient | Errors |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for rule,x in summary['rules'].items():
        rate='—' if x['pass_rate'] is None else f"{100*x['pass_rate']:.1f}%"
        mean='—' if x['mean_score'] is None else f"{x['mean_score']:.2f}"
        lines.append(f"| {rule} | {x['eligible']} | {x['passes']} | {rate} | {mean} | {x['not_applicable']} | {x['insufficient_context']} | {x['errors']} |")
    lines+=['','## Integrity checks','']
    lines += [f'- {issue}' for issue in summary['issues']] or ['No parse or completeness issues detected.']
    lines+=['','This small pilot evaluates rule compliance using two targeted fixtures per rule.',
            'It does not establish prompt-specific causal effects, longitudinal consistency, or clinical efficacy.','']
    return '\n'.join(lines)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family',choices=list(FAMILY_COUNTS),required=True)
    parser.add_argument('--rule',help='Optional single rule for filtered export')
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args(argv)
    if not args.input.is_file():
        parser.error(f'Missing Promptfoo results: {args.input}')
    rows=load_rows(args.input)
    stats,issues=aggregate(rows,args.family,rule=args.rule)
    summary={'family':args.family,'source':str(args.input),
             'analyzed_at':datetime.now(timezone.utc).isoformat(),
             'response_count':len(rows),'rules':stats,'issues':issues}
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (args.output_dir/'report.md').write_text(report(summary),encoding='utf-8')
    print(f"Analyzed {len(rows)} {args.family} results. Report: {args.output_dir/'report.md'}")
    return 0 if not issues else 2


if __name__=='__main__':
    raise SystemExit(main())