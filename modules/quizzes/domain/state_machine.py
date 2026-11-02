from typing import FrozenSet, Tuple, Iterable, Dict, Any, List, Optional
from enum import StrEnum
from dataclasses import dataclass
from datetime import datetime, timedelta


class InvalidTransition(Exception):
    """Raised when an invalid transition is attempted."""


class PermissionDenied(PermissionError):
    """Raised when a transition exists but permission is missing."""


class BusinessRuleViolation(Exception):
    """Raised when a business rule or guard condition is violated."""


# --- Domain Status Enums ---

class QuizStatus(StrEnum):
    """Quiz lifecycle states (CW-QZ-01)."""
    DRAFT = "DRAFT"
    DRAFT_CONFIGURED_WITH_QUESTIONS = "DRAFT_CONFIGURED_WITH_QUESTIONS"
    READY_FOR_PUBLICATION = "READY_FOR_PUBLICATION"
    READY_FOR_SCHEDULING = "READY_FOR_SCHEDULING"
    SCHEDULED = "SCHEDULED"
    AVAILABLE = "AVAILABLE"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class AttemptStatus(StrEnum):
    """Student attempt lifecycle states (CW-QZ-02)."""
    IN_PROGRESS = "IN_PROGRESS"
    IN_PROGRESS_RESPONSES_RECORDED = "IN_PROGRESS_RESPONSES_RECORDED"
    SUBMITTED = "SUBMITTED"


class ResultStatus(StrEnum):
    """Evaluation and result release lifecycle states (CW-QZ-03)."""
    NOT_EVALUATED = "NOT_EVALUATED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_EVALUATED = "PARTIALLY_EVALUATED"
    EVALUATED = "EVALUATED"
    RELEASED = "RELEASED"
    RELEASED_VIEWED = "RELEASED_VIEWED"


class Status(StrEnum):
    """Unified Status enum conforming to ELM state machine conventions."""
    # CW-QZ-01: Quiz states
    DRAFT = "DRAFT"
    DRAFT_CONFIGURED_WITH_QUESTIONS = "DRAFT_CONFIGURED_WITH_QUESTIONS"
    READY_FOR_PUBLICATION = "READY_FOR_PUBLICATION"
    READY_FOR_SCHEDULING = "READY_FOR_SCHEDULING"
    SCHEDULED = "SCHEDULED"
    AVAILABLE = "AVAILABLE"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"

    # CW-QZ-02: Attempt states
    IN_PROGRESS = "IN_PROGRESS"
    IN_PROGRESS_RESPONSES_RECORDED = "IN_PROGRESS_RESPONSES_RECORDED"
    SUBMITTED = "SUBMITTED"

    # CW-QZ-03: Result states
    NOT_EVALUATED = "NOT_EVALUATED"
    PARTIALLY_EVALUATED = "PARTIALLY_EVALUATED"
    EVALUATED = "EVALUATED"
    RELEASED = "RELEASED"
    RELEASED_VIEWED = "RELEASED_VIEWED"


@dataclass(frozen=True)
class Transition:
    """Defines a transition from one status to another."""
    from_status: Status
    to_status: Status
    permission: str
    workflow_id: str = ""
    use_case_id: str = ""


# --- Authoritative Transitions ---

