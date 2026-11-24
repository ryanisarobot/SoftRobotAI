# Willow verified prompt-library integration

## Active instructions in the OCEAN testing harness

The shared `prompts/willow_library.py` assembles the system instructions for each OCEAN comparison from the committed rubric files. It does **not** overwrite the starter `prompts/willow.json` or deployed Streamlit study.

- **FOUND-001..005**: all five verbatim original instructions.
- **CONV-001..020**: all twenty verbatim original instructions.
- **OCEAN**: one selected locked level (1–5) per trait; **the four non-target traits are held at level 3**. Only the target trait varies within the five-level comparison.
- **CAPS-001**: one verified conditional celebratory expression instruction, identical in every test. Its activation still depends on the user's message; it is not a universal command to celebrate.
- **CAPS-002..004**: intentionally **not loaded**. Their committed rubrics contain provisional paraphrases rather than recovered verbatim locked instructions. The loader rejects attempts to activate them instead of silently promoting a paraphrase to a canonical instruction.
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

1. Recover exact original CAPS-002, CAPS-003, and CAPS-004 wording and incorporate it only after verification; until then, full CAPS integration is blocked.
2. Exercise one live Promptfoo run and confirm the JSON export format, individual rubric integration, and cross-level comparisons end-to-end.
3. Extend realistic generated multi-turn and repeat-run testing; fixed conversation history is not a generated multi-turn session.
4. Integrate full FOUND/CONV/CAPS individual-rule test suites, distinct from this controlled OCEAN comparison.

The user requested a consolidated operating-instructions printout only after the work in this chat is finished. Do not treat this technical note as that final printout.