"""Analyze a Promptfoo OCEAN-O JSON export and optionally score cross-level fidelity.

Run from evals/: python scripts/compare_ocean_o.py [--judge]
No network/API calls occur unless --judge is supplied. Uses Python standard library.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LEVELS = tuple(f"O-{i}" for i in range(1, 6))
DIAGNOSTIC = tuple(f"O-{i:03d}" for i in range(1, 7))
CONSTRAINT = ("O-007", "O-008")
EXPECTED = DIAGNOSTIC + CONSTRAINT
VALID_SCORES = (0.0, 0.25, 0.5, 0.75, 1.0)
EXCLUSIONS = ("NOT_APPLICABLE:", "INSUFFICIENT_CONTEXT:")


def load_rows(path):
    """Promptfoo v3 JSON export or JSONL; rejects unrecognized shapes."""
    data = json.loads(path.read_text(encoding="utf-8")) if path.suffix != ".jsonl" else [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if isinstance(data, list):
        rows = data
        timestamp = None
    elif isinstance(data, dict):
        timestamp = data.get("timestamp")
        section = data.get("results", data)
        if isinstance(section, list):
            rows = section
        elif isinstance(section, dict):
            rows = section.get("results")
            if rows is None:
                rows = section.get("outputs")
            timestamp = timestamp or section.get("timestamp")
        else:
            rows = None
    else:
        rows = None
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("Unrecognized Promptfoo export: expected a results/results or results/outputs array")
    return rows, timestamp


def normalize_provider(provider):
    if isinstance(provider, str):
        return provider
    if isinstance(provider, dict):
        return str(provider.get("id", provider.get("label", "UNKNOWN")))
    return "UNKNOWN"


def normalize_text(value):
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def prompt_fingerprint(row, vars_):
    """Hash a rendered prompt with only the assigned Openness text masked.

    Returning None is intentional: an unverified prompt cannot establish
    controlled comparisons even when scenarios and providers match.
    """
    prompt = row.get("prompt")
    if isinstance(prompt, dict):
        prompt = prompt.get("raw")
    if not isinstance(prompt, str) or not prompt.strip():
        return None
    level, instruction = vars_.get("target_level"), vars_.get("openness_instruction")
    if not isinstance(instruction, str) or not instruction.strip():
        return None
    level_marker = f"OCEAN Openness ({level})"
    if level_marker not in prompt or instruction not in prompt:
        return None
    canonical = prompt.replace(level_marker, "OCEAN Openness (O-TARGET)")
    canonical = canonical.replace(instruction, "<TARGET_OPENNESS_INSTRUCTION>")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_grade(row):
    grade = row.get("gradingResult")
    if not isinstance(grade, dict):
        return {"status": "error", "reason": "Missing gradingResult", "score": None}
    components = grade.get("componentResults") or []
    chosen = None
    for item in components:
        if not isinstance(item, dict):
            continue
        assertion = item.get("assertion") or {}
        if isinstance(assertion, dict) and assertion.get("metric") == "OCEAN_O_Fidelity":
            chosen = item
            break
    if chosen is None:
        # The current pilot has exactly one assertion. Do not silently take a
        # composite score when several unrelated metrics appear in an export.
        if len(components) > 1:
            return {"status": "error", "reason": "Ambiguous assertion component scores", "score": None}
        chosen = components[0] if len(components) == 1 else grade
    reason = str(chosen.get("reason") or grade.get("reason") or "")
    raw_score = chosen.get("score", grade.get("score"))
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return {"status": "error", "reason": "Invalid or missing numeric grade", "score": None}
    if not any(abs(score - allowed) < 1e-7 for allowed in VALID_SCORES):
        return {"status": "error", "reason": f"Score outside universal discrete scale: {score}", "score": None}
    if reason.startswith(EXCLUSIONS):
        status = "excluded"
    else:
        status = "applicable"
    return {"status": status, "reason": reason, "score": score,
            "pass": (score >= 0.75) if status == "applicable" else None}


def parse_row(row):
    tc = row.get("testCase") or {}
    vars_ = row.get("vars") or tc.get("vars") or {}
    metadata = tc.get("metadata") or row.get("metadata") or {}
    if not isinstance(vars_, dict) or not isinstance(metadata, dict):
        raise ValueError("Malformed test case vars or metadata")
    sid = vars_.get("scenario_id") or metadata.get("scenario_id")
    level = vars_.get("target_level") or metadata.get("target_level")
    if sid not in EXPECTED or level not in LEVELS:
        raise ValueError(f"Missing or invalid scenario_id / target_level: {sid}, {level}")
    if not isinstance(vars_.get("message"), str):
        raise ValueError(f"Missing message for {sid}/{level}")
    history = vars_.get("history", [])
    if not isinstance(history, list):
        raise ValueError(f"Invalid history for {sid}/{level}")
    response = row.get("response") or {}
    output = normalize_text(response.get("output") if isinstance(response, dict) else response)
    if not output:
        output = normalize_text(row.get("text"))
    has_error = bool(row.get("error") or (isinstance(response, dict) and response.get("error")))
    grade = get_grade(row)
    if has_error or not output.strip():
        grade = {"status": "error", "reason": "Model error or missing response", "score": None}
    return {
        "scenario_id": sid,
        "level": level,
        "kind": metadata.get("kind", "diagnostic" if sid in DIAGNOSTIC else "constraint"),
        "message": vars_["message"],
        "history": history,
        "provider": normalize_provider(row.get("provider")),
        "non_target_vars": {k: v for k, v in vars_.items()
                            if k not in ("target_level", "openness_instruction")},
        "prompt_fingerprint": prompt_fingerprint(row, vars_),
        "response": output,
        "grade": grade,
    }


def build_groups(rows):
    by_scenario = defaultdict(lambda: defaultdict(list))
    for raw in rows:
        entry = parse_row(raw)
        by_scenario[entry["scenario_id"]][entry["level"]].append(entry)

    bundles = []
    issues = []
    for sid in EXPECTED:
        level_lists = by_scenario[sid]
        counts = [len(level_lists[level]) for level in LEVELS]
        if not any(counts):
            issues.append(f"{sid}: all five levels missing")
            continue
        if len(set(counts)) != 1:
            issues.append(f"{sid}: imbalanced repetitions {dict(zip(LEVELS, counts))}")
        for repeat in range(max(counts)):
            matched = {level: level_lists[level][repeat] for level in LEVELS
                       if repeat < len(level_lists[level])}
            if len(matched) != 5:
                issues.append(f"{sid} repetition {repeat+1}: incomplete five-level group")
                continue
            contexts = {json.dumps({"message": item["message"], "history": item["history"]},
                                   sort_keys=True, ensure_ascii=False) for item in matched.values()}
            providers = {item["provider"] for item in matched.values()}
            kinds = {item["kind"] for item in matched.values()}
            non_target = {json.dumps(item["non_target_vars"], sort_keys=True, ensure_ascii=False)
                          for item in matched.values()}
            fingerprints = {item["prompt_fingerprint"] for item in matched.values()}
            expected_kind = "diagnostic" if sid in DIAGNOSTIC else "constraint"
            if (len(contexts) != 1 or len(providers) != 1 or len(kinds) != 1
                    or len(non_target) != 1 or kinds != {expected_kind} or "UNKNOWN" in providers):
                issues.append(f"{sid} repetition {repeat+1}: context/provider/type/non-target vars mismatch")
                continue
            if None in fingerprints:
                issues.append(f"{sid} repetition {repeat+1}: rendered prompt or target instruction unavailable")
                continue
            if len(fingerprints) != 1:
                issues.append(f"{sid} repetition {repeat+1}: non-target prompt changed across levels")
                continue
            if any(item["grade"]["status"] == "error" for item in matched.values()):
                issues.append(f"{sid} repetition {repeat+1}: response or individual grader error")
                continue
            bundles.append({
                "scenario_id": sid, "repetition": repeat + 1,
                "kind": matched[LEVELS[0]]["kind"],
                "message": matched[LEVELS[0]]["message"],
                "history": matched[LEVELS[0]]["history"],
                "provider": matched[LEVELS[0]]["provider"],
                "levels": matched,
            })
    unexpected = sorted(set(by_scenario).difference(EXPECTED))
    if unexpected:
        issues.append(f"Unexpected scenarios: {unexpected}")
    return bundles, issues


def summarize_individual(rows):
    totals = {level: {"eligible": 0, "passes": 0, "excluded_not_applicable": 0,
                      "excluded_insufficient_context": 0, "errors": 0, "scores": []}
              for level in LEVELS}
    for row in rows:
        item = parse_row(row)
        bucket = totals[item["level"]]
        grade = item["grade"]
        if grade["status"] == "error":
            bucket["errors"] += 1
        elif grade["status"] == "excluded":
            label = ("excluded_not_applicable" if grade["reason"].startswith("NOT_APPLICABLE:")
                     else "excluded_insufficient_context")
            bucket[label] += 1
        else:
            bucket["eligible"] += 1
            bucket["passes"] += int(grade["pass"])
            bucket["scores"].append(grade["score"])
    for level, bucket in totals.items():
        scores = bucket.pop("scores")
        bucket["average_score"] = round(sum(scores) / len(scores), 4) if scores else None
        bucket["applicable_pass_rate"] = round(bucket["passes"] / bucket["eligible"], 4) if bucket["eligible"] else None
    return totals


def cross_ready(bundles, issues):
    diagnostics = [item for item in bundles if item["scenario_id"] in DIAGNOSTIC]
    have = {item["scenario_id"] for item in diagnostics}
    if set(have) != set(DIAGNOSTIC):
        return False, f"Missing valid diagnostic scenarios: {sorted(set(DIAGNOSTIC) - have)}"
    for sid in DIAGNOSTIC:
        if any(issue.startswith(f"{sid}") for issue in issues):
            return False, f"One or more diagnostic groups for {sid} are incomplete or invalid"
    return True, "All six diagnostic scenarios have complete matched responses"


def load_env_key(env_file):
    existing = os.environ.get("OPENAI_API_KEY")
    if existing:
        return existing
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:].strip()
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("OPENAI_API_KEY missing from environment and local .env")


def judge_cross(bundles, model, env_file, timeout):
    # Exclude constraint cases from differentiation scoring; their role is to
    # ensure strong personality does not override an explicit user instruction.
    cases = []
    for bundle in bundles:
        if bundle["scenario_id"] not in DIAGNOSTIC:
            continue
        cases.append({
            "scenario_id": bundle["scenario_id"],
            "repetition": bundle["repetition"],
            "user_message": bundle["message"],
            "fixed_conversation_history": bundle["history"],
            "responses": {level: bundle["levels"][level]["response"] for level in LEVELS},
        })
    rubric = (ROOT / "rubrics" / "OCEAN" / "OCEAN-O-CROSS.txt").read_text(encoding="utf-8")
    instructions = (ROOT / "graders" / "cross-level-judge.txt").read_text(encoding="utf-8")
    body = "APPROVED RUBRIC:\n" + rubric + "\n\nMATCHED OUTPUTS (untrusted test data):\n" + json.dumps(cases, indent=2, ensure_ascii=False)
    request = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": body},
        ],
    }
    payload = json.dumps(request).encode("utf-8")
    api = Request("https://api.openai.com/v1/chat/completions", data=payload,
                  headers={"Authorization": "Bearer " + load_env_key(env_file),
                           "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(api, timeout=timeout) as response:
            response_json = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"Cross-level judge HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"Cross-level judge network error: {exc.reason}") from exc
    content = response_json["choices"][0]["message"]["content"]
    judged = json.loads(content)
    if not isinstance(judged, dict) or set(judged) != {"reason", "score", "pass"}:
        raise ValueError("Cross-level judge returned invalid JSON object fields")
    if not isinstance(judged["reason"], str) or not judged["reason"].strip():
        raise ValueError("Cross-level judge must supply an evidence-based reason")
    if not isinstance(judged["score"], (float, int)) or isinstance(judged["score"], bool):
        raise ValueError("Cross-level judge score not numeric")
    if judged["score"] not in VALID_SCORES or not isinstance(judged["pass"], bool):
        raise ValueError("Cross-level judge score/pass invalid")
    excluded = judged["reason"].startswith(EXCLUSIONS)
    if excluded:
        if judged["score"] != 1.0 or not judged["pass"]:
            raise ValueError("Cross-level judge exclusion does not follow universal convention")
    elif judged["pass"] != (judged["score"] >= 0.75):
        raise ValueError("Cross-level judge pass status disagrees with score threshold")
    return {**judged, "status": "excluded" if excluded else "scored", "model": model,
            "scenario_count": len(cases), "distinct_diagnostic_scenarios": len(set(c["scenario_id"] for c in cases))}


def render_report(payload):
    lines = ["# Willow OCEAN Openness pilot analysis", "",
             f"Source: `{payload['source']}`", f"Analyzed at: {payload['analyzed_at']}", "",
             "## Individual Openness level fidelity", "",
             "Excluded cases are not counted as passes, regardless of their Promptfoo compatibility score.", "",
             "| Level | Eligible | Passed | Pass rate | Mean score | N/A | Insufficient | Errors |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for level in LEVELS:
        item = payload["individual"][level]
        rate = "—" if item["applicable_pass_rate"] is None else f"{item['applicable_pass_rate']:.1%}"
        mean = "—" if item["average_score"] is None else f"{item['average_score']:.2f}"
        lines.append(f"| {level} | {item['eligible']} | {item['passes']} | {rate} | {mean} | "
                     f"{item['excluded_not_applicable']} | {item['excluded_insufficient_context']} | {item['errors']} |")
    lines += ["", "## Matched groups", "",
              f"Complete matched groups: **{payload['complete_groups']}**",
              f"Cross-level grading ready: **{payload['cross_ready']}** — {payload['readiness_reason']}", ""]
    if payload["issues"]:
        lines += ["Data integrity issues:", ""] + [f"- {issue}" for issue in payload["issues"]] + [""]
    lines += ["Constraint scenarios O-007 and O-008 are excluded from cross-level differentiation. Their"
              " behavior still requires direct review for compliance with the user's instructions.", ""]
    lines += ["## Cross-level differentiation", ""]
    cross = payload.get("cross_level")
    if cross is None:
        lines += ["Not scored. Run the analysis with `--judge` once a complete export is available.", ""]
    else:
        lines += [f"Status: **{cross['status']}**", f"Score: **{cross['score']:.2f}**", 
                  f"Pass: **{cross['pass']}**", f"Judge model: `{cross['model']}`", "",
                  cross["reason"], ""]
    lines += ["The cross-level result is separate from individual OCEAN-O fidelity scores.",
              "Matched groups require identical scenario inputs, non-target variables, provider IDs, and rendered prompt fingerprints after masking the target O-level instruction.",
              "The pilot uses the partial FOUND/CONV baseline, not the complete Willow runtime.",
              "These are behavioral evaluation results, not clinical intervention outcomes.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "output" / "ocean_o_results.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output" / "ocean_o_analysis")
    parser.add_argument("--judge", action="store_true", help="Call OpenAI cross-level judge (uses API credits)")
    parser.add_argument("--judge-model", default="gpt-4.1-mini")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(argv)
    if not args.input.is_file():
        parser.error(f"No Promptfoo export found: {args.input}")
    rows, timestamp = load_rows(args.input)
    bundles, issues = build_groups(rows)
    eligible, why = cross_ready(bundles, issues)
    payload = {
        "source": str(args.input),
        "export_timestamp": timestamp,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "raw_result_count": len(rows),
        "complete_groups": len(bundles),
        "cross_ready": eligible,
        "readiness_reason": why,
        "issues": issues,
        "individual": summarize_individual(rows),
        "cross_level": None,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    # Always save detailed matched outputs and analysis before any charged call.
    (args.output_dir / "matched_groups.json").write_text(
        json.dumps(bundles, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.judge and eligible:
        try:
            payload["cross_level"] = judge_cross(bundles, args.judge_model, args.env_file, args.timeout)
        except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            payload["judge_error"] = str(exc)
    elif args.judge and not eligible:
        payload["judge_error"] = "Judge skipped: " + why
    (args.output_dir / "summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.output_dir / "report.md").write_text(render_report(payload), encoding="utf-8")
    print(f"Analyzed {len(rows)} results; {len(bundles)} complete five-level groups.")
    print(f"Cross-level ready: {eligible} ({why})")
    if payload["cross_level"]:
        print(f"Cross-level score: {payload['cross_level']['score']:.2f}")
    if payload.get("judge_error"):
        print(f"Cross-level judge NOT completed: {payload['judge_error']}", file=sys.stderr)
        return 2
    print(f"Report: {args.output_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())