# CW-QZ-01: Quiz Preparation and Availability Lifecycle
QUIZ_TRANSITIONS: Tuple[Transition, ...] = (
    # Professor creates/configures questions in draft
    Transition(Status.DRAFT, Status.DRAFT_CONFIGURED_WITH_QUESTIONS, "quiz.quiz.manage_questions", "CW-QZ-01", "UC-QZ-002"),
    Transition(Status.DRAFT_CONFIGURED_WITH_QUESTIONS, Status.DRAFT, "quiz.quiz.manage_questions", "CW-QZ-01", "UC-QZ-002"),
    # Professor configures quiz and schedule
    Transition(Status.DRAFT_CONFIGURED_WITH_QUESTIONS, Status.READY_FOR_PUBLICATION, "quiz.quiz.configure", "CW-QZ-01", "UC-QZ-004"),
    Transition(Status.DRAFT_CONFIGURED_WITH_QUESTIONS, Status.READY_FOR_SCHEDULING, "quiz.quiz.configure", "CW-QZ-01", "UC-QZ-004"),
    Transition(Status.DRAFT, Status.READY_FOR_PUBLICATION, "quiz.quiz.configure", "CW-QZ-01", "UC-QZ-004"),
    Transition(Status.DRAFT, Status.READY_FOR_SCHEDULING, "quiz.quiz.configure", "CW-QZ-01", "UC-QZ-004"),
    # Publication / Scheduling
    Transition(Status.READY_FOR_PUBLICATION, Status.AVAILABLE, "quiz.quiz.publish", "CW-QZ-01", "UC-QZ-005"),
    Transition(Status.READY_FOR_SCHEDULING, Status.SCHEDULED, "quiz.quiz.publish", "CW-QZ-01", "UC-QZ-005"),
    Transition(Status.DRAFT_CONFIGURED_WITH_QUESTIONS, Status.AVAILABLE, "quiz.quiz.publish", "CW-QZ-01", "UC-QZ-005"),
    Transition(Status.DRAFT_CONFIGURED_WITH_QUESTIONS, Status.SCHEDULED, "quiz.quiz.publish", "CW-QZ-01", "UC-QZ-005"),
    Transition(Status.DRAFT, Status.AVAILABLE, "quiz.quiz.publish", "CW-QZ-01", "UC-QZ-005"),
    Transition(Status.DRAFT, Status.SCHEDULED, "quiz.quiz.publish", "CW-QZ-01", "UC-QZ-005"),
    # System processes availability boundary
    Transition(Status.SCHEDULED, Status.AVAILABLE, "quiz.system.process_boundary", "CW-QZ-01", "UC-QZ-018"),
    Transition(Status.AVAILABLE, Status.CLOSED, "quiz.system.process_boundary", "CW-QZ-01", "UC-QZ-018"),
    # Professor archives closed quiz
    Transition(Status.CLOSED, Status.ARCHIVED, "quiz.quiz.archive", "CW-QZ-01", "UC-QZ-006"),
)

# CW-QZ-02: Student Attempt and Submission Lifecycle
ATTEMPT_TRANSITIONS: Tuple[Transition, ...] = (
    # Student starts attempt on Available quiz
    Transition(Status.AVAILABLE, Status.IN_PROGRESS, "quiz.attempt.start", "CW-QZ-02", "UC-QZ-008"),
    # Student saves / records responses
    Transition(Status.IN_PROGRESS, Status.IN_PROGRESS_RESPONSES_RECORDED, "quiz.attempt.record_response", "CW-QZ-02", "UC-QZ-009"),
    Transition(Status.IN_PROGRESS_RESPONSES_RECORDED, Status.IN_PROGRESS_RESPONSES_RECORDED, "quiz.attempt.record_response", "CW-QZ-02", "UC-QZ-009"),
    # Student manually submits attempt
    Transition(Status.IN_PROGRESS_RESPONSES_RECORDED, Status.SUBMITTED, "quiz.attempt.submit", "CW-QZ-02", "UC-QZ-010"),
    Transition(Status.IN_PROGRESS, Status.SUBMITTED, "quiz.attempt.submit", "CW-QZ-02", "UC-QZ-010"),
    # System auto-submits expired attempt
    Transition(Status.IN_PROGRESS_RESPONSES_RECORDED, Status.SUBMITTED, "quiz.system.auto_submit", "CW-QZ-02", "UC-QZ-011"),
    Transition(Status.IN_PROGRESS, Status.SUBMITTED, "quiz.system.auto_submit", "CW-QZ-02", "UC-QZ-011"),
)

