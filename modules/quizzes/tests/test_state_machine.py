import unittest
from datetime import datetime, timedelta

from modules.quizzes.domain.state_machine import (
    Status,
    QuizStatus,
    AttemptStatus,
    ResultStatus,
    validate_transition,
    validate_quiz_transition,
    validate_attempt_transition,
    validate_evaluation_transition,
    InvalidTransition,
    PermissionDenied,
    BusinessRuleViolation,
    check_course_scope,
    check_student_eligibility,
    check_pre_activation_edit,
    check_availability_window,
    check_attempt_allowance,
    check_submission_immutability,
    check_auto_submit_expiry,
    evaluate_objective_response,
    evaluate_subjective_response,
    calculate_quiz_result,
    check_result_visibility,
)


class TestQuizStateMachine(unittest.TestCase):
    """Test Suite for Module 20 (QUIZZES) Domain State Machine and Rules."""

    # ---------------------------------------------------------
    # 1. Valid Transitions across Three Composite Workflows
    # ---------------------------------------------------------
    def test_valid_transitions_cw_qz_01_quiz_lifecycle(self):
        """CW-QZ-01: Quiz preparation, question configuration, scheduling, availability, archive."""
        valid_quiz_transitions = [
            (Status.DRAFT, Status.DRAFT_CONFIGURED_WITH_QUESTIONS, {"quiz.quiz.manage_questions"}),
            (Status.DRAFT_CONFIGURED_WITH_QUESTIONS, Status.DRAFT, {"quiz.quiz.manage_questions"}),
            (Status.DRAFT_CONFIGURED_WITH_QUESTIONS, Status.READY_FOR_PUBLICATION, {"quiz.quiz.configure"}),
            (Status.DRAFT_CONFIGURED_WITH_QUESTIONS, Status.READY_FOR_SCHEDULING, {"quiz.quiz.configure"}),
            (Status.READY_FOR_PUBLICATION, Status.AVAILABLE, {"quiz.quiz.publish"}),
            (Status.READY_FOR_SCHEDULING, Status.SCHEDULED, {"quiz.quiz.publish"}),
            (Status.SCHEDULED, Status.AVAILABLE, {"quiz.system.process_boundary"}),
            (Status.AVAILABLE, Status.CLOSED, {"quiz.system.process_boundary"}),
            (Status.CLOSED, Status.ARCHIVED, {"quiz.quiz.archive"}),
        ]
        for from_status, to_status, perms in valid_quiz_transitions:
            validate_transition(from_status, to_status, perms)
            validate_quiz_transition(from_status, to_status, perms)

    def test_valid_transitions_cw_qz_02_attempt_lifecycle(self):
        """CW-QZ-02: Student attempt start, response recording, manual submit, auto-submit."""
        valid_attempt_transitions = [
            (Status.AVAILABLE, Status.IN_PROGRESS, {"quiz.attempt.start"}),
            (Status.IN_PROGRESS, Status.IN_PROGRESS_RESPONSES_RECORDED, {"quiz.attempt.record_response"}),
            (Status.IN_PROGRESS_RESPONSES_RECORDED, Status.IN_PROGRESS_RESPONSES_RECORDED, {"quiz.attempt.record_response"}),
            (Status.IN_PROGRESS_RESPONSES_RECORDED, Status.SUBMITTED, {"quiz.attempt.submit"}),
            (Status.IN_PROGRESS, Status.SUBMITTED, {"quiz.attempt.submit"}),
            (Status.IN_PROGRESS_RESPONSES_RECORDED, Status.SUBMITTED, {"quiz.system.auto_submit"}),
            (Status.IN_PROGRESS, Status.SUBMITTED, {"quiz.system.auto_submit"}),
        ]
        for from_status, to_status, perms in valid_attempt_transitions:
            validate_transition(from_status, to_status, perms)
            validate_attempt_transition(from_status, to_status, perms)

    def test_valid_transitions_cw_qz_03_evaluation_lifecycle(self):
        """CW-QZ-03: Objective eval, mixed partial eval, subjective eval, result release, viewing."""
        valid_eval_transitions = [
            # Objective-only evaluation
            (Status.SUBMITTED, Status.EVALUATED, {"quiz.system.evaluate_objective"}),
            # Mixed evaluation: objective portion first
            (Status.SUBMITTED, Status.PARTIALLY_EVALUATED, {"quiz.system.evaluate_objective"}),
            # Subjective evaluation by professor
            (Status.SUBMITTED, Status.EVALUATED, {"quiz.evaluation.evaluate_subjective"}),
            (Status.PARTIALLY_EVALUATED, Status.EVALUATED, {"quiz.evaluation.evaluate_subjective"}),
            # Result release by professor
            (Status.EVALUATED, Status.RELEASED, {"quiz.result.release"}),
            # Student views released result
            (Status.RELEASED, Status.RELEASED_VIEWED, {"quiz.result.view"}),
            (Status.RELEASED, Status.RELEASED, {"quiz.result.view"}),
        ]
        for from_status, to_status, perms in valid_eval_transitions:
            validate_transition(from_status, to_status, perms)
            validate_evaluation_transition(from_status, to_status, perms)

    def test_valid_transition_wildcard_permission(self):
        """Wildcard permission '*' must satisfy any valid transition."""
        validate_transition(Status.DRAFT, Status.DRAFT_CONFIGURED_WITH_QUESTIONS, {"*"})
        validate_transition(Status.AVAILABLE, Status.IN_PROGRESS, {"*"})
        validate_transition(Status.SUBMITTED, Status.EVALUATED, {"*"})
        validate_transition(Status.EVALUATED, Status.RELEASED, {"*"})

    # ---------------------------------------------------------
    # 2. Invalid Transitions and Errors
    # ---------------------------------------------------------
    def test_invalid_transitions(self):
        """Illegal transitions must raise InvalidTransition even with wildcard permissions."""
        invalid_pairs = [
            (Status.DRAFT, Status.CLOSED),
            (Status.AVAILABLE, Status.ARCHIVED),
            (Status.SUBMITTED, Status.IN_PROGRESS),
            (Status.RELEASED, Status.DRAFT),
            (Status.ARCHIVED, Status.AVAILABLE),
            (Status.EVALUATED, Status.IN_PROGRESS),
        ]
        for from_s, to_s in invalid_pairs:
            with self.assertRaises(InvalidTransition):
                validate_transition(from_s, to_s, {"*"})

    def test_invalid_permissions(self):
        """Valid transition with missing or wrong permission must raise PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            validate_transition(Status.DRAFT, Status.DRAFT_CONFIGURED_WITH_QUESTIONS, set())
        with self.assertRaises(PermissionDenied):
            validate_transition(Status.DRAFT, Status.DRAFT_CONFIGURED_WITH_QUESTIONS, {"wrong.permission"})
        with self.assertRaises(PermissionDenied):
            validate_transition(Status.AVAILABLE, Status.IN_PROGRESS, {"quiz.quiz.publish"})
        with self.assertRaises(PermissionDenied):
            validate_transition(Status.EVALUATED, Status.RELEASED, {"quiz.attempt.submit"})

    # ---------------------------------------------------------
    # 3. Quiz Publication and Scheduling (CW-QZ-01)
    # ---------------------------------------------------------
    def test_quiz_publication_and_scheduling(self):
        """Verify immediate publication, future scheduling, boundary progression, and archival."""
        # Immediate availability
        validate_transition(Status.READY_FOR_PUBLICATION, Status.AVAILABLE, {"quiz.quiz.publish"})
        # Future scheduled availability
        validate_transition(Status.READY_FOR_SCHEDULING, Status.SCHEDULED, {"quiz.quiz.publish"})
        # System makes scheduled quiz available
        validate_transition(Status.SCHEDULED, Status.AVAILABLE, {"quiz.system.process_boundary"})
        # System closes available quiz
        validate_transition(Status.AVAILABLE, Status.CLOSED, {"quiz.system.process_boundary"})
        # Professor archives closed quiz
        validate_transition(Status.CLOSED, Status.ARCHIVED, {"quiz.quiz.archive"})

        # Cannot archive directly from Available or Draft
        with self.assertRaises(InvalidTransition):
            validate_transition(Status.AVAILABLE, Status.ARCHIVED, {"quiz.quiz.archive"})
        with self.assertRaises(InvalidTransition):
            validate_transition(Status.DRAFT, Status.ARCHIVED, {"quiz.quiz.archive"})

    # ---------------------------------------------------------
    # 4. Student Eligibility and Attempt Restrictions
    # ---------------------------------------------------------
    def test_course_scope_restriction(self):
        """BR-QZ-002: Professor may manage quizzes only for associated courses."""
        authorized_courses = ["CS101", "CS202"]
        # Valid course access
        check_course_scope(professor_id=1, course_id="CS101", authorized_courses=authorized_courses)
        # Out of scope course
        with self.assertRaises(PermissionDenied):
            check_course_scope(professor_id=1, course_id="ME301", authorized_courses=authorized_courses)

    def test_student_eligibility(self):
        """BR-QZ-003: Student may access only eligible quizzes."""
        eligible_students = [101, 102, 103]
        # Eligible student
        check_student_eligibility(student_id=101, quiz_id=1, eligible_student_ids=eligible_students)
        # Ineligible student
        with self.assertRaises(PermissionDenied):
            check_student_eligibility(student_id=999, quiz_id=1, eligible_student_ids=eligible_students)

    def test_permitted_attempts_limit(self):
        """BR-QZ-008: Student cannot exceed permitted attempt limit."""
        # Remaining attempt
        check_attempt_allowance(attempts_taken=0, permitted_attempts=2)
        check_attempt_allowance(attempts_taken=1, permitted_attempts=2)
        # Exhausted attempt allowance
        with self.assertRaises(BusinessRuleViolation):
            check_attempt_allowance(attempts_taken=2, permitted_attempts=2)
        with self.assertRaises(BusinessRuleViolation):
            check_attempt_allowance(attempts_taken=3, permitted_attempts=2)

    def test_availability_window(self):
        """BR-QZ-006: Student cannot start quiz outside availability period."""
        now = datetime(2026, 11, 2, 10, 0, 0)
        start = datetime(2026, 11, 2, 9, 0, 0)
        close = datetime(2026, 11, 2, 12, 0, 0)

        # Within window
        check_availability_window(now, start, close)

        # Before start window
        with self.assertRaises(BusinessRuleViolation):
            check_availability_window(now, start_time=datetime(2026, 11, 2, 11, 0, 0), closing_time=close)

        # After closing window
        with self.assertRaises(BusinessRuleViolation):
            check_availability_window(now, start_time=start, closing_time=datetime(2026, 11, 2, 9, 30, 0))

    def test_pre_activation_edit_boundary(self):
        """BR-QZ-005: Details/questions editable only before quiz becomes active."""
        # Editable statuses
        check_pre_activation_edit(Status.DRAFT)
        check_pre_activation_edit(Status.DRAFT_CONFIGURED_WITH_QUESTIONS)
        check_pre_activation_edit(Status.READY_FOR_PUBLICATION)
        check_pre_activation_edit(Status.READY_FOR_SCHEDULING)
        check_pre_activation_edit(Status.SCHEDULED)

        # Non-editable active / closed / archived statuses
        with self.assertRaises(BusinessRuleViolation):
            check_pre_activation_edit(Status.AVAILABLE)
        with self.assertRaises(BusinessRuleViolation):
            check_pre_activation_edit(Status.CLOSED)
        with self.assertRaises(BusinessRuleViolation):
            check_pre_activation_edit(Status.ARCHIVED)

    # ---------------------------------------------------------
    # 5. Response Recording, Manual and Automatic Submission (CW-QZ-02)
    # ---------------------------------------------------------
    def test_response_recording_and_manual_submission(self):
        """CW-QZ-02: Recording responses during attempt and manual submission."""
        validate_transition(Status.IN_PROGRESS, Status.IN_PROGRESS_RESPONSES_RECORDED, {"quiz.attempt.record_response"})
        validate_transition(Status.IN_PROGRESS_RESPONSES_RECORDED, Status.SUBMITTED, {"quiz.attempt.submit"})

    def test_automatic_submission_on_time_expiry(self):
        """CW-QZ-02 & BR-QZ-017: System auto-submits when time expires."""
        start = datetime(2026, 11, 2, 10, 0, 0)
        duration_minutes = 30

        # Before expiry: 20 mins passed
        is_expired = check_auto_submit_expiry(datetime(2026, 11, 2, 10, 20, 0), start, duration_minutes)
        self.assertFalse(is_expired)

        # At/after expiry: 30 and 35 mins passed
        is_expired_at = check_auto_submit_expiry(datetime(2026, 11, 2, 10, 30, 0), start, duration_minutes)
        self.assertTrue(is_expired_at)
        is_expired_after = check_auto_submit_expiry(datetime(2026, 11, 2, 10, 35, 0), start, duration_minutes)
        self.assertTrue(is_expired_after)

        # Transition executed by System
        validate_transition(Status.IN_PROGRESS_RESPONSES_RECORDED, Status.SUBMITTED, {"quiz.system.auto_submit"})

    def test_submission_immutability(self):
        """BR-QZ-016: Once submitted, an attempt cannot be modified."""
        # In progress is mutable
        check_submission_immutability(Status.IN_PROGRESS)
        check_submission_immutability(Status.IN_PROGRESS_RESPONSES_RECORDED)

        # Submitted is immutable
        with self.assertRaises(BusinessRuleViolation):
            check_submission_immutability(Status.SUBMITTED)

        # Cannot transition back to IN_PROGRESS
        with self.assertRaises(InvalidTransition):
            validate_transition(Status.SUBMITTED, Status.IN_PROGRESS, {"*"})
        with self.assertRaises(InvalidTransition):
            validate_transition(Status.SUBMITTED, Status.IN_PROGRESS_RESPONSES_RECORDED, {"*"})

    # ---------------------------------------------------------
    # 6. Objective and Subjective Evaluation (CW-QZ-03)
    # ---------------------------------------------------------
    def test_objective_evaluation_scoring(self):
        """BR-QZ-018 & BR-QZ-011: Objective evaluation with and without negative marking."""
        # MCQ correct
        res_mcq_correct = evaluate_objective_response(
            question_type="MCQ",
            correct_answer="B",
            student_answer="B",
            marks=2.0,
            negative_marks=0.5,
            negative_marking_enabled=True,
        )
        self.assertTrue(res_mcq_correct["is_correct"])
        self.assertEqual(res_mcq_correct["marks_obtained"], 2.0)
        self.assertEqual(res_mcq_correct["negative_marks"], 0.0)

        # MCQ incorrect with negative marking enabled
        res_mcq_wrong = evaluate_objective_response(
            question_type="MCQ",
            correct_answer="B",
            student_answer="C",
            marks=2.0,
            negative_marks=0.5,
            negative_marking_enabled=True,
        )
        self.assertFalse(res_mcq_wrong["is_correct"])
        self.assertEqual(res_mcq_wrong["marks_obtained"], -0.5)
        self.assertEqual(res_mcq_wrong["negative_marks"], 0.5)

        # MCQ incorrect with negative marking disabled
        res_mcq_wrong_no_neg = evaluate_objective_response(
            question_type="MCQ",
            correct_answer="B",
            student_answer="C",
            marks=2.0,
            negative_marks=0.5,
            negative_marking_enabled=False,
        )
        self.assertFalse(res_mcq_wrong_no_neg["is_correct"])
        self.assertEqual(res_mcq_wrong_no_neg["marks_obtained"], 0.0)
        self.assertEqual(res_mcq_wrong_no_neg["negative_marks"], 0.0)

        # True/False question
        res_tf = evaluate_objective_response("TF", "True", "true", 1.0)
        self.assertTrue(res_tf["is_correct"])

        # Multiple Select question (MSQ)
        res_msq = evaluate_objective_response("MSQ", ["A", "C"], ["A", "C"], 3.0)
        self.assertTrue(res_msq["is_correct"])
        res_msq_wrong = evaluate_objective_response("MSQ", ["A", "C"], ["A", "B"], 3.0)
        self.assertFalse(res_msq_wrong["is_correct"])

        # Fill in the blank (FITB)
        res_fitb = evaluate_objective_response("FITB", "Python", "python", 2.0)
        self.assertTrue(res_fitb["is_correct"])

        # Unanswered question (no negative marks applied)
        res_unanswered = evaluate_objective_response("MCQ", "A", None, 2.0, negative_marks=0.5, negative_marking_enabled=True)
        self.assertFalse(res_unanswered["is_answered"])
        self.assertEqual(res_unanswered["marks_obtained"], 0.0)

    def test_subjective_evaluation_professor_authority(self):
        """BR-QZ-019: AI suggestions are advisory only; Professor confirmed marks are final."""
        # Professor confirms marks matching AI suggestion
        eval_ai_accepted = evaluate_subjective_response(
            professor_confirmed_marks=8.0,
            max_marks=10.0,
            ai_suggested_marks=8.0,
            feedback="Good structure and explanation."
        )
        self.assertEqual(eval_ai_accepted["marks_obtained"], 8.0)
        self.assertTrue(eval_ai_accepted["is_ai_advisory"])

        # Professor modifies AI suggestion (AI advised 7, Professor gives 9)
        eval_ai_modified = evaluate_subjective_response(
            professor_confirmed_marks=9.0,
            max_marks=10.0,
            ai_suggested_marks=7.0,
            feedback="Excellent depth beyond standard answer."
        )
        self.assertEqual(eval_ai_modified["marks_obtained"], 9.0)
        self.assertEqual(eval_ai_modified["ai_suggested_marks"], 7.0)

        # Manual evaluation without AI
        eval_manual = evaluate_subjective_response(
            professor_confirmed_marks=6.5,
            max_marks=10.0,
            ai_suggested_marks=None,
        )
        self.assertEqual(eval_manual["marks_obtained"], 6.5)
        self.assertFalse(eval_manual["is_ai_advisory"])

        # Validation: cannot exceed max marks or be negative
        with self.assertRaises(BusinessRuleViolation):
            evaluate_subjective_response(professor_confirmed_marks=12.0, max_marks=10.0)
        with self.assertRaises(BusinessRuleViolation):
            evaluate_subjective_response(professor_confirmed_marks=-1.0, max_marks=10.0)

    def test_aggregate_result_calculation(self):
        """BR-QZ-020: Compute total marks, net score, percentage, and pass/fail."""
        responses = [
            {"is_answered": True, "is_correct": True, "marks_obtained": 4.0, "negative_marks": 0.0},
            {"is_answered": True, "is_correct": False, "marks_obtained": -1.0, "negative_marks": 1.0},
            {"is_answered": True, "is_correct": False, "marks_obtained": 6.0, "negative_marks": 0.0}, # Subjective
            {"is_answered": False, "is_correct": False, "marks_obtained": 0.0, "negative_marks": 0.0},
        ]
        result = calculate_quiz_result(responses, max_marks=20.0, passing_marks=8.0)
        # Net score: 4.0 - 1.0 + 6.0 = 9.0
        self.assertEqual(result["marks_obtained"], 9.0)
        self.assertEqual(result["negative_marks"], 1.0)
        self.assertEqual(result["percentage"], 45.0)
        self.assertTrue(result["is_passed"])
        self.assertEqual(result["correct_count"], 1)
        self.assertEqual(result["incorrect_count"], 1)
        self.assertEqual(result["unanswered_count"], 1)

    # ---------------------------------------------------------
    # 7. Result Release and Visibility Permissions (CW-QZ-03)
    # ---------------------------------------------------------
    def test_result_release_and_visibility(self):
        """BR-QZ-004 & BR-QZ-021: Results exposed only when Released and to authorized recipient."""
        # Professor releases result
        validate_transition(Status.EVALUATED, Status.RELEASED, {"quiz.result.release"})

        # Student views own released result
        check_result_visibility(
            result_status=Status.RELEASED,
            student_id=101,
            target_student_id=101,
            permissions={"quiz.result.view"},
        )

        # Student cannot view unreleased result
        with self.assertRaises(PermissionDenied):
            check_result_visibility(
                result_status=Status.EVALUATED,
                student_id=101,
                target_student_id=101,
                permissions={"quiz.result.view"},
            )

        # Student cannot view another student's result
        with self.assertRaises(PermissionDenied):
            check_result_visibility(
                result_status=Status.RELEASED,
                student_id=101,
                target_student_id=999,
                permissions={"quiz.result.view"},
            )

        # Professor can view any result
        check_result_visibility(
            result_status=Status.EVALUATED,
            student_id=1,
            target_student_id=101,
            permissions={"quiz.result.release"},
        )

    # ---------------------------------------------------------
    # 8. Unauthorized Operations and Role Separation
    # ---------------------------------------------------------
    def test_role_separation_unauthorized_operations(self):
        """BR-QZ-001: Students cannot perform professor operations."""
        student_perms = {"quiz.attempt.start", "quiz.attempt.record_response", "quiz.attempt.submit", "quiz.result.view"}

        # Student cannot publish quiz
        with self.assertRaises(PermissionDenied):
            validate_transition(Status.READY_FOR_PUBLICATION, Status.AVAILABLE, student_perms)

        # Student cannot archive quiz
        with self.assertRaises(PermissionDenied):
            validate_transition(Status.CLOSED, Status.ARCHIVED, student_perms)

        # Student cannot evaluate subjective responses
        with self.assertRaises(PermissionDenied):
            validate_transition(Status.SUBMITTED, Status.EVALUATED, student_perms)

        # Student cannot release results
        with self.assertRaises(PermissionDenied):
            validate_transition(Status.EVALUATED, Status.RELEASED, student_perms)


if __name__ == "__main__":
    unittest.main()
