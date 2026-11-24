# OCEAN-O cross-level analysis

The approved rubric is `rubrics/OCEAN/OCEAN-O-CROSS.txt`. This is a separate evaluation from individual O-1 to O-5 fidelity.

## Run after the Promptfoo pilot

From `evals` (Windows):

    python scripts\compare_ocean_o.py

This **offline-only** command parses `output/ocean_o_results.json`, validates the matched groups, excludes NOT_APPLICABLE and INSUFFICIENT_CONTEXT from individual pass rates, and generates:

- `output/ocean_o_analysis/matched_groups.json`: the original paired responses and individual rubric scores
- `output/ocean_o_analysis/summary.json`: per-level pass rate, validation errors, and optional cross-level verdict
- `output/ocean_o_analysis/report.md`: readable summary of individual fidelity and cross-level differentiation

To perform the **paid LLM cross-level evaluation**, run `analyze-ocean-o.cmd` or:

    python scripts\compare_ocean_o.py --judge

Python sends a single batch of all six diagnostic scenarios (O-001 to O-006) with the five level-labeled outputs to the `gpt-4.1-mini` evaluator, using the approved cross-level rubric and `graders/cross-level-judge.txt`. Use `--judge-model MODEL` to change the judge. Python reads the API key from your environment or your uncommitted `evals/.env` file. The script refuses cross-level scoring if any diagnostic comparison group is missing, a model/individual grade failed, provider differs, scenario/history differs, or there is an unmatched non-target system prompt change.

O-007 and O-008 are constraint cases excluded from cross-level differentiation; their behavioral compliance still requires separate inspection/evaluation. O-006 uses fixed history, not genuine generated multiple-turn dialogue. All eight cases receive individual fidelity grades from Promptfoo; this script does not alter them.

For review without API cost, omit `--judge`; no networking occurs. This script uses only Python standard library. Automated offline unit tests:

    python -m unittest discover -s tests/unit -v

**Validation status:** synthetic Promptfoo v3 JSON exports and a mocked judge API were tested locally. Real Promptfoo exports and live API grading have **not** yet been tested; run the one-time live pilot and inspect JSON output. The current testing prompt contains FOUND-001..005, CONV-001..020, CAPS-001, and controlled OCEAN trait levels. CAPS-002..004 and full production-runtime integration remain pending.

Never commit the `.env` file, model outputs, study participant data, or the generated `output/` directory. Test conversations may be transmitted to an LLM evaluator when `--judge` is specified.