# CW-QZ-03: Evaluation and Result Release Lifecycle
EVALUATION_TRANSITIONS: Tuple[Transition, ...] = (
    # Automatic evaluation of objective portion (System)
    Transition(Status.SUBMITTED, Status.EVALUATED, "quiz.system.evaluate_objective", "CW-QZ-03", "UC-QZ-012"),
    Transition(Status.SUBMITTED, Status.PARTIALLY_EVALUATED, "quiz.system.evaluate_objective", "CW-QZ-03", "UC-QZ-012"),
    Transition(Status.NOT_EVALUATED, Status.EVALUATED, "quiz.system.evaluate_objective", "CW-QZ-03", "UC-QZ-012"),
    Transition(Status.NOT_EVALUATED, Status.PARTIALLY_EVALUATED, "quiz.system.evaluate_objective", "CW-QZ-03", "UC-QZ-012"),
    # Subjective evaluation by Professor (manual or AI-assisted)
    Transition(Status.SUBMITTED, Status.EVALUATED, "quiz.evaluation.evaluate_subjective", "CW-QZ-03", "UC-QZ-013"),
    Transition(Status.PARTIALLY_EVALUATED, Status.EVALUATED, "quiz.evaluation.evaluate_subjective", "CW-QZ-03", "UC-QZ-013"),
    Transition(Status.NOT_EVALUATED, Status.EVALUATED, "quiz.evaluation.evaluate_subjective", "CW-QZ-03", "UC-QZ-013"),
    # Result release by Professor
    Transition(Status.EVALUATED, Status.RELEASED, "quiz.result.release", "CW-QZ-03", "UC-QZ-014"),
    # Student views released result
    Transition(Status.RELEASED, Status.RELEASED_VIEWED, "quiz.result.view", "CW-QZ-03", "UC-QZ-015"),
    Transition(Status.RELEASED, Status.RELEASED, "quiz.result.view", "CW-QZ-03", "UC-QZ-015"),
)

# Unified transitions tuple
TRANSITIONS: Tuple[Transition, ...] = (
    *QUIZ_TRANSITIONS,
    *ATTEMPT_TRANSITIONS,
    *EVALUATION_TRANSITIONS,
)


def validate_transition(
    from_status: Status | str,
    to_status: Status | str,
    permissions: FrozenSet[str] | Iterable[str]
) -> None:
    """Validate a transition from one status to another with given permissions."""
    perms = frozenset(permissions)
    for transition in TRANSITIONS:
        if transition.from_status == from_status and transition.to_status == to_status:
            if "*" in perms or transition.permission in perms:
                return
    if not any(t.from_status == from_status and t.to_status == to_status for t in TRANSITIONS):
        raise InvalidTransition(f"No transition from {from_status} to {to_status}")
    raise PermissionDenied(f"No permission to transition from {from_status} to {to_status}")


def validate_quiz_transition(
    from_status: QuizStatus | Status | str,
    to_status: QuizStatus | Status | str,
    permissions: FrozenSet[str] | Iterable[str]
) -> None:
    """Validate a CW-QZ-01 quiz lifecycle transition."""
    perms = frozenset(permissions)
    for transition in QUIZ_TRANSITIONS:
        if transition.from_status == from_status and transition.to_status == to_status:
            if "*" in perms or transition.permission in perms:
                return
    if not any(t.from_status == from_status and t.to_status == to_status for t in QUIZ_TRANSITIONS):
        raise InvalidTransition(f"No quiz transition from {from_status} to {to_status}")
    raise PermissionDenied(f"No permission for quiz transition from {from_status} to {to_status}")


def validate_attempt_transition(
    from_status: AttemptStatus | Status | str,
    to_status: AttemptStatus | Status | str,
    permissions: FrozenSet[str] | Iterable[str]
) -> None:
    """Validate a CW-QZ-02 student attempt lifecycle transition."""
    perms = frozenset(permissions)
    for transition in ATTEMPT_TRANSITIONS:
        if transition.from_status == from_status and transition.to_status == to_status:
            if "*" in perms or transition.permission in perms:
                return
    if not any(t.from_status == from_status and t.to_status == to_status for t in ATTEMPT_TRANSITIONS):
        raise InvalidTransition(f"No attempt transition from {from_status} to {to_status}")
    raise PermissionDenied(f"No permission for attempt transition from {from_status} to {to_status}")


