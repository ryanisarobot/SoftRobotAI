# OCEAN five-trait matched Promptfoo testing

This is an **initial test-fixture expansion**, not a claim that the scenarios have been behaviorally validated. The previously approved Openness fixtures remain in `tests/ocean/openness.yaml`; the four new scenario sets are proposed diagnostic inputs for C/E/A/N and may be revised after review and live pilot results. Approved rubric files have **not** been changed.

## Coverage

| Trait | Scenario file | Level assignments | Individual rubric | Cross-level rubric |
| --- | --- | --- | --- | --- |
| O | `tests/ocean/openness.yaml` | O-1 ... O-5 | `OCEAN-O.txt` | `OCEAN-O-CROSS.txt` |
| C | `tests/ocean/conscientiousness.yaml` | C-1 ... C-5 | `OCEAN-C.txt` | `OCEAN-C-CROSS.txt` |
| E | `tests/ocean/extraversion.yaml` | E-1 ... E-5 | `OCEAN-E.txt` | `OCEAN-E-CROSS.txt` |
| A | `tests/ocean/agreeableness.yaml` | A-1 ... A-5 | `OCEAN-A.txt` | `OCEAN-A-CROSS.txt` |
| N | `tests/ocean/neuroticism.yaml` | N-1 ... N-5 | `OCEAN-N.txt` | `OCEAN-N-CROSS.txt` |

Each trait contains six diagnostic inputs and two constraint checks. Scenario 006 uses a **fixed supplied history**; it does not test a genuinely generated multi-turn conversation. Each scenario is run with all five levels and the same model and baseline. The assembler now supplies all five FOUND and twenty CONV verified rules, CAPS-001, and the four non-target OCEAN traits at level 3. Only the target OCEAN instruction changes between matched levels. CAPS-002..004 now use the exact newly approved canonical instructions; see `FULL-PROMPT-INTEGRATION.md`. Earlier partial-baseline runs are not directly comparable.

## Windows commands from `evals`

One-time: `python -m pip install PyYAML` and create local `.env` containing your OpenAI API key. Do not commit `.env`.

For a trait, run:

    run-tests-ocean.cmd C
    analyze-ocean.cmd C

Replace `C` with `O`, `E`, `A`, or `N`. `run-tests-ocean.cmd` makes paid target and individual-judge calls; `analyze-ocean.cmd` runs the paid cross-level judge after checking matched exports. **Do not automatically run all five traits until an individual trait run has been examined.**

To analyze **without any additional API calls**, run:

    python scripts\compare_ocean.py --trait C

Manual generation and evaluation:

    python scripts\generate_ocean.py --trait C --output output\ocean_tests.json
    promptfoo eval -c promptfooconfig.ocean.yaml --env-file .env --no-cache --output output\ocean_c_results.json

The Promptfoo configuration points to `output/ocean_tests.json`, which is overwritten by the last generator invocation. Do not run multiple trait batches concurrently against the same directory. The generated test matrix and all result exports are ignored by Git.

## Outputs

For trait `C`:

- `output/ocean_c_results.json` — Promptfoo exported candidate responses and individual grading details
- `output/ocean_c_analysis/matched_groups.json` — complete validated response groups
- `output/ocean_c_analysis/summary.json` — individual scores, exclusions, integrity diagnostics, cross-level verdict
- `output/ocean_c_analysis/report.md` — readable results

The individual grader loads `graders/judge-prompt.txt` into the assertion `rubricPrompt` when generating the matrix; the test rubric comes verbatim from the selected trait's approved `rubrics/OCEAN/OCEAN-X.txt`, with target-level metadata appended. The cross-level grader loads the approved `rubrics/OCEAN/OCEAN-X-CROSS.txt` unchanged.

`NOT_APPLICABLE:` and `INSUFFICIENT_CONTEXT:` are excluded from applicable pass rates; diagnostic exclusions block the cross-level scoring. Cross-level results are distinct from the individual compliance scores. No personality validity, statistically significant differentiation, or loneliness reduction can be inferred from this initial pilot.

## Validation and known limitations

    python -m unittest discover -s tests/unit -v

The new generic pipeline has passed seven synthetic offline tests with mock Promptfoo exports and a mock Chat Completions judge. It has **not** yet been exercised using real Promptfoo exports, real model responses, or a live LLM judge. Check provider and grade metadata on your first live export before interpreting the report.

The earlier Openness-specific launcher and analyzer remain available, and the legacy prompt entry point now uses the same verified library assembler. Once the first live export is verified, the generic scripts can replace that older pilot path. Do not commit the `output/` directory, API keys, or private user/participant conversations.