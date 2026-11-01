"""Domain rules, no database."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from modules.quizzes.domain import scoring
from modules.quizzes.domain import state_machine as sm

NOW = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
D = Decimal


def _key(qtype=scoring.MCQ, correct=(1,), answers=()):
    return scoring.QuestionKey(qtype, D("2"), D("0.5"), frozenset(correct), answers)


def test_student_cannot_publish_a_quiz():
    with pytest.raises(sm.InvalidTransition):
        sm.check("quiz", sm.DRAFT, sm.AVAILABLE, sm.STUDENT)


def test_only_the_system_auto_submits():
    with pytest.raises(sm.InvalidTransition):
        sm.check("attempt", sm.IN_PROGRESS, sm.AUTO_SUBMITTED, sm.STUDENT)


def test_publish_target_depends_on_start_time():
    assert sm.publish_target(NOW - timedelta(minutes=1), NOW) == sm.AVAILABLE
    assert sm.publish_target(NOW + timedelta(days=1), NOW) == sm.SCHEDULED


def test_window_is_half_open():
    closes = NOW + timedelta(hours=1)
    assert sm.is_open(sm.AVAILABLE, NOW, closes, NOW)
    assert not sm.is_open(sm.AVAILABLE, NOW, closes, closes)


def test_deadline_is_capped_by_closing_time():
    closes = NOW + timedelta(minutes=20)
    assert sm.attempt_deadline(NOW, 30, closes) == closes
    assert sm.attempt_deadline(NOW, 10, closes) == NOW + timedelta(minutes=10)


def test_negative_marking_applies_only_to_wrong_answers():
    wrong = scoring.Answer(frozenset({2}))
    assert scoring.mark(_key(), wrong, negative_marking=True) == D("-0.5")
    assert scoring.mark(_key(), wrong, negative_marking=False) == 0
    assert scoring.mark(_key(), scoring.Answer(), negative_marking=True) == 0


def test_multi_select_is_all_or_nothing():
    key = _key(scoring.MULTI_SELECT, correct=(1, 2))
    assert scoring.mark(key, scoring.Answer(frozenset({1, 2})), False) == D("2")
    assert scoring.mark(key, scoring.Answer(frozenset({1})), False) == 0


def test_fill_blank_ignores_case_and_spacing():
    key = _key(scoring.FILL_BLANK, correct=(), answers=("Binary  Search",))
    assert scoring.is_correct(key, scoring.Answer(text=" binary search "))


def test_mcq_with_two_correct_options_is_rejected():
    problems = scoring.validate_key(_key(correct=(1, 2)), option_count=4)
    assert "Only one option may be correct." in problems