def validate_evaluation_transition(
    from_status: ResultStatus | Status | str,
    to_status: ResultStatus | Status | str,
    permissions: FrozenSet[str] | Iterable[str]
) -> None:
    """Validate a CW-QZ-03 evaluation and result release transition."""
    perms = frozenset(permissions)
    for transition in EVALUATION_TRANSITIONS:
        if transition.from_status == from_status and transition.to_status == to_status:
            if "*" in perms or transition.permission in perms:
                return
    if not any(t.from_status == from_status and t.to_status == to_status for t in EVALUATION_TRANSITIONS):
        raise InvalidTransition(f"No evaluation transition from {from_status} to {to_status}")
    raise PermissionDenied(f"No permission for evaluation transition from {from_status} to {to_status}")


# --- Business Rules and Guard Validators ---

def check_course_scope(professor_id: int, course_id: str | int, authorized_courses: Iterable[str | int]) -> None:
    """BR-QZ-002: Professor may manage quizzes only for associated courses."""
    if course_id not in authorized_courses:
        raise PermissionDenied(f"Professor {professor_id} is not authorized for course {course_id}")


def check_student_eligibility(student_id: int, quiz_id: int, eligible_student_ids: Iterable[int]) -> None:
    """BR-QZ-003: Student may access only quizzes for which they are eligible."""
    if student_id not in eligible_student_ids:
        raise PermissionDenied(f"Student {student_id} is not eligible for quiz {quiz_id}")


def check_pre_activation_edit(quiz_status: QuizStatus | Status | str) -> None:
    """BR-QZ-005: Quiz details and questions may be edited/removed only before activation."""
    editable_statuses = {
        Status.DRAFT,
        Status.DRAFT_CONFIGURED_WITH_QUESTIONS,
        Status.READY_FOR_PUBLICATION,
        Status.READY_FOR_SCHEDULING,
        Status.SCHEDULED,
    }
    if quiz_status not in editable_statuses:
        raise BusinessRuleViolation(f"Cannot edit quiz in active or closed status: {quiz_status}")


def check_availability_window(
    current_time: datetime,
    start_time: Optional[datetime],
    closing_time: Optional[datetime]
) -> None:
    """BR-QZ-006: Student cannot start a quiz outside its configured availability period."""
    if start_time and current_time < start_time:
        raise BusinessRuleViolation(f"Quiz is not yet available. Starts at {start_time}")
    if closing_time and current_time >= closing_time:
        raise BusinessRuleViolation(f"Quiz availability has closed at {closing_time}")


def check_attempt_allowance(attempts_taken: int, permitted_attempts: int) -> None:
    """BR-QZ-008: Student cannot exceed configured permitted attempts."""
    if attempts_taken >= permitted_attempts:
        raise BusinessRuleViolation(f"Permitted attempts ({permitted_attempts}) exhausted. Taken: {attempts_taken}")


def check_submission_immutability(attempt_status: AttemptStatus | Status | str) -> None:
    """BR-QZ-016: Once submitted, an attempt cannot be modified."""
    if attempt_status == Status.SUBMITTED:
        raise BusinessRuleViolation("Submitted attempt is immutable and cannot be modified.")


def check_auto_submit_expiry(
    current_time: datetime,
    started_at: datetime,
    duration_minutes: int
) -> bool:
    """BR-QZ-017: Detect if active attempt has reached time limit."""
    expiry_time = started_at + timedelta(minutes=duration_minutes)
    return current_time >= expiry_time


