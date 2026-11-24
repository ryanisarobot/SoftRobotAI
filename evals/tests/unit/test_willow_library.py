"""Offline contract checks for the verified Willow prompt assembler."""
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

FILE = Path(__file__).resolve().parents[2] / 'prompts' / 'willow_library.py'
spec = importlib.util.spec_from_file_location('willow_library', FILE)
library = importlib.util.module_from_spec(spec)
spec.loader.exec_module(library)


def make_rubrics(root):
    for group, count in (('FOUND', 5), ('CONV', 20), ('CAPS', 1)):
        path = root / 'rubrics' / group
        path.mkdir(parents=True, exist_ok=True)
        for n in range(1, count + 1):
            name = f'{group}-{n:03d}'
            (path / f'{name}.txt').write_text(
                f'RULE ID: {name}\nORIGINAL INSTRUCTION:\nVerified {name} rule.\n\n'
                'EVALUATION OBJECTIVE\nAssess it.\n', encoding='utf-8')
    path = root / 'rubrics' / 'OCEAN'
    path.mkdir(parents=True)
    for trait in library.TRAITS:
        body = '\n'.join(f'{trait}-{n}: Verified {trait}-{n} instruction.' for n in range(1, 6))
        (path / f'OCEAN-{trait}.txt').write_text(
            f'RULE ID: OCEAN-{trait}\nORIGINAL INSTRUCTIONS\n{body}\n\n'
            'EVALUATION OBJECTIVE\nAssess it.\n', encoding='utf-8')


class VerifiedLibraryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        make_rubrics(self.root)
        self.root_patch = patch.object(library, 'ROOT', self.root)
        self.root_patch.start()
        library.common_rules.cache_clear()
        library.ocean_levels.cache_clear()

    def tearDown(self):
        library.common_rules.cache_clear()
        library.ocean_levels.cache_clear()
        self.root_patch.stop()
        self.folder.cleanup()

    def test_exact_25_common_rules_and_conditional_caps(self):
        entries = library.common_rules()
        self.assertEqual(len(entries), 26)
        self.assertEqual(sum(k.startswith('FOUND-') for k, _ in entries), 5)
        self.assertEqual(sum(k.startswith('CONV-') for k, _ in entries), 20)
        self.assertEqual([k for k, _ in entries if k.startswith('CAPS-')], ['CAPS-001'])

    def test_all_25_locked_ocean_definitions(self):
        self.assertEqual(sum(map(len, library.ocean_levels().values())), 25)

    def test_only_target_level_changes_across_matched_set(self):
        outputs = []
        for n in range(1, 6):
            code = f'E-{n}'
            prompt = library.build_system_prompt('E', code, f'Verified E-{n} instruction.')
            self.assertEqual(prompt.count('OCEAN Extraversion (E-'), 1)
            self.assertEqual(prompt.count('CAPS-001: Verified CAPS-001 rule.'), 1)
            self.assertIn('OCEAN Openness (O-3): Verified O-3 instruction.', prompt)
            self.assertIn('OCEAN Neuroticism (N-3): Verified N-3 instruction.', prompt)
            prompt = re.sub(r'OCEAN Extraversion \(E-[1-5]\): Verified E-[1-5] instruction.',
                            'OCEAN Extraversion (E-TARGET): <TARGET>', prompt)
            outputs.append(prompt)
        self.assertEqual(len(set(outputs)), 1)

    def test_reject_unverified_caps_and_tampered_target(self):
        with self.assertRaisesRegex(ValueError, 'Unverified'):
            library.build_system_prompt('O', 'O-1', 'Verified O-1 instruction.',
                                        active_caps=['CAPS-002'])
        with self.assertRaisesRegex(ValueError, 'differs'):
            library.build_system_prompt('O', 'O-1', 'Paraphrase')

    def test_reject_placeholder_as_original(self):
        path = self.root / 'rubrics' / 'CAPS' / 'CAPS-002.txt'
        path.write_text('RULE ID: CAPS-002\nORIGINAL INSTRUCTION:\n'
                        '[Exact locked instruction wording not recovered.]\n\n'
                        'EVALUATION OBJECTIVE\nAssess.\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Noncanonical'):
            library.original_instruction('CAPS', 'CAPS-002')

    def test_history_and_legacy_target_variable(self):
        data = {'target_level': 'O-4', 'openness_instruction': 'Verified O-4 instruction.',
                'history': [{'role': 'user', 'content': 'Before'}], 'message': 'Now'}
        messages = library.create_messages(data, trait='O')
        self.assertEqual([row['role'] for row in messages], ['system','user','user'])
        self.assertEqual(messages[-1]['content'], 'Now')
        self.assertIn('OCEAN Openness (O-4)', messages[0]['content'])


if __name__ == '__main__':
    unittest.main()