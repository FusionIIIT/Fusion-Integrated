"""Source-level contract checks for the Quizzing specification.

These checks deliberately use only the Python standard library so that the
specification gaps can be inspected even when the Django test environment is
not configured. They are not a substitute for API/database integration tests.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE = REPO_ROOT / "modules" / "quizzing"


def source(relative_path: str) -> str:
    return (MODULE / relative_path).read_text(encoding="utf-8")


class QuizzingSpecificationChecks(unittest.TestCase):
    """Ten focused source-level checks for Quizzing obligations."""

    def test_qz_spec_001_afr_qz_001_3_student_quizzes_are_eligibility_scoped(self):
        """QZ-SPEC-001; source_id=AFR-QZ-001.3. Student listings are eligibility-scoped."""
        selector = source("selectors/quiz_selectors.py")
        function = selector.split("def get_student_quizzes", 1)[1].split("\ndef ", 1)[0]
        self.assertRegex(
            function,
            re.compile(r"\.filter\([^)]*student_id", re.DOTALL),
            "get_student_quizzes accepts student_id but does not use it in a queryset predicate",
        )

    def test_qz_spec_002_afr_qz_005_2_question_bank_supports_required_filters(self):
        """QZ-SPEC-002; source_id=AFR-QZ-005.2. Bank search covers topic and difficulty."""
        views = source("api/views.py").lower()
        models = source("models.py").lower()
        self.assertIn('request.query_params.get("difficulty")', views)
        self.assertTrue("topic" in views and ("topic" in models or "unit" in models))

    def test_qz_spec_003_br_qz_017_expiry_task_is_registered_with_celery_beat(self):
        """QZ-SPEC-003; source_id=BR-QZ-017. The periodic task is scheduled."""
        celery = source("../../config/celery.py").lower()
        self.assertIn("quizzing.schedule", celery)
        self.assertIn("quizzing_schedule", celery)

    def test_qz_spec_004_afr_qz_012_2_ai_inputs_and_review_outputs_are_supported(self):
        """QZ-SPEC-004; source_id=AFR-QZ-012.2. AI review uses required inputs and outputs."""
        service = source("services/ai_evaluation_service.py").lower()
        self.assertIn("criteria", service)
        self.assertIn("strengths", service)
        self.assertTrue("missing" in service or "incorrect" in service)
        self.assertTrue("client" in service or "provider" in service)

    def test_qz_spec_005_afr_qz_015_2_analytics_separates_attempted_from_enrolled(self):
        """QZ-SPEC-005; source_id=AFR-QZ-015.2. Analytics reports both populations."""
        selector = source("selectors/quiz_selectors.py").lower()
        self.assertIn('"not_attempted_count"', selector)
        self.assertNotIn('"total_enrolled": attempted_count', selector)

    def test_qz_spec_006_br_qz_008_attempt_limit_is_enforced(self):
        """QZ-SPEC-006; source_id=BR-QZ-008. Starting checks the configured limit."""
        service = source("services/quiz_service.py")
        self.assertIn("validate_attempt_limit(past_attempts_count, quiz.max_attempts)", service)

    def test_qz_spec_007_br_qz_006_invalid_schedule_is_rejected(self):
        """QZ-SPEC-007; source_id=BR-QZ-006. Invalid schedules are rejected."""
        rules = source("domain/rules.py")
        self.assertIn("if end_time <= start_time:", rules)
        self.assertIn("if duration_minutes <= 0:", rules)

    def test_qz_spec_008_br_qz_016_submitted_attempt_answers_are_locked(self):
        """QZ-SPEC-008; source_id=BR-QZ-016. Submitted attempts are immutable."""
        service = source("services/quiz_service.py")
        self.assertIn("if attempt.status != AttemptState.IN_PROGRESS:", service)

    def test_qz_spec_009_br_qz_010_linear_navigation_blocks_backtracking(self):
        """QZ-SPEC-009; source_id=BR-QZ-010. Linear mode blocks backtracking."""
        service = source("services/quiz_service.py")
        rules = source("domain/rules.py")
        self.assertIn("validate_linear_navigation(current_order, attempt.last_answered_order)", service)
        self.assertIn("if current_order < last_completed_order:", rules)

    def test_qz_spec_010_br_qz_021_unreleased_scores_are_hidden(self):
        """QZ-SPEC-010; source_id=BR-QZ-021. Unreleased scores are hidden."""
        serializers = source("api/serializers.py")
        self.assertIn("not attempt.quiz.grades_released", serializers)
        self.assertIn('ret["total_score"] = None', serializers)


if __name__ == "__main__":
    unittest.main()
