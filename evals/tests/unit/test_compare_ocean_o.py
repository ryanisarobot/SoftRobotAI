"""Offline contract checks; does not contact providers or incur API charges."""
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[2] / "scripts" / "compare_ocean_o.py"
spec = importlib.util.spec_from_file_location("compare_ocean_o", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sample_rows():
    rows = []
    for sid in mod.EXPECTED:
        for level in mod.LEVELS:
            score = 0.75
            reason = "Appropriately calibrated for this level"
            if (sid, level) == ("O-007", "O-2"):
                score, reason = 1.0, "NOT_APPLICABLE: Only narrow instructions"
            vars_ = {"scenario_id": sid, "target_level": level,
                     "message": f"Same message for {sid}", "history": [],
                     "openness_instruction": f"Instruction for {level}"}
            metadata = {"scenario_id": sid, "target_level": level,
                        "kind": "diagnostic" if sid in mod.DIAGNOSTIC else "constraint"}
            rows.append({"vars": vars_, "testCase": {"metadata": metadata},
                         "prompt": f"SYSTEM: shared. OCEAN Openness ({level}): Instruction for {level}\nUSER: {vars_['message']}",
                         "provider": {"id": "openai:gpt-4o-mini"},
                         "response": {"output": f"Response from {level} on {sid}"},
                         "gradingResult": {"score": score, "pass": True, "reason": reason,
                           "componentResults": [{"score": score, "reason": reason,
                              "assertion": {"type": "llm-rubric", "metric": "OCEAN_O_Fidelity"}}]}})
    return rows


class TestCrossLevelPipeline(unittest.TestCase):
    def test_complete_matrix_and_exclusion(self):
        rows = sample_rows()
        groups, issues = mod.build_groups(rows)
        self.assertEqual(len(groups), 8)
        self.assertEqual(issues, [])
        self.assertTrue(mod.cross_ready(groups, issues)[0])
        report = mod.summarize_individual(rows)
        self.assertEqual(report["O-2"]["excluded_not_applicable"], 1)
        self.assertEqual(report["O-2"]["eligible"], 7)
        self.assertEqual(report["O-2"]["passes"], 7)
        self.assertEqual(report["O-1"]["eligible"], 8)

    def test_missing_level_prevents_judging(self):
        rows = [item for item in sample_rows() if not (
            item["vars"]["scenario_id"] == "O-003" and item["vars"]["target_level"] == "O-4")]
        groups, issues = mod.build_groups(rows)
        self.assertEqual(len(groups), 7)
        self.assertFalse(mod.cross_ready(groups, issues)[0])

    def test_nontarget_prompt_change_prevents_judging(self):
        rows = sample_rows()
        rows[0]["prompt"] += " (extra instruction)"
        groups, issues = mod.build_groups(rows)
        self.assertFalse(mod.cross_ready(groups, issues)[0])

    def test_missing_prompt_prevents_judging(self):
        rows = sample_rows()
        del rows[0]["prompt"]
        groups, issues = mod.build_groups(rows)
        self.assertFalse(mod.cross_ready(groups, issues)[0])

    def test_mismatched_context_prevents_judging(self):
        rows = sample_rows()
        rows[0]["vars"]["message"] = "Different user scenario"
        groups, issues = mod.build_groups(rows)
        self.assertFalse(mod.cross_ready(groups, issues)[0])

    def test_judge_contract_with_mocked_api(self):
        rows = sample_rows()
        groups, issues = mod.build_groups(rows)
        self.assertTrue(mod.cross_ready(groups, issues)[0])
        fake_response = {"choices": [{"message": {"content": json.dumps({
            "reason": "O-001 and O-002 show progressive exploratory detail across levels.",
            "score": 0.75, "pass": True
        })}}]}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "rubrics" / "OCEAN").mkdir(parents=True)
            (root / "graders").mkdir()
            (root / "rubrics" / "OCEAN" / "OCEAN-O-CROSS.txt").write_text("Approved rubric")
            (root / "graders" / "cross-level-judge.txt").write_text("Cross-level judge instructions")
            with patch.object(mod, "ROOT", root), patch.object(mod, "load_env_key", return_value="dummy"), \
                 patch.object(mod, "urlopen", return_value=BytesIO(json.dumps(fake_response).encode())) as send:
                result = mod.judge_cross(groups, "gpt-4.1-mini", root / ".env", 20)
                self.assertTrue(result["pass"])
                self.assertEqual(result["distinct_diagnostic_scenarios"], 6)
                self.assertEqual(result["scenario_count"], 6)
                posted = json.loads(send.call_args.args[0].data)
                self.assertEqual(len(posted["messages"]), 2)
                self.assertIn("O-5", posted["messages"][1]["content"])
                self.assertNotIn("O-007", posted["messages"][1]["content"])

    def test_json_envelopes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.json"
            for doc in ({"version": 3, "results": {"results": sample_rows()}},
                        {"version": 3, "results": {"outputs": sample_rows()}}):
                path.write_text(json.dumps(doc), encoding="utf-8")
                entries, ts = mod.load_rows(path)
                self.assertEqual(len(entries), 40)

    def test_cli_dry_run_writes_report(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source = folder / "input.json"
            source.write_text(json.dumps({"version": 3, "results": {"results": sample_rows()}}),
                              encoding="utf-8")
            out = folder / "reports"
            code = mod.main(["--input", str(source), "--output-dir", str(out)])
            self.assertEqual(code, 0)
            saved = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(saved["cross_ready"])
            self.assertEqual(saved["complete_groups"], 8)
            self.assertIsNone(saved["cross_level"])
            self.assertIn("O-5", (out / "report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()