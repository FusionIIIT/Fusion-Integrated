"""Objective response scoring with unresolved policies kept fail-closed."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from modules.quiz.domain.errors import DomainError, UnresolvedPolicyError


class QuestionType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    MULTIPLE_SELECT = "multiple_select"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"


@dataclass(frozen=True)
class ObjectiveScore:
    maximum_marks: Decimal
    awarded_marks: Decimal
    is_correct: bool
    unanswered: bool


def _validate_marks(maximum_marks: Decimal) -> None:
    if not isinstance(maximum_marks, Decimal) or not maximum_marks.is_finite():
        raise DomainError("invalid_marks", "Maximum marks must be a finite Decimal.")
    if maximum_marks <= 0:
        raise DomainError("invalid_marks", "Maximum marks must be positive.")


def score_objective_response(
    *,
    question_type: QuestionType,
    maximum_marks: Decimal,
    expected_answer: UUID | bool | frozenset[UUID],
    submitted_answer: UUID | bool | frozenset[UUID] | None,
    unanswered: bool,
    negative_marking_enabled: bool = False,
) -> ObjectiveScore:
    """Score supported canonical objective answers.

    MSQ uses the peer-accepted provisional all-or-nothing rule. Negative-mark
    precedence (UAD-04) and fill-blank normalization remain unresolved and raise
    instead of silently selecting a policy. This function never calls services.
    """

    _validate_marks(maximum_marks)
    if negative_marking_enabled:
        raise UnresolvedPolicyError(
            "UAD-04",
            "Negative marking is gated until its configured precedence is approved.",
        )
    if question_type is QuestionType.FILL_BLANK:
        raise DomainError(
            "fill_blank_scoring_unsupported",
            "Fill-in-the-blank matching has no approved comparison rule yet.",
        )
    if question_type not in {
        QuestionType.MULTIPLE_CHOICE,
        QuestionType.MULTIPLE_SELECT,
        QuestionType.TRUE_FALSE,
    }:
        raise DomainError(
            "not_objective_question", "Subjective question types cannot use objective scoring."
        )

    if unanswered:
        if submitted_answer is not None:
            raise DomainError(
                "answer_state_mismatch", "An unanswered response cannot contain an answer."
            )
        return ObjectiveScore(maximum_marks, Decimal("0"), False, True)
    if submitted_answer is None:
        raise DomainError(
            "answer_state_mismatch", "Mark a missing answer as unanswered explicitly."
        )

    if question_type is QuestionType.MULTIPLE_CHOICE:
        if not isinstance(expected_answer, UUID) or not isinstance(submitted_answer, UUID):
            raise DomainError(
                "invalid_canonical_answer", "Multiple-choice answers must use option UUIDs."
            )
        is_correct = submitted_answer == expected_answer
    elif question_type is QuestionType.TRUE_FALSE:
        if type(expected_answer) is not bool or type(submitted_answer) is not bool:
            raise DomainError("invalid_canonical_answer", "True/False answers must be booleans.")
        is_correct = submitted_answer is expected_answer
    else:
        if not isinstance(expected_answer, frozenset) or not isinstance(
            submitted_answer, frozenset
        ):
            raise DomainError(
                "invalid_canonical_answer",
                "Multiple-select answers must be canonical option UUID sets.",
            )
        if any(not isinstance(option_id, UUID) for option_id in expected_answer | submitted_answer):
            raise DomainError(
                "invalid_canonical_answer", "Multiple-select options must use UUID identities."
            )
        is_correct = submitted_answer == expected_answer

    awarded_marks = maximum_marks if is_correct else Decimal("0")
    return ObjectiveScore(maximum_marks, awarded_marks, is_correct, False)
