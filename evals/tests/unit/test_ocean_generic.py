"""Synthetic offline checks for every OCEAN trait. Never makes API calls."""
from io import BytesIO
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

HERE = Path(__file__).resolve().parents[2]

def load(name):
    spec=importlib.util.spec_from_file_location(name,HERE/'scripts'/f'{name}.py')
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

gen=load('generate_ocean')
cmp=load('compare_ocean')


def sample(trait):
    rows=[]
    for n in range(1,9):
        sid=f'{trait}-{n:03d}'
        for i in range(1,6):
            level=f'{trait}-{i}'
            instruction=f'Locked instruction {level}'
            message=f'Fixed input {sid}'
            context={'message':message,'history':[],'trait':trait,
                     'trait_name':cmp.TRAITS[trait],'scenario_id':sid}
            variables={**context,'target_level':level,'trait_instruction':instruction}
            grade={'score':0.75,'reason':'Appropriate trait expression',
                   'componentResults':[{'score':0.75,'reason':'Appropriate trait expression',
                     'assertion':{'type':'llm-rubric','metric':f'OCEAN_{trait}_Fidelity'}}]}
            rows.append({'testCase':{'metadata':{'kind':'diagnostic' if n<=6 else 'constraint'},'vars':variables},
                         'prompt':f'OCEAN {cmp.TRAITS[trait]} ({level}): {instruction}; shared baseline',
                         'provider':{'id':'openai:gpt-4o-mini'},
                         'response':{'output':f'Answer {sid} {level}'},'gradingResult':grade})
    return rows


class TestGenericOCEAN(unittest.TestCase):
    def test_generator_all_traits(self):
        for trait in gen.TRAITS:
            with self.subTest(trait=trait), tempfile.TemporaryDirectory() as folder:
                root=Path(folder)
                (root/'tests'/'ocean').mkdir(parents=True)
                (root/'rubrics'/'OCEAN').mkdir(parents=True)
                (root/'graders').mkdir()
                file=(HERE/'tests'/'ocean'/f'{gen.TRAITS[trait]}.yaml')
                if not file.exists() and trait=='O':
                    raw=[]
                    for n in range(1,9):
                        raw.append({'description':f'{trait}-{n:03d}',
                            'metadata':{'scenario_id':f'{trait}-{n:03d}','trait':trait,'family':'OCEAN',
                            'kind':'diagnostic' if n<=6 else 'constraint'},
                            'vars':{'message':f'Scenario {n}'}})
                    file_text=yaml.safe_dump(raw)
                else:
                    file_text=file.read_text(encoding='utf-8')
                (root/'tests'/'ocean'/f'{gen.TRAITS[trait]}.yaml').write_text(file_text,encoding='utf-8')
                head='ORIGINAL INSTRUCTIONS\n\n'+''.join(
                    f'{trait}-{i}: Locked instruction {trait}-{i}\n' for i in range(1,6))+'\nEVALUATION OBJECTIVE'
                (root/'rubrics'/'OCEAN'/f'OCEAN-{trait}.txt').write_text(head,encoding='utf-8')
                (root/'graders'/'judge-prompt.txt').write_text('User: {{message}}\n{{output}}\n{{rubric}}',encoding='utf-8')
                cases=gen.build_tests(trait,root)
                self.assertEqual(len(cases),40)
                self.assertEqual({c['metadata']['scenario_id'] for c in cases},
                    {f'{trait}-{n:03d}' for n in range(1,9)})
                self.assertTrue(all(c['assert'][0]['rubricPrompt']=='User: {{message}}\n{{output}}\n{{rubric}}'
                        for c in cases))
                self.assertEqual(len({c['vars']['trait_instruction'] for c in cases}),5)

    def test_matched_outputs_and_statistics(self):
        for trait in cmp.TRAITS:
            with self.subTest(trait=trait):
                rows=sample(trait)
                groups,issues=cmp.group_rows(rows,trait)
                self.assertEqual(len(groups),8)
                self.assertFalse(issues)
                self.assertTrue(cmp.judge_ready(groups,issues,trait)[0])
                summary=cmp.summarize(rows,trait)
                self.assertEqual(summary[f'{trait}-2']['eligible'],8)
                self.assertEqual(summary[f'{trait}-2']['passes'],8)

    def test_reject_non_target_changes(self):
        rows=sample('N')
        rows[0]['prompt']+=' EXTRA INSTRUCTION'
        groups,issues=cmp.group_rows(rows,'N')
        self.assertFalse(cmp.judge_ready(groups,issues,'N')[0])

    def test_missing_level(self):
        rows=[r for r in sample('E') if not (
            r['testCase']['vars']['scenario_id']=='E-005' and
            r['testCase']['vars']['target_level']=='E-4')]
        groups,issues=cmp.group_rows(rows,'E')
        self.assertFalse(cmp.judge_ready(groups,issues,'E')[0])

    def test_exclusions_are_not_passes_and_block_cross_scoring(self):
        rows=sample('A')
        row=rows[0]
        component=row['gradingResult']['componentResults'][0]
        component['score']=1.0
        component['reason']='INSUFFICIENT_CONTEXT: Missing context'
        groups,issues=cmp.group_rows(rows,'A')
        self.assertFalse(cmp.judge_ready(groups,issues,'A')[0])
        info=cmp.summarize(rows,'A')
        self.assertEqual(info['A-1']['eligible'],7)
        self.assertEqual(info['A-1']['insufficient_context'],1)

    def test_run_cli_and_json_envelope(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'input.json'
            dest=Path(temp)/'analysis'
            source.write_text(json.dumps({'version':3,'results':{'outputs':sample('C')}}))
            self.assertEqual(cmp.main(['--trait','C','--input',str(source),'--output-dir',str(dest)]),0)
            result=json.loads((dest/'summary.json').read_text())
            self.assertTrue(result['cross_ready'])
            self.assertEqual(result['complete_groups'],8)
            self.assertTrue((dest/'report.md').is_file())

    def test_mocked_cross_judge(self):
        groups,issues=cmp.group_rows(sample('C'),'C')
        fake={'choices':[{'message':{'content':json.dumps({'reason':'Different degrees of planning across C-001 and C-002',
                                                      'score':0.75,'pass':True})}}]}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'rubrics'/'OCEAN').mkdir(parents=True)
            (root/'graders').mkdir()
            (root/'rubrics'/'OCEAN'/'OCEAN-C-CROSS.txt').write_text('Approved Conscientiousness rubric')
            (root/'graders'/'ocean-cross-level-judge.txt').write_text('Independent judge')
            with patch.object(cmp,'urlopen',return_value=BytesIO(json.dumps(fake).encode('utf-8'))) as call,\
                 patch.object(cmp,'env_key',return_value='redacted'):
                verdict=cmp.judge_cross(groups,'C','gpt-4.1-mini',root/'.env',15,root=root)
                self.assertEqual(verdict['status'],'scored')
                sent=json.loads(call.call_args.args[0].data)
                self.assertEqual(len(sent['messages']),2)
                self.assertIn('C-5',sent['messages'][1]['content'])
                self.assertNotIn('C-008',sent['messages'][1]['content'])

if __name__=='__main__':
    unittest.main()