def evaluate_objective_response(
    question_type: str,
    correct_answer: Any,
    student_answer: Any,
    marks: float,
    negative_marks: float = 0.0,
    negative_marking_enabled: bool = False
) -> Dict[str, Any]:
    """BR-QZ-018: Evaluate objective questions (MCQ, MSQ, TF, FITB) with negative marks."""
    if student_answer is None or student_answer == "" or student_answer == []:
        return {
            "is_answered": False,
            "is_correct": False,
            "marks_obtained": 0.0,
            "negative_marks": 0.0,
        }

    is_correct = False
    q_type = question_type.upper()

    if q_type in ("MCQ", "TF"):
        is_correct = str(student_answer).strip().lower() == str(correct_answer).strip().lower()
    elif q_type == "MSQ":
        # Multi-select requires matching set of selected options
        student_set = set(student_answer) if isinstance(student_answer, (list, tuple, set)) else {student_answer}
        correct_set = set(correct_answer) if isinstance(correct_answer, (list, tuple, set)) else {correct_answer}
        is_correct = student_set == correct_set
    elif q_type == "FITB":
        # Fill in blank: case-insensitive normalized comparison
        is_correct = str(student_answer).strip().lower() == str(correct_answer).strip().lower()
    else:
        # Default equality
        is_correct = student_answer == correct_answer

    if is_correct:
        return {
            "is_answered": True,
            "is_correct": True,
            "marks_obtained": float(marks),
            "negative_marks": 0.0,
        }
    else:
        penalty = float(negative_marks) if negative_marking_enabled else 0.0
        return {
            "is_answered": True,
            "is_correct": False,
            "marks_obtained": -penalty if penalty > 0 else 0.0,
            "negative_marks": penalty,
        }


def evaluate_subjective_response(
    professor_confirmed_marks: float,
    max_marks: float,
    ai_suggested_marks: Optional[float] = None,
    feedback: str = ""
) -> Dict[str, Any]:
    """BR-QZ-019: Subjective evaluation remains strictly Professor-controlled.

    AI suggested marks are purely advisory; only professor confirmed marks are final.
    """
    if professor_confirmed_marks < 0:
        raise BusinessRuleViolation("Marks cannot be negative.")
    if professor_confirmed_marks > max_marks:
        raise BusinessRuleViolation(f"Marks ({professor_confirmed_marks}) cannot exceed maximum ({max_marks}).")

    return {
        "is_evaluated": True,
        "marks_obtained": float(professor_confirmed_marks),
        "ai_suggested_marks": float(ai_suggested_marks) if ai_suggested_marks is not None else None,
        "is_ai_advisory": ai_suggested_marks is not None,
        "feedback": feedback,
    }


def calculate_quiz_result(
    evaluated_responses: List[Dict[str, Any]],
    max_marks: float,
    passing_marks: float
) -> Dict[str, Any]:
    """BR-QZ-020: Calculate aggregate marks, percentage, and pass/fail."""
    total_obtained = 0.0
    total_negative = 0.0
    correct_count = 0
    incorrect_count = 0
    unanswered_count = 0

    for resp in evaluated_responses:
        if not resp.get("is_answered", True):
            unanswered_count += 1
            continue

        if resp.get("is_correct", False):
            correct_count += 1
            total_obtained += resp.get("marks_obtained", 0.0)
        else:
            if resp.get("marks_obtained", 0.0) > 0:
                # Subjective response with positive marks
                total_obtained += resp.get("marks_obtained", 0.0)
            else:
                incorrect_count += 1
                neg = resp.get("negative_marks", 0.0)
                total_negative += neg
                total_obtained += resp.get("marks_obtained", 0.0)

    # Net score cannot drop below 0 unless negative marks policy dictates otherwise; standard is max(0, total_obtained)
    final_score = max(0.0, round(total_obtained, 2))
    percentage = round((final_score / max_marks) * 100.0, 2) if max_marks > 0 else 0.0
    is_passed = final_score >= passing_marks

    return {
        "total_marks": float(max_marks),
        "marks_obtained": float(final_score),
        "negative_marks": float(round(total_negative, 2)),
        "percentage": percentage,
        "is_passed": is_passed,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "unanswered_count": unanswered_count,
    }


def check_result_visibility(
    result_status: ResultStatus | Status | str,
    student_id: int,
    target_student_id: int,
    permissions: FrozenSet[str] | Iterable[str]
) -> None:
    """BR-QZ-004 & BR-QZ-021: Results exposed only after release and only to authorized student/professor."""
    perms = frozenset(permissions)
    is_professor = ("*" in perms or "quiz.result.release" in perms or "quiz.quiz.create" in perms)

    if not is_professor:
        # Student request: must be own result
        if student_id != target_student_id:
            raise PermissionDenied("Students may only view their own quiz results.")
        # Must be released
        if result_status not in (Status.RELEASED, Status.RELEASED_VIEWED):
            raise PermissionDenied("Quiz results have not been released yet.")
