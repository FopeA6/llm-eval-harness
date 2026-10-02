"""
Pluggable model client so the eval harness can run two ways:

  - "mock"     — deterministic, canned persona responses. No API key or
                 network access needed. This is the default, and what the
                 test suite and CI would run, so the repo is reviewable
                 and runnable by anyone without credentials.
  - "anthropic" — real calls to Claude via the Anthropic API, for when you
                 actually want to evaluate a live model. Requires
                 ANTHROPIC_API_KEY to be set in the environment.

Swapping backends doesn't touch the scoring logic at all — scorer.py only
ever sees a plain string response, regardless of where it came from.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod


class ModelClient(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, case_id: str) -> str:
        """Return the model's response text for a given persona + prompt.

        `case_id` is passed through for the mock backend's lookup table;
        the real backend ignores it and just calls the model.
        """


class MockModelClient(ModelClient):
    """
    Deterministic canned responses keyed by case id.

    Includes a couple of deliberately *flawed* responses (too much jargon
    for a beginner persona, a response that's too long) so the scorer has
    something real to catch — a harness that only ever shows passes isn't
    a convincing demonstration that the scoring logic actually works.
    """

    RESPONSES: dict[str, str] = {
        "beginner_js_1": (
            "A variable is like a labelled box where you can store a value, "
            "like a number or some text, so you can use it again later in your code."
        ),
        "beginner_js_2": (
            # Deliberately flawed: uses jargon the beginner-tutor persona
            # should avoid (hoisting, closures, scope chain).
            "This happens because of hoisting and the scope chain — the "
            "variable is lifted to the top of its lexical scope before "
            "execution, which interacts with closures if you're not careful."
        ),
        "python_mentor_1": (
            "A list comprehension is a concise way to build a list in one line, "
            "for example [x * 2 for x in range(5)] doubles each number from 0 to 4. "
            "It's equivalent to writing a for loop that appends to a list, but more compact."
        ),
        "python_mentor_2": (
            "Use a virtual environment (venv) to isolate your project's dependencies "
            "from your system Python installation, then install packages with pip "
            "inside that environment so different projects don't conflict with each other."
        ),
        "career_change_1": (
            "It's completely normal to feel behind when you're switching careers into tech — "
            "most people learning to code for the first time feel this way. Focus on small, "
            "consistent progress rather than comparing yourself to people with years of experience."
        ),
        "career_change_2": (
            # Deliberately flawed: far too long for this persona's rubric
            # (meant to be a short, encouraging check-in, not an essay).
            "Let me give you a comprehensive breakdown of every single consideration "
            "you should think about when changing careers into software engineering, "
            "starting with an assessment of your current skill gaps, followed by a "
            "detailed six-month study plan covering data structures, algorithms, system "
            "design, behavioural interview preparation, networking strategies, portfolio "
            "project selection, open source contribution strategies, and how to evaluate "
            "whether a bootcamp or self-study path is right for your specific learning "
            "style and financial circumstances, among many other factors worth considering "
            "before you commit to this significant life and career transition."
        ),
        "interview_coach_1": (
            "Walk me through your approach before you write any code — what's the time "
            "complexity of your current solution, and can you think of an edge case that "
            "would break it?"
        ),
        "interview_coach_2": (
            "That answer is a good start, but I'd push you to justify why you chose a "
            "hash map here instead of sorting the array first — what's the tradeoff?"
        ),
    }

    def generate(self, system_prompt: str, user_prompt: str, case_id: str) -> str:
        if case_id not in self.RESPONSES:
            raise KeyError(f"No mock response registered for case id '{case_id}'")
        return self.RESPONSES[case_id]


class AnthropicModelClient(ModelClient):
    """Real backend. Requires `pip install anthropic` and ANTHROPIC_API_KEY set."""

    def __init__(self, model: str = "claude-3-5-haiku-latest"):
        import anthropic  # imported lazily so mock mode never needs this installed

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Export it, or run with --backend mock."
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, case_id: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


def get_client(backend: str) -> ModelClient:
    if backend == "mock":
        return MockModelClient()
    if backend == "anthropic":
        return AnthropicModelClient()
    raise ValueError(f"Unknown backend '{backend}'. Use 'mock' or 'anthropic'.")
