import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scorer import run_check, score_case  # noqa: E402


def test_keyword_present_passes_when_keyword_found():
    check = {"type": "keyword_present", "keywords": ["store", "value"]}
    result = run_check(check, "A variable lets you store a value.")
    assert result.passed is True


def test_keyword_present_fails_when_no_keyword_found():
    check = {"type": "keyword_present", "keywords": ["store", "value"]}
    result = run_check(check, "Variables are containers.")
    assert result.passed is False


def test_keyword_present_is_case_insensitive():
    check = {"type": "keyword_present", "keywords": ["STORE"]}
    result = run_check(check, "you can store things here")
    assert result.passed is True


def test_keyword_absent_passes_when_clean():
    check = {"type": "keyword_absent", "keywords": ["hoisting", "closure"]}
    result = run_check(check, "A variable stores a value.")
    assert result.passed is True


def test_keyword_absent_fails_when_forbidden_term_present():
    check = {"type": "keyword_absent", "keywords": ["hoisting"]}
    result = run_check(check, "This is caused by hoisting.")
    assert result.passed is False


def test_keyword_absent_catches_substring_match():
    # "closure" should match inside "closures" — deliberately permissive
    # substring matching, documented in scorer.py's module docstring.
    check = {"type": "keyword_absent", "keywords": ["closure"]}
    result = run_check(check, "this interacts with closures")
    assert result.passed is False


def test_max_words_passes_under_limit():
    check = {"type": "max_words", "value": 5}
    result = run_check(check, "one two three")
    assert result.passed is True


def test_max_words_fails_over_limit():
    check = {"type": "max_words", "value": 3}
    result = run_check(check, "one two three four five")
    assert result.passed is False


def test_min_words_fails_under_limit():
    check = {"type": "min_words", "value": 10}
    result = run_check(check, "too short")
    assert result.passed is False


def test_min_words_passes_over_limit():
    check = {"type": "min_words", "value": 2}
    result = run_check(check, "just enough words here")
    assert result.passed is True


def test_unknown_check_type_raises():
    import pytest

    check = {"type": "not_a_real_check"}
    with pytest.raises(ValueError):
        run_check(check, "anything")


def test_score_case_all_checks_pass():
    case = {
        "id": "t1",
        "persona": "Test",
        "prompt": "p",
        "rubric": [
            {"type": "keyword_present", "keywords": ["hello"]},
            {"type": "max_words", "value": 10},
        ],
    }
    result = score_case(case, "hello world")
    assert result.score == 1.0
    assert result.passed is True


def test_score_case_partial_failure_below_threshold():
    case = {
        "id": "t2",
        "persona": "Test",
        "prompt": "p",
        "rubric": [
            {"type": "keyword_present", "keywords": ["hello"]},
            {"type": "keyword_absent", "keywords": ["world"]},
            {"type": "max_words", "value": 10},
        ],
    }
    # Fails the keyword_absent check (1 of 3 checks fails -> score 0.667 < 0.75 threshold)
    result = score_case(case, "hello world")
    assert result.score < 1.0
    assert result.passed is False


def test_score_case_with_no_rubric_scores_zero():
    case = {"id": "t3", "persona": "Test", "prompt": "p", "rubric": []}
    result = score_case(case, "anything")
    assert result.score == 0.0
    assert result.passed is False
