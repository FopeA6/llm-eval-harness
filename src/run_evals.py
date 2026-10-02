#!/usr/bin/env python3
"""
Run the persona eval suite and write a JSON + Markdown report.

Usage:
    python src/run_evals.py                  # mock backend (default, no API key needed)
    python src/run_evals.py --backend anthropic --model claude-3-5-haiku-latest

Exit code is 1 if any case fails its rubric (so this is CI-friendly).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from model_client import get_client  # noqa: E402
from scorer import score_case  # noqa: E402

ROOT = Path(__file__).parent.parent


def load_cases() -> list[dict]:
    with open(ROOT / "cases" / "personas.json") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the persona eval suite.")
    parser.add_argument("--backend", choices=["mock", "anthropic"], default="mock")
    parser.add_argument("--model", default="claude-3-5-haiku-latest")
    args = parser.parse_args()

    client = get_client(args.backend)
    cases = load_cases()

    results = []
    for case in cases:
        response = client.generate(case["system_prompt"], case["prompt"], case["id"])
        results.append(score_case(case, response))

    total = len(results)
    passed = sum(1 for r in results if r.passed)

    print(f"\nPersona Eval Suite — backend: {args.backend}\n{'=' * 60}")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.case_id} ({r.persona}) — score {r.score:.2f}")
        for c in r.checks:
            mark = "  ok" if c.passed else "  ✗ "
            print(f"    {mark} {c.check_type}: {c.detail}")
    print(f"\n{passed}/{total} cases passed ({passed / total:.0%})\n")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "backend": args.backend,
        "summary": {"total": total, "passed": passed, "pass_rate": passed / total},
        "results": [
            {
                "case_id": r.case_id,
                "persona": r.persona,
                "prompt": r.prompt,
                "response": r.response,
                "score": r.score,
                "passed": r.passed,
                "checks": [
                    {"type": c.check_type, "passed": c.passed, "detail": c.detail}
                    for c in r.checks
                ],
            }
            for r in results
        ],
    }

    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    with open(results_dir / "report.json", "w") as f:
        json.dump(report, f, indent=2)

    md_lines = [
        f"# Persona Eval Report ({args.backend} backend)",
        "",
        f"Generated: {report['generated_at']}",
        "",
        f"**{passed}/{total} cases passed ({passed / total:.0%})**",
        "",
    ]
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        md_lines.append(f"## {r.case_id} — {r.persona} — {status} ({r.score:.2f})")
        md_lines.append(f"**Prompt:** {r.prompt}")
        md_lines.append(f"**Response:** {r.response}")
        md_lines.append("")
        md_lines.append("| Check | Result | Detail |")
        md_lines.append("|---|---|---|")
        for c in r.checks:
            md_lines.append(f"| {c.check_type} | {'✅' if c.passed else '❌'} | {c.detail} |")
        md_lines.append("")
    with open(results_dir / "report.md", "w") as f:
        f.write("\n".join(md_lines))

    print(f"Reports written to {results_dir}/report.json and {results_dir}/report.md")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
