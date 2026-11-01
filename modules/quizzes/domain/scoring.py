"""Marking rules (BR-QZ-011, BR-QZ-018, BR-QZ-020). Pure Python.

Objective questions are marked here. Subjective ones (short answer, photo
upload) are never auto-marked: they wait for the professor (BR-QZ-019).
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

MCQ = "mcq"                       # exactly one correct option
MULTI_SELECT = "multi_select"     # one or more correct options, all-or-nothing
TRUE_FALSE = "true_false"
FILL_BLANK = "fill_blank"
SHORT_ANSWER = "short_answer"

QUESTION_TYPES = (MCQ, MULTI_SELECT, TRUE_FALSE, FILL_BLANK, SHORT_ANSWER)
OBJECTIVE = frozenset({MCQ, MULTI_SELECT, TRUE_FALSE, FILL_BLANK})
CHOICE_BASED = frozenset({MCQ, MULTI_SELECT, TRUE_FALSE})

ZERO = Decimal("0")


@dataclass(frozen=True)
class QuestionKey:
    """What the marker needs to know about one question."""
    question_type: str
    marks: Decimal
    negative_marks: Decimal
    correct_option_ids: frozenset[int] = frozenset()
    accepted_answers: tuple[str, ...] = ()


@dataclass(frozen=True)
class Answer:
    selected_option_ids: frozenset[int] = frozenset()
    text: str = ""

    @property
    def is_blank(self) -> bool:
        return not self.selected_option_ids and not self.text.strip()


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())


def is_correct(key: QuestionKey, answer: Answer) -> bool:
    if key.question_type in CHOICE_BASED:
        return answer.selected_option_ids == key.correct_option_ids
    if key.question_type == FILL_BLANK:
        given = _normalise(answer.text)
        return any(given == _normalise(a) for a in key.accepted_answers)
    raise ValueError(f"{key.question_type!r} is not objectively markable.")


def mark(key: QuestionKey, answer: Answer | None,
         negative_marking: bool) -> Decimal:
    """Marks for one objective response. A blank answer is never penalised."""
    if answer is None or answer.is_blank:
        return ZERO
    if is_correct(key, answer):
        return key.marks
    return -key.negative_marks if negative_marking else ZERO


def total(awarded: Iterable[Decimal]) -> Decimal:
    """Final score, floored at zero so negative marking cannot go below it."""
    return max(sum(awarded, ZERO), ZERO)


def has_passed(score: Decimal, passing_marks: Decimal) -> bool:
    return score >= passing_marks


def validate_key(key: QuestionKey, option_count: int) -> list[str]:
    """Why a question cannot be published as written, if it cannot."""
    problems = []
    if key.marks <= ZERO:
        problems.append("Marks must be positive.")
    if key.negative_marks < ZERO:
        problems.append("Negative marks cannot be below zero.")
    if key.question_type in CHOICE_BASED:
        if option_count < 2:
            problems.append("A choice question needs at least two options.")
        if not key.correct_option_ids:
            problems.append("Mark at least one option correct.")
        if key.question_type != MULTI_SELECT and len(key.correct_option_ids) > 1:
            problems.append("Only one option may be correct.")
    if key.question_type == FILL_BLANK and not key.accepted_answers:
        problems.append("Give at least one accepted answer.")
    return problems
