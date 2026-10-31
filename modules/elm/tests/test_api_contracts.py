from types import SimpleNamespace

from django.test import SimpleTestCase

from modules.elm.api.serializers import (
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
)
from modules.elm.api.views import _actor_id
from modules.elm.models import (
    ApprovalRoutingConfiguration,
    LeaveApplication,
    LeaveBalance,
    LeaveCategory,
)
from modules.elm.services import LeaveValidationService


class ELMApiContractTests(SimpleTestCase):
    def test_application_accepts_category_code_and_keeps_employee_id_server_owned(self):
        serializer = LeaveApplicationSerializer()

        self.assertIn("leave_category_code", serializer.fields)
        self.assertFalse(serializer.fields["leave_category_code"].read_only)
        self.assertTrue(serializer.fields["employee_user_id"].read_only)

    def test_balance_response_uses_frontend_category_code(self):
        serializer = LeaveBalanceSerializer()

        self.assertIn("leave_category_code", serializer.fields)
        self.assertNotIn("leave_category", serializer.fields)

    def test_balance_primary_key_allows_multiple_categories_per_employee(self):
        self.assertNotEqual(LeaveBalance._meta.pk.name, "user_id")
        self.assertIn(
            ("user_id", "leave_category", "year"),
            LeaveBalance._meta.unique_together,
        )

    def test_actor_id_comes_from_fusion_principal(self):
        request = SimpleNamespace(principal=SimpleNamespace(user_id=42))

        self.assertEqual(_actor_id(request), 42)

    def test_actor_id_does_not_fall_back_to_a_fixed_user(self):
        request = SimpleNamespace(principal=None)

        self.assertIsNone(_actor_id(request))


class ELMLeaveCountingTests(SimpleTestCase):
    def make_application(self, start, end, *, continuous=False, day_part="full_day"):
        category = SimpleNamespace(continuous_day_counting=continuous)
        return SimpleNamespace(
            requested_start=start,
            requested_end=end,
            leave_category=category,
            day_part=day_part,
        )

    def test_half_day_cl_counts_as_half_day(self):
        from datetime import date

        application = self.make_application(
            date(2026, 4, 6), date(2026, 4, 6), day_part=LeaveApplication.DayPartChoices.FIRST_HALF
        )

        self.assertEqual(LeaveValidationService.count_requested_days(application), 0.5)

    def test_weekday_counting_excludes_weekends(self):
        from datetime import date

        application = self.make_application(date(2026, 4, 3), date(2026, 4, 6))

        self.assertEqual(LeaveValidationService.count_requested_days(application), 2)

    def test_continuous_counting_includes_weekends(self):
        from datetime import date

        application = self.make_application(date(2026, 4, 3), date(2026, 4, 6), continuous=True)

        self.assertEqual(LeaveValidationService.count_requested_days(application), 4)


class ELMRoutingConfigurationTests(SimpleTestCase):
    def test_incomplete_routing_is_not_ready_for_non_cl_categories(self):
        config = ApprovalRoutingConfiguration(
            unit_head_role="",
            establishment_enabled=None,
            establishment_role="",
            final_authority_role="",
        )
        config.leave_category = LeaveCategory(code="SCL")

        self.assertFalse(config.is_complete())

    def test_cl_routing_requires_unit_head_but_no_final_role(self):
        config = ApprovalRoutingConfiguration(
            unit_head_role="Unit Head",
            establishment_enabled=None,
            establishment_role="",
            final_authority_role="",
        )
        config.leave_category = LeaveCategory(code="CL")

        self.assertTrue(config.is_complete())
