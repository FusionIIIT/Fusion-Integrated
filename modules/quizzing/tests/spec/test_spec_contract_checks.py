"""Source-level contract checks for the Quizzing specification.

These checks deliberately use only the Python standard library so that the
specification gaps can be inspected even when the Django test environment is
not configured. They are not a substitute for API/database integration tests.
"""

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE = REPO_ROOT / "modules" / "quizzing"


def source(relative_path: str) -> str:
    return (MODULE / relative_path).read_text(encoding="utf-8")


def all_module_python() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in MODULE.rglob("*.py")
        if "tests" not in path.parts and "migrations" not in path.parts
    )


class QuizzingSpecificationChecks(unittest.TestCase):
    """Ten high-impact checks selected for an initial ~5/10 review."""

    def test_QZ_SPEC_001_AFR_QZ_001_3_student_quizzes_are_eligibility_scoped(self):
        """QZ-SPEC-001; source_id=AFR-QZ-001.3. Student listings are eligibility-scoped."""
        selector = source("selectors/quiz_selectors.py")
        function = selector.split("def get_student_quizzes", 1)[1].split("\ndef ", 1)[0]
        self.assertGreater(
            function.count("student_id"),
            1,
            "get_student_quizzes accepts student_id but does not use it to scope the queryset",
        )

    def test_QZ_SPEC_002_AFR_QZ_005_2_question_bank_has_management_api(self):
        """QZ-SPEC-002; source_id=AFR-QZ-005.2. Professors can search/filter the bank."""
        urls = source("api/urls.py").lower()
        views = source("api/views.py").lower()
        self.assertTrue(
            "question-bank" in urls or "question_banks" in urls or "question bank" in views,
            "No question-bank management/search API is routed by the module",
        )

    def test_QZ_SPEC_003_BR_QZ_017_attempt_expiry_triggers_without_a_student_request(self):
        """QZ-SPEC-003; source_id=BR-QZ-017. Expiry submits without a student request."""
        module_code = all_module_python().lower()
        self.assertTrue(
            "shared_task" in module_code or "periodic_task" in module_code or "beat_schedule" in module_code,
            "No background/event trigger is present to submit an idle attempt at its deadline",
        )

    def test_QZ_SPEC_004_AFR_QZ_012_2_ai_subjective_evaluation_is_integrated(self):
        """QZ-SPEC-004; source_id=AFR-QZ-012.2. AI marks remain advisory."""
        services = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in (MODULE / "services").glob("*.py")
        )
        self.assertTrue(
            "ai" in services and ("suggested_marks" in services or "evaluation_reasoning" in services),
            "No AI evaluation integration or advisory result fields exist in the service layer",
        )

    def test_QZ_SPEC_005_AFR_QZ_015_2_quiz_performance_metrics_are_exposed(self):
        """QZ-SPEC-005; source_id=AFR-QZ-015.2. Professor quiz metrics are exposed."""
        urls = source("api/urls.py").lower()
        module_code = all_module_python().lower()
        has_metrics = all(
            label in module_code
            for label in ("average_score", "highest_score", "lowest_score", "pass_percentage")
        )
        self.assertTrue(
            has_metrics and ("performance" in urls or "report" in urls or "analytics" in urls),
            "No quiz performance metric/report endpoint or aggregate implementation exists",
        )

    def test_QZ_SPEC_006_BR_QZ_008_attempt_limit_is_enforced(self):
        """QZ-SPEC-006; source_id=BR-QZ-008. Starting checks the configured limit."""
        service = source("services/quiz_service.py")
        self.assertIn("validate_attempt_limit(past_attempts_count, quiz.max_attempts)", service)

    def test_QZ_SPEC_007_BR_QZ_006_invalid_schedule_is_rejected(self):
        """QZ-SPEC-007; source_id=BR-QZ-006. Invalid schedules are rejected."""
        rules = source("domain/rules.py")
        self.assertIn("if end_time <= start_time:", rules)
        self.assertIn("if duration_minutes <= 0:", rules)

    def test_QZ_SPEC_008_BR_QZ_016_submitted_attempt_answers_are_locked(self):
        """QZ-SPEC-008; source_id=BR-QZ-016. Submitted attempts are immutable."""
        service = source("services/quiz_service.py")
        self.assertIn("if attempt.status != AttemptState.IN_PROGRESS:", service)

    def test_QZ_SPEC_009_BR_QZ_010_linear_navigation_blocks_backtracking(self):
        """QZ-SPEC-009; source_id=BR-QZ-010. Linear mode blocks backtracking."""
        service = source("services/quiz_service.py")
        rules = source("domain/rules.py")
        self.assertIn("validate_linear_navigation(current_order, attempt.last_answered_order)", service)
        self.assertIn("if current_order < last_completed_order:", rules)

    def test_QZ_SPEC_010_BR_QZ_021_unreleased_scores_are_hidden(self):
        """QZ-SPEC-010; source_id=BR-QZ-021. Unreleased scores are hidden."""
        serializers = source("api/serializers.py")
        self.assertIn("not attempt.quiz.grades_released", serializers)
        self.assertIn('ret["total_score"] = None', serializers)


if __name__ == "__main__":
    unittest.main()
