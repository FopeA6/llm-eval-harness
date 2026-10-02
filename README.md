# Persona Eval Harness

A small, real eval harness: it runs a set of test prompts against an LLM playing different personas, scores each response against an explicit rubric, and produces a pass/fail report explaining *why* — not just a number.

Built to practice the specific discipline PostHog describes as "evals": defining criteria up front, running outputs against them repeatedly, and making failures explainable rather than eyeballing responses once.

## Why personas

This is modelled on a real project I worked on: building and evaluating several AI personas for a teaching chatbot, where each persona needed a different tone and vocabulary level for its audience (e.g. a beginner tutor shouldn't use jargon a career-interview coach would use freely). Here that's reduced to four personas, each with its own rubric:

| Persona | What "good" looks like |
|---|---|
| Beginner-Friendly JavaScript Tutor | Plain language, no jargon, short answers |
| Intermediate Python Mentor | Can use technical terms, moderate length |
| Career-Change Encourager | Warm, brief, no overwhelming technical detail |
| Technical Interview Coach | Pushes back, asks "why", stays concise |

## How it works

1. **`cases/personas.json`** — 8 test cases (2 per persona), each with a `system_prompt`, a `prompt`, and a `rubric` (a list of checks).
2. **`src/model_client.py`** — pluggable backend. Defaults to a `mock` client with deterministic canned responses (including two *deliberately flawed* ones, so the scorer has something real to catch). A real `anthropic` backend is also implemented, for actually evaluating a live model.
3. **`src/scorer.py`** — runs each rubric check (`keyword_present`, `keyword_absent`, `max_words`, `min_words`) against the response and produces a pass/fail with a human-readable reason per check. A case passes if ≥75% of its checks pass.
4. **`src/run_evals.py`** — orchestrates the above, prints a console summary, and writes `results/report.json` + `results/report.md`.

## Running it

```bash
pip install -r requirements.txt

# Mock backend — no API key needed, deterministic, what CI would run:
python src/run_evals.py

# Real backend — requires ANTHROPIC_API_KEY to be set:
export ANTHROPIC_API_KEY=sk-...
python src/run_evals.py --backend anthropic --model claude-3-5-haiku-latest
```

Exit code is `1` if any case fails its rubric, so this plugs into CI as-is.

## Example output (mock backend)

See [`results/report.md`](results/report.md) for a full committed example run. Summary:

**6/8 cases passed (75%)** — the two failures are intentional:
- `beginner_js_2` fails because the mock response leaks jargon (`hoisting`, `scope chain`, `closures`) into the beginner persona, which its rubric explicitly forbids.
- `career_change_2` fails because the mock response is 91 words against a 70-word limit — too long for what's meant to be a brief, encouraging check-in.

Both are deliberate: a harness that only ever shows green is not demonstrating that the scoring logic actually works.

## Testing

Unit tests cover the scorer logic directly (no model call needed, so they're fast and deterministic):

```bash
pip install pytest
pytest tests/ -v
```

14 tests, covering each check type's pass and fail paths, case-level score aggregation, and the pass/fail threshold.

## Design notes

- The model backend is swappable without touching the scorer — `scorer.py` only ever sees a plain string response, never anything backend-specific. That's what makes the mock backend safe to run with zero credentials, while the real backend is a genuine drop-in.
- Checks are deliberately simple and deterministic (keyword/length based) rather than using a second LLM call to grade the first — this keeps the harness fast, free, and reproducible, at the cost of not catching more nuanced issues (tone, factual correctness) that a model-graded eval would. A natural next step would be adding an LLM-as-judge check type alongside the deterministic ones.

## Stack

Python 3.12, [`anthropic`](https://pypi.org/project/anthropic/) SDK (optional real backend), `pytest` for unit tests. No framework dependencies beyond the standard library for the core scoring logic.

## Author

Fopefoluwa Ayo — [fopeayo@hotmail.com](mailto:fopeayo@hotmail.com)
