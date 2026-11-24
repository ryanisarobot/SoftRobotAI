# Willow verified prompt-library integration

## Active instructions in the OCEAN testing harness

The shared `prompts/willow_library.py` assembles the system instructions for each OCEAN comparison from the committed rubric files. It does **not** overwrite the starter `prompts/willow.json` or deployed Streamlit study.

- **FOUND-001..005**: all five verbatim original instructions.
- **CONV-001..020**: all twenty verbatim original instructions.
- **OCEAN**: one selected locked level (1–5) per trait; **the four non-target traits are held at level 3**. Only the target trait varies within the five-level comparison.
- **CAPS-001..004**: all four approved conditional expressive rules, identical across matched OCEAN levels. CAPS-002..004 use newly approved canonical wording (2026-11-23), rather than claiming to have recovered lost historical wording. Their activation depends on user context.
- **FOUND-006**: provisional and not activated.

Order is FOUND > CONV > OCEAN > CAPS, following the established design precedence. The same baseline and fixed OCEAN controls are applied to all five target levels. The target wording is verified against the committed OCEAN rubric, and the existing analysis script checks that rendered prompts differ only in the target definition.

The two OCEAN Promptfoo entry points now share the same assembler:

- `prompts/ocean.py` — generic five-trait suite (`run-tests-ocean.cmd`)
- `prompts/ocean_o.py` — legacy Openness pilot (`run-tests-ocean-o.cmd`)

The new profile is **not directly equivalent** to earlier partial-baseline pilot results. Do not combine historical runs using the partial baseline with full-library runs in the same aggregate comparison. Preserve the commit hash and profile when comparing future exports.

## Validation

Run the offline checks from `evals`:

    python -m unittest discover -s tests/unit -v

Then run one real Openness pilot and inspect its export before interpreting fidelity or cross-level scores. Promptfoo model and judge requests incur API costs.

## Remaining work

1. Exercise one live Promptfoo run and confirm the JSON export format, individual rubric integration, and cross-level comparisons end-to-end.
2. Extend realistic generated multi-turn and repeat-run testing; fixed conversation history is not a generated multi-turn session.
3. Integrate full FOUND/CONV/CAPS individual-rule test suites, distinct from this controlled OCEAN comparison.

The user requested a consolidated operating-instructions printout only after the work in this chat is finished. Do not treat this technical note as that final printout.