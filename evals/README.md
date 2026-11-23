# Willow Promptfoo evaluations

This folder runs **independent prompt-level tests** for Willow. It does not modify the deployed Streamlit study in `../website/` or the compatibility entry point in `../SoftRobotAI/`.

## One-time setup on Windows

1. Install Git for Windows if needed, and make sure `promptfoo --version` works in CMD.
2. Clone `https://github.com/ryanisarobot/SoftRobotAI.git` into your user folder (or pull an existing clone).
3. Open `SoftRobotAI\evals` in File Explorer.
4. Copy `.env.example` to a **new local file** named `.env`. Replace the placeholder value with your OpenAI API key. Do not commit or share `.env` (the repository is currently public).
5. Double-click `run-tests.cmd`. It runs the test suite and opens the Promptfoo browser results viewer. Leave the command window open.
6. Later, double-click `view-results.cmd` to inspect results without running tests again.

The launchers require Promptfoo to be accessible in CMD. If your Node installation is managed by `fnm` and `promptfoo` cannot be found in a new CMD window, initialize `fnm` or configure its shell startup first.

## Maintaining the tests

- `promptfooconfig.yaml` defines the provider and test selection (currently `openai:gpt-4o-mini`).
- `prompts/willow.json` holds an **initial** subset of FOUND and CONV instructions.
- `tests/foundational.yaml` contains six starter scenarios and simple assertions.
- `run-tests.cmd` runs evaluations and opens the browser.
- `view-results.cmd` opens saved results.
- `.env.example` illustrates the local API key file; `.env` is gitignored.

The committed prompt is **not** yet dynamically sourced from the full Willow runtime, which is not present in this repository. Replace the duplicated instructions with a real runtime adapter when that code is available. The tests are basic smoke tests, not validated measures of loneliness reduction or conversational quality.

Never commit API keys, sensitive user/participant transcripts, or private evaluation exports. API calls incur provider charges.

## Behavioral rubrics

Rubrics are organized by prompt module while preserving each rule's identifier:

- `rubrics/FOUND/FOUND-001.txt` through `rubrics/FOUND/FOUND-005.txt`
- `rubrics/CONV/CONV-001.txt` through `rubrics/CONV/CONV-020.txt`
- `rubrics/CAPS/CAPS-001.txt` through `rubrics/CAPS/CAPS-004.txt`
- CAPS-001 includes its verified original instruction. CAPS-002 through CAPS-004 are approved evaluation rubrics using explicitly marked working paraphrases, pending recovery of their verbatim locked instruction text. Do not treat those paraphrases as canonical instructions.
- Future modules can use `rubrics/OCEAN/` and `rubrics/MEM/`.

Each rubric is intended to be supplied as `{{rubric}}` in `graders/judge-prompt.txt`. The judge defines the shared scoring scale, pass/fail conventions, and JSON output contract. The existing `promptfooconfig.yaml` and `tests/foundational.yaml` remain starter smoke tests; they do not yet automatically load these rubric files.
