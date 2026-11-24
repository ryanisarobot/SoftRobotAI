# OCEAN Openness pilot

This is the approved 8-scenario, 5-level matched comparison pilot (40 response-and-grade pairs per run). It is isolated from the existing starter tests.

## Run on Windows

1. In the evals folder, create a local .env from .env.example and set OPENAI_API_KEY (never commit it).
2. Ensure Python and Promptfoo are on PATH. Install PyYAML once: python -m pip install PyYAML.
3. Double-click run-tests-ocean-o.cmd. It generates output/ocean_o_tests.json, runs 40 cases, saves output/ocean_o_results.json, and opens the local viewer.

Manual commands from evals:

    python scripts\generate_ocean_o.py
    promptfoo eval -c promptfooconfig.ocean-o.yaml --env-file .env --no-cache --output output\ocean_o_results.json

The model under test is openai:gpt-4o-mini. The separate judge is openai:gpt-4.1-mini. API calls incur charges. Start with one repetition per scenario and level.

## Controlled comparison

The scenario source is tests/ocean/openness.yaml. The generator takes the five locked Openness instructions verbatim from the ORIGINAL INSTRUCTIONS section of rubrics/OCEAN/OCEAN-O.txt. The common prompt is the existing prompts/willow.json system text, held fixed in every condition. That baseline currently contains FOUND-001–005 and CONV-001 only. Full FOUND/CONV/CAPS and non-target OCEAN assembly remains pending. This pilot is not full-runtime validation.

Each scenario uses identical user input, any fixed conversation history, model and sampling settings across levels. Only the target Openness instruction changes. O-006 uses fixed prior turns; it is not a live multi-turn generated conversation.

Every response is graded by the approved OCEAN-O individual rubric, with its assigned level and any fixed history explicitly included for the judge. The judge uses graders/judge-prompt.txt and a threshold of 0.75.

## Exports and next phase

The generated 40-test matrix includes scenario_id, target_level and kind metadata. Promptfoo's full JSON results export preserves outputs and grading results. Both files go under the gitignored output/ directory.

The approved OCEAN-O-CROSS rubric is not run by this launcher; the separate Python comparison pipeline will group matched responses and run cross-level evaluation after exports have been validated.

The universal judge assigns pass=true with score=1.00 to NOT_APPLICABLE and INSUFFICIENT_CONTEXT cases for interface compatibility. The downstream analysis MUST exclude these from actual behavioral pass rates. Promptfoo's raw UI pass rate therefore is not the final reporting rate.

These files have been statically validated, not exercised against live OpenAI API models. Validate a local pilot before scaling up.
