"""Build the 8 x 5 matched Openness pilot from approved scenarios and rubric.

Usage (from evals/): python scripts/generate_ocean_o.py
Requires: pip install PyYAML
This script makes no API calls. It writes the generated test matrix to ignored output/.
"""

import json
import re
from pathlib import Path

import yaml

EVALS_DIR = Path(__file__).resolve().parents[1]
SCENARIOS_FILE = EVALS_DIR / "tests" / "ocean" / "openness.yaml"
RUBRIC_FILE = EVALS_DIR / "rubrics" / "OCEAN" / "OCEAN-O.txt"
OUTPUT_FILE = EVALS_DIR / "output" / "ocean_o_tests.json"
LEVELS = [f"O-{number}" for number in range(1, 6)]


def get_locked_levels(rubric):
    """Extract verbatim O-1..O-5 text from the existing approved rubric."""
    original = rubric.split("ORIGINAL INSTRUCTIONS", 1)[1].split(
        "EVALUATION OBJECTIVE", 1
    )[0]
    found = dict(re.findall(r"(?m)^(O-[1-5]):\s*(.+?)\s*$", original))
    if set(found) != set(LEVELS):
        raise ValueError(f"Expected the five locked O-levels, found: {sorted(found)}")
    return found


def build_tests():
    scenarios = yaml.safe_load(SCENARIOS_FILE.read_text(encoding="utf-8"))
    rubric = RUBRIC_FILE.read_text(encoding="utf-8")
    instructions = get_locked_levels(rubric)

    if not isinstance(scenarios, list) or len(scenarios) != 8:
        raise ValueError("Expected exactly eight approved scenarios")
    ids = [item["metadata"]["scenario_id"] for item in scenarios]
    if len(ids) != len(set(ids)):
        raise ValueError("Scenario IDs must be unique")

    tests = []
    for scenario in scenarios:
        meta = scenario["metadata"]
        sid = meta["scenario_id"]
        message = scenario["vars"]["message"]
        history = scenario["vars"].get("history", [])
        if not isinstance(history, list) or any(
            not isinstance(turn, dict)
            or turn.get("role") not in ("user", "assistant")
            or not isinstance(turn.get("content"), str)
            for turn in history
        ):
            raise ValueError(f"Invalid fixed history for {sid}")
        history_text = "\n".join(
            f"{turn['role']}: {turn['content']}" for turn in history
        ) or "(No prior turns supplied)"

        for level in LEVELS:
            individual_rubric = (
                rubric
                + f"\n\nTEST CONFIGURATION\nASSIGNED TARGET LEVEL: {level}\n"
                + f"SCENARIO ID: {sid}\n"
                + f"SCENARIO TYPE: {meta['kind']}\n"
                + "FIXED CONVERSATION HISTORY:\n"
                + history_text
                + "\n"
            )
            tests.append(
                {
                    "description": f"{sid} | {level} | {scenario['description']}",
                    "metadata": {**meta, "target_level": level, "suite": "OCEAN-O"},
                    "vars": {
                        "message": message,
                        "history": history,
                        "target_level": level,
                        "openness_instruction": instructions[level],
                        "scenario_id": sid,
                    },
                    "options": {"disableVarExpansion": True},
                    "assert": [
                        {
                            "type": "llm-rubric",
                            "metric": "OCEAN_O_Fidelity",
                            "threshold": 0.75,
                            "value": individual_rubric,
                        }
                    ],
                }
            )
    return tests


def main():
    tests = build_tests()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(tests, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Generated {len(tests)} tests at {OUTPUT_FILE}")
    print("8 matched scenarios x 5 levels; no API calls made.")


if __name__ == "__main__":
    main()
