"""Eligibility (PC-BR-002, PC-BR-004).

Two load-bearing properties: nothing reaches "eligible" by accident (the facts
come from a projection that can legitimately be empty), and every denial names
the actual value and the required one.
"""
from decimal import Decimal

from django.test import SimpleTestCase

from modules.placement.domain.eligibility import evaluate, failure_reasons


def facts(**kw):
    base = {"cpi": Decimal("8.0"), "active_backlogs": 0, "discipline": "CSE",
            "programme": "B.Tech", "batch_year": 2023, "is_placed": False,
            "is_registered": True, "skills": ["python", "sql"],
            "profile_complete": True, "earned_credits": Decimal("120"),
            "semester": 6, "offer_count": 0}
    base.update(kw)
    return base


class FailClosedTests(SimpleTestCase):

    def test_no_rule_means_no_restriction(self):
        self.assertTrue(evaluate({}, facts()).is_eligible)
        self.assertTrue(evaluate(None, facts()).is_eligible)

    def test_a_missing_fact_denies(self):
        """A student with no declared result has no CPI. That must deny, not
        be skipped and not be read as zero."""
        out = evaluate({"gte": ["cpi", 7.0]}, facts(cpi=None))
        self.assertFalse(out.is_eligible)
        self.assertEqual(out.outcomes[0].reason, "missing_fact")

    def test_an_unknown_field_denies(self):
        out = evaluate({"gte": ["favourite_colour", 7]}, facts())
        self.assertFalse(out.is_eligible)
        self.assertEqual(out.error, "unknown_field")

    def test_a_malformed_rule_denies(self):
        for rule in ({"gte": "not-a-pair"}, {"gte": [1, 2, 3]},
                     {"nonsense": ["cpi", 7]}, {"all": "not-a-list"}):
            self.assertFalse(evaluate(rule, facts()).is_eligible, rule)

    def test_an_empty_any_denies(self):
        self.assertFalse(evaluate({"any": []}, facts()).is_eligible)

    def test_deep_nesting_denies_rather_than_recursing(self):
        rule = {"gte": ["cpi", 1]}
        for _ in range(12):
            rule = {"all": [rule]}
        out = evaluate(rule, facts())
        self.assertFalse(out.is_eligible)
        self.assertEqual(out.error, "rule_too_complex")


class ComparisonTests(SimpleTestCase):

    def test_cpi_threshold(self):
        rule = {"gte": ["cpi", 7.0]}
        self.assertTrue(evaluate(rule, facts(cpi=Decimal("7.0"))).is_eligible)
        self.assertFalse(evaluate(rule, facts(cpi=Decimal("6.99"))).is_eligible)

    def test_discipline_allow_list(self):
        rule = {"in": ["discipline", ["CSE", "ECE"]]}
        self.assertTrue(evaluate(rule, facts(discipline="ECE")).is_eligible)
        self.assertFalse(evaluate(rule, facts(discipline="ME")).is_eligible)

    def test_zero_backlogs(self):
        rule = {"eq": ["active_backlogs", 0]}
        self.assertTrue(evaluate(rule, facts(active_backlogs=0)).is_eligible)
        self.assertFalse(evaluate(rule, facts(active_backlogs=1)).is_eligible)

    def test_all_requires_every_branch(self):
        rule = {"all": [{"gte": ["cpi", 7.0]}, {"eq": ["active_backlogs", 0]}]}
        self.assertTrue(evaluate(rule, facts()).is_eligible)
        self.assertFalse(evaluate(rule, facts(active_backlogs=2)).is_eligible)

    def test_any_requires_one_branch(self):
        rule = {"any": [{"gte": ["cpi", 9.5]}, {"in": ["discipline", ["CSE"]]}]}
        self.assertTrue(evaluate(rule, facts()).is_eligible)
        self.assertFalse(evaluate(rule, facts(discipline="ME")).is_eligible)

    def test_not_inverts(self):
        rule = {"not": {"eq": ["is_placed", True]}}
        self.assertTrue(evaluate(rule, facts(is_placed=False)).is_eligible)
        self.assertFalse(evaluate(rule, facts(is_placed=True)).is_eligible)


class SkillsTests(SimpleTestCase):
    """PC-BR-004 names skills explicitly."""

    def test_has_all(self):
        rule = {"has_all": ["skills", ["python", "sql"]]}
        self.assertTrue(evaluate(rule, facts()).is_eligible)
        self.assertFalse(
            evaluate(rule, facts(skills=["python"])).is_eligible)

    def test_has_any(self):
        rule = {"has_any": ["skills", ["rust", "sql"]]}
        self.assertTrue(evaluate(rule, facts()).is_eligible)
        self.assertFalse(evaluate(rule, facts(skills=["cobol"])).is_eligible)

    def test_matching_ignores_case_and_whitespace(self):
        rule = {"has_all": ["skills", ["Python"]]}
        self.assertTrue(evaluate(rule, facts(skills=[" python "])).is_eligible)

    def test_an_empty_skill_list_fails_has_all(self):
        rule = {"has_all": ["skills", ["python"]]}
        self.assertFalse(evaluate(rule, facts(skills=[])).is_eligible)

    def test_a_scalar_operator_on_a_list_field_denies(self):
        """A rule-authoring mistake, but it still denies — guessing what was
        meant is how someone becomes eligible by accident."""
        out = evaluate({"eq": ["skills", "python"]}, facts())
        self.assertFalse(out.is_eligible)
        self.assertEqual(out.outcomes[0].reason, "operator_not_valid_for_field")

    def test_a_list_operator_on_a_scalar_field_denies(self):
        out = evaluate({"has_all": ["cpi", [7]]}, facts())
        self.assertFalse(out.is_eligible)
        self.assertEqual(out.outcomes[0].reason, "operator_not_valid_for_field")


class ExplanationTests(SimpleTestCase):

    def test_a_cpi_shortfall_names_both_numbers(self):
        out = evaluate({"gte": ["cpi", 7.0]}, facts(cpi=Decimal("6.80")))
        message = failure_reasons(out)[0]["message"]
        self.assertIn("6.80", message)
        self.assertIn("7.0", message)
        self.assertIn("CPI", message)

    def test_no_declared_result_says_so_plainly(self):
        out = evaluate({"gte": ["cpi", 7.0]}, facts(cpi=None))
        message = failure_reasons(out)[0]["message"]
        self.assertIn("declared", message.lower())

    def test_missing_skills_are_named(self):
        out = evaluate({"has_all": ["skills", ["rust", "go"]]},
                       facts(skills=["python"]))
        message = failure_reasons(out)[0]["message"]
        self.assertIn("rust", message)
        self.assertIn("go", message)

    def test_a_discipline_mismatch_lists_what_is_accepted(self):
        out = evaluate({"in": ["discipline", ["CSE", "ECE"]]},
                       facts(discipline="ME"))
        message = failure_reasons(out)[0]["message"]
        self.assertIn("CSE", message)
        self.assertIn("ME", message)

    def test_only_failures_are_reported(self):
        out = evaluate({"all": [{"gte": ["cpi", 7.0]},
                                {"eq": ["active_backlogs", 5]}]}, facts())
        reasons = failure_reasons(out)
        self.assertEqual(len(reasons), 1)
        self.assertEqual(reasons[0]["field"], "active_backlogs")

    def test_a_broken_rule_does_not_blame_the_student(self):
        out = evaluate({"gte": ["nonexistent_field", 1]}, facts())
        message = failure_reasons(out)[0]["message"]
        self.assertIn("placement office", message.lower())
