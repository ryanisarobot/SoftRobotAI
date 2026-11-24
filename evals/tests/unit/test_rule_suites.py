"""Offline validation for newly introduced individual-rule evaluation path."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]

def load_module(name,file):
    spec=importlib.util.spec_from_file_location(name,file)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

generate=load_module('generate_rules',ROOT/'scripts'/'generate_rules.py')
summarize=load_module('summarize_rules',ROOT/'scripts'/'summarize_rules.py')


class IndividualRuleTests(unittest.TestCase):
    def test_scenario_counts_and_ids(self):
        import yaml
        for fam,count in generate.COUNTS.items():
            rows=yaml.safe_load((ROOT/'tests'/'rules'/f'{fam.lower()}.yaml').read_text(encoding='utf-8'))
            self.assertEqual(len(rows),count*2)
            self.assertEqual(len(set(x['metadata']['scenario_id'] for x in rows)),count*2)
            self.assertTrue(all(x['metadata']['family']==fam for x in rows))
            self.assertTrue(all(x['vars']['message'].strip() for x in rows))

    def test_generate_using_canonical_fixture_rubrics(self):
        import yaml
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for family,count in generate.COUNTS.items():
                (root/'tests'/'rules').mkdir(parents=True,exist_ok=True)
                (root/'rubrics'/family).mkdir(parents=True,exist_ok=True)
                (root/'tests'/'rules'/f'{family.lower()}.yaml').write_text(
                    (ROOT/'tests'/'rules'/f'{family.lower()}.yaml').read_text(encoding='utf-8'),encoding='utf-8')
                for i in range(1,count+1):
                    rid=f'{family}-{i:03d}'
                    (root/'rubrics'/family/f'{rid}.txt').write_text(
                        f'RULE ID: {rid}\nORIGINAL INSTRUCTION:\nVerified instruction.\n\nEVALUATION OBJECTIVE\nAssess.\n',encoding='utf-8')
                tests=generate.build_tests(family,root=root)
                self.assertEqual(len(tests),count*2)
                self.assertEqual(tests[0]['assert'][0]['metric'],f'{family}_001_Fidelity')
                self.assertTrue(all(t['assert'][0]['threshold']==.75 for t in tests))
                self.assertTrue(all(t['options']['disableVarExpansion'] for t in tests))
                subset=generate.build_tests(family,rule=f'{family}-001',root=root)
                self.assertEqual(len(subset),2)

    def test_no_silent_placeholder_or_unknown_rule(self):
        with self.assertRaisesRegex(ValueError,'does not belong'):
            generate.build_tests('FOUND',rule='CAPS-001')

    def test_evaluator_export_and_exclusions(self):
        rows=[]
        for i in range(1,6):
            rid=f'FOUND-{i:03d}'
            for s in (1,2):
                reason='Target behavior demonstrated'
                score=.75
                if i==2 and s==2:
                    score,reason=1.,'NOT_APPLICABLE: Absent behavior opportunity'
                rows.append({'vars':{'target_rule':rid,'scenario_id':f'{rid}-{s:02d}'},
                             'testCase':{'metadata':{'kind':'diagnostic'}},
                             'response':{'output':f'Response for {rid}'},
                             'gradingResult':{'componentResults':[{'score':score,'reason':reason,
                                 'assertion':{'metric':f'FOUND_{i:03d}_Fidelity'}}]}})
        stats,issues=summarize.aggregate(rows,'FOUND')
        self.assertEqual(issues,[])
        self.assertEqual(stats['FOUND-002']['eligible'],1)
        self.assertEqual(stats['FOUND-002']['not_applicable'],1)
        self.assertEqual(stats['FOUND-002']['pass_rate'],1.0)
        selected, issues2=summarize.aggregate([x for x in rows if x["vars"]["target_rule"]=="FOUND-002"],"FOUND",rule="FOUND-002")
        self.assertEqual(issues2,[])
        self.assertEqual(list(selected),["FOUND-002"])
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'results.json'
            file.write_text(json.dumps({'results':{'results':rows}}),encoding='utf-8')
            self.assertEqual(len(summarize.load_rows(file)),10)

    def test_missing_scenario_is_reported(self):
        rows=[{'vars':{'target_rule':'CAPS-001','scenario_id':'CAPS-001-01'},
               'response':{'output':'Response'},
               'gradingResult':{'score':.75,'reason':'Target appropriate'}}]
        stats,issues=summarize.aggregate(rows,'CAPS')
        self.assertTrue(any('CAPS-001' in s for s in issues))


if __name__=='__main__':
    unittest.main()