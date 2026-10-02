"""
Rubric-based scorer for LLM outputs.

Each test case defines a rubric: a list of checks that a "good" response
for that persona/prompt should satisfy. This module runs those checks
against an actual model response and produces a pass/fail verdict plus
a per-check breakdown, so a failure is explainable rather than a bare
number.

Supported check types (deliberately simple, deterministic, and fast —
no second model call required to grade):
  - keyword_present: at least one of `keywords` must appear (case-insensitive)
  - keyword_absent:  none of `keywords` may appear (case-insensitive)
  - max_words:       response must be at most `value` words
  - min_words:       response must be at least `value` words
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CheckResult:
    check_type: str
    passed: bool
    detail: str


@dataclass
class CaseResult:
    case_id: str
    persona: str
    prompt: str
    response: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def score(self) -> float:
        if not self.checks:
            return 0.0
        return sum(1 for c in self.checks if c.passed) / len(self.checks)

    @property
    def passed(self) -> bool:
        return self.score >= 0.75


def _word_count(text: str) -> int:
    return len(text.split())


def run_check(check: dict, response: str) -> CheckResult:
    check_type = check["type"]
    lower = response.lower()

    if check_type == "keyword_present":
        keywords = [k.lower() for k in check["keywords"]]
        found = [k for k in keywords if k in lower]
        passed = len(found) > 0
        detail = (
            f"found: {found}" if passed else f"none of {keywords} present"
        )
        return CheckResult(check_type, passed, detail)

    if check_type == "keyword_absent":
        keywords = [k.lower() for k in check["keywords"]]
        found = [k for k in keywords if k in lower]
        passed = len(found) == 0
        detail = (
            "clean" if passed else f"forbidden term(s) present: {found}"
        )
        return CheckResult(check_type, passed, detail)

    if check_type == "max_words":
        count = _word_count(response)
        passed = count <= check["value"]
        detail = f"{count} words (limit {check['value']})"
        return CheckResult(check_type, passed, detail)

    if check_type == "min_words":
        count = _word_count(response)
        passed = count >= check["value"]
        detail = f"{count} words (minimum {check['value']})"
        return CheckResult(check_type, passed, detail)

    raise ValueError(f"Unknown check type: {check_type}")


def score_case(case: dict, response: str) -> CaseResult:
    result = CaseResult(
        case_id=case["id"],
        persona=case["persona"],
        prompt=case["prompt"],
        response=response,
    )
    for check in case["rubric"]:
        result.checks.append(run_check(check, response))
    return result
