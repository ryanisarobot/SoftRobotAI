# Willow LLM evaluations

This directory contains Promptfoo tests for Willow's conversation behavior. It is independent of the Streamlit pilot in `../website/`; do not replace `website/prompts.json` with these instructions.

## Getting started (Windows CMD)

1. Clone the repository or pull its latest changes to your computer.
2. Open CMD in the repository's `evals` directory.
3. Ensure Promptfoo is installed (`promptfoo --version`).
4. Set an OpenAI API key for this terminal only: `set OPENAI_API_KEY=your-key` (do not commit the key).
5. Run `promptfoo eval`, then `promptfoo view` to inspect results in your browser.

Run `promptfoo view` alone to inspect previously saved results.

## Contents

- `promptfooconfig.yaml`: selected model and test suite.
- `prompts/willow.json`: Willow's initial conversational developer instructions.
- `tests/foundational.yaml`: starter input scenarios and objective assertions.

## Important limitations

This is a standalone **prompt-level** harness, not yet a test of Willow's actual Python runtime, audio pipeline, memory, OCEAN selectors, or CAPS controller. The current GitHub repository primarily contains the Streamlit pilot application. Once the runtime is committed, connect Promptfoo to the real prompt assembly and model provider so there is a single source of truth.

The included prompt file contains the currently agreed foundational and conversational instructions only; it is not the full, finalized runtime prompt. The tests are initial smoke checks, not a validated assessment of companionship quality, loneliness reduction, or safety.

Keep API tokens, identifiable participant conversations, raw transcripts, and generated evaluation exports out of this public repository.
