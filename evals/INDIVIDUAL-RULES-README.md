# Individual FOUND / CONV / CAPS evaluation pilot

The shared OCEAN harness compares personality levels. This separate harness tests compliance with one approved behavioral rubric at a time while **every approved FOUND/CONV/CAPS instruction and all five median OCEAN levels are held fixed** in the Willow prompt.

## Coverage

- FOUND: 5 rubric IDs, 2 scenario fixtures each = 10 responses per single repetition.
- CONV: 20 rubric IDs, 2 scenario fixtures each = 40 responses.
- CAPS: 4 rubric IDs, 2 scenario fixtures each = 8 responses.
- Total initial individual suite: 58 responses and 58 individual LLM-judge evaluations per repetition.

Scenarios are in `tests/rules/found.yaml`, `tests/rules/conv.yaml`, and `tests/rules/caps.yaml`. They include a target opportunity, a user message, and optional **fixed supplied** conversation history. Some exercise explicit boundaries. They are an **initial pilot**, not a complete or validated behavioral test battery; live multi-turn dialogues and wider coverage remain future work.

The generator loads the full, approved `rubrics/FOUND`, `rubrics/CONV`, and `rubrics/CAPS` files **without altering their criteria**, appends explicit scenario context, and assigns one `llm-rubric` assertion per test. Judge criteria use `graders/judge-prompt.txt` with score 0.00 / 0.25 / 0.50 / 0.75 / 1.00 and threshold 0.75.

`prompts/rules.py` produces an identical complete Willow prompt for every individual test: FOUND-001..005, CONV-001..020, CAPS-001..004, O-3/C-3/E-3/A-3/N-3. This measures rule compliance **within the complete prompt**, not the causal effect of including/removing a particular rule.

## Windows execution (after pulling latest GitHub changes)

From `SoftRobotAI/evals`, ensure Python, PyYAML, Node/Promptfoo, and local `.env` containing OPENAI_API_KEY are configured.

Start with one cheap two-case rule pilot:

    run-tests-rules.cmd FOUND FOUND-001
    analyze-rules.cmd FOUND FOUND-001

For a full family (do not run all three simultaneously because the generated tests file is shared):

    run-tests-rules.cmd FOUND
    analyze-rules.cmd FOUND

Replace FOUND with CONV or CAPS. The runner writes `output/rules_FAMILY_results.json`; the analyzer writes `output/rules_FAMILY_analysis/summary.json` and `report.md`. A single-rule filtered export has a `_<RULE-ID>` filename suffix. Filtered runs analyze only the selected rule and do not count unexecuted rules as missing scenarios.

No API calls occur when generating tests or analyzing an existing export; Promptfoo evaluation incurs model and grader charges. Exclusions with `NOT_APPLICABLE:` or `INSUFFICIENT_CONTEXT:` are not counted as behavioral passes even though the grader compatibility JSON reports `pass=true`. `output/` and `.env` are ignored by Git; do not upload participant data.

## Current validation limits

The generator and summarizer have offline tests. **No live Promptfoo run has yet been verified**, so the first two-case pilot must confirm actual JSON export paths, rendered judge prompts, and scoring behavior before scaling up. Run offline tests from `evals`:

    python -m unittest discover -s tests/unit -v

The final consolidated operating instructions are deferred until all implementation work in the conversation is completed.