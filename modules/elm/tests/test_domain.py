from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import unittest

from modules.elm.domain.counting import chargeable_days, validate_rh_dates, validate_vacation
from modules.elm.domain.overlap import overlaps
from modules.elm.domain.policy import annual_credit_for, PolicyViolation, validate_params
from modules.elm.domain.routing import resolve_route, RouteError
from modules.elm.domain.state_machine import transition, InvalidTransition
from modules.elm.domain.year_end import vl_to_el

class LeaveCountingTests(unittest.TestCase):
    def test_half_day_cl_is_half(self):
        self.assertEqual(chargeable_days("CL", date(2026, 10, 29), date(2026, 10, 29), half="first"), Decimal("0.5"))

    def test_continuous_leave_includes_weekend(self):
        self.assertEqual(chargeable_days("EL", date(2026, 10, 30), date(2026, 11, 2)), Decimal("4"))

    def test_working_day_leave_excludes_weekend_and_closed_days(self):
        self.assertEqual(chargeable_days("CL", date(2026, 10, 30), date(2026, 11, 2), closed_dates={date(2026, 10, 30)}), Decimal("1"))

    def test_different_cl_halves_do_not_overlap(self):
        existing = SimpleNamespace(status="approved", start_date=date(2026, 10, 29), end_date=date(2026, 10, 29), category="CL", half="first")
        self.assertFalse(overlaps(date(2026, 10, 29), date(2026, 10, 29), "second", "CL", [existing]))
        self.assertTrue(overlaps(date(2026, 10, 29), date(2026, 10, 29), "", "CL", [existing]))

    def test_rh_must_match_single_published_rh_date(self):
        validate_rh_dates(date(2026, 11, 2), date(2026, 11, 2), {date(2026, 11, 2)})
        with self.assertRaises(ValueError):
            validate_rh_dates(date(2026, 11, 2), date(2026, 11, 3), {date(2026, 11, 2)})

    def test_vacation_must_contain_whole_period(self):
        validate_vacation(date(2026, 5, 1), date(2026, 5, 10), [(date(2026, 5, 1), date(2026, 5, 20))])
        with self.assertRaises(ValueError):
            validate_vacation(date(2026, 5, 1), date(2026, 5, 21), [(date(2026, 5, 1), date(2026, 5, 20))])

class PolicyAndRoutingTests(unittest.TestCase):
    def test_default_entitlements_and_eligibility(self):
        self.assertEqual(annual_credit_for("CL", "faculty"), Decimal("8"))
        self.assertEqual(annual_credit_for("EL", "staff"), Decimal("30"))
        with self.assertRaises(PolicyViolation):
            annual_credit_for("EL", "faculty")

    def test_policy_rejects_conflicting_carry_forward_rule(self):
        with self.assertRaises(PolicyViolation):
            validate_params({"CL": {"carry_forward": True}})

    def test_policy_requires_target_for_escalation(self):
        with self.assertRaises(PolicyViolation):
            validate_params({"sla": {"escalation_hours": 24}})

    def test_missing_unit_head_mapping_is_rejected(self):
        with self.assertRaises(RouteError):
            resolve_route(category="CL", applicant_role="staff", department="Unknown Unit", hierarchy={"unit_heads": {}})

    def test_cl_route_ends_at_unit_head(self):
        route = resolve_route(category="CL", applicant_role="staff", department="CSE", hierarchy={"unit_heads": {"CSE": "HOD (CSE)"}})
        self.assertEqual(len(route), 1)
        self.assertTrue(route[0]["final"])

    def test_fractional_vl_conversion(self):
        self.assertEqual(vl_to_el(Decimal("1.5")), Decimal("0.75"))

    def test_state_machine_rejects_illegal_transition(self):
        self.assertEqual(transition("awaiting_substitute", "substitute_accept", "substitute").target, "awaiting_unit_head")
        with self.assertRaises(InvalidTransition):
            transition("approved", "withdraw", "employee")

if __name__ == "__main__":
    unittest.main()
