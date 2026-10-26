"""Tests for LeaveApplication model validation constraints.

Verifies:
- BR-EL-014: Substitute self-nomination validation in clean()
- BR-EL-010: Half-day CL validation in clean()
- BR-EL-011: Start date vs end date ordering in clean()
- BR-EL-002: Exceeding annual entitlement in clean()
- Chargeable days computation method on LeaveApplication
"""
from __future__ import annotations

import unittest
from datetime import date

import modules.leave.tests._shim  # isort: skip # noqa: F401

from django.core.exceptions import ValidationError

from modules.leave.models import LeaveApplication, LeaveCategory


class TestLeaveApplicationValidation(unittest.TestCase):
    """Test model clean() validations for business rules."""

    def _create_app(
        self,
        user_id: int = 101,
        category: str = "CL",
        start_date: date | None = None,
        end_date: date | None = None,
        half_day_cl: bool = False,
        substitute_id: int | None = None,
    ) -> LeaveApplication:
        app = LeaveApplication()
        app.user_id = user_id
        app.category = category
        app.start_date = start_date or date(2026, 11, 2)
        app.end_date = end_date or date(2026, 11, 2)
        app.half_day_cl = half_day_cl
        app.substitute_id = substitute_id
        app.status = "draft"
        # Mock get_category_display if not provided by full Django runtime
        if not hasattr(app, "get_category_display"):
            app.get_category_display = lambda: dict(LeaveCategory.choices).get(app.category, app.category)
        return app

    def test_substitute_cannot_be_applicant_self(self):
        """BR-EL-014: clean() raises ValidationError if substitute is applicant."""
        app = self._create_app(user_id=101, substitute_id=101)
        with self.assertRaises(ValidationError) as ctx:
            app.clean()
        self.assertIn("substitute_id", ctx.exception.message_dict)

    def test_substitute_different_from_applicant_passes(self):
        """BR-EL-014: Valid substitute passes."""
        app = self._create_app(user_id=101, substitute_id=102)
        app.clean()  # Should not raise

    def test_substitute_none_passes(self):
        """BR-EL-014: When substitute is None, clean() passes."""
        app = self._create_app(user_id=101, substitute_id=None)
        app.clean()  # Should not raise

    def test_half_day_non_cl_rejected(self):
        """BR-EL-010: Half day on EL must be rejected."""
        d = date(2026, 11, 2)
        app = self._create_app(category="EL", start_date=d, end_date=d, half_day_cl=True)
        with self.assertRaises(ValidationError) as ctx:
            app.clean()
        self.assertIn("half_day_cl", ctx.exception.message_dict)

    def test_half_day_cl_multi_day_rejected(self):
        """BR-EL-010: Half day spanning multiple dates must be rejected."""
        app = self._create_app(
            category="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 3),
            half_day_cl=True,
        )
        with self.assertRaises(ValidationError) as ctx:
            app.clean()
        self.assertIn("half_day_cl", ctx.exception.message_dict)

    def test_start_date_after_end_date_rejected(self):
        """BR-EL-011: Start date after end date must be rejected."""
        app = self._create_app(
            category="CL",
            start_date=date(2026, 11, 5),
            end_date=date(2026, 11, 2),
        )
        with self.assertRaises(ValidationError) as ctx:
            app.clean()
        self.assertIn("start_date", ctx.exception.message_dict)

    def test_request_exceeding_annual_entitlement_rejected(self):
        """AFR-EL-003.2, BR-EL-002: Single application exceeding quota (e.g. 10 CL days > 8 quota) rejected."""
        # 2026-11-02 (Mon) to 2026-11-13 (Fri) = 10 working days of CL
        app = self._create_app(
            category="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 13),
        )
        with self.assertRaises(ValidationError) as ctx:
            app.clean()
        self.assertIn("category", ctx.exception.message_dict)

    def test_accumulated_el_not_blocked_by_annual_ceiling(self):
        """BR-EL-005: EL accumulates and carries forward, so a 40-day request is not blocked by clean()."""
        app = self._create_app(
            category="EL",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 12, 10),
        )
        app.clean()  # Should not raise; balance verification is handled by balance service

    def test_chargeable_days_method_on_model(self):
        """Verify chargeable_days helper computes correct duration."""
        app = self._create_app(
            category="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 2),
            half_day_cl=True,
        )
        self.assertEqual(app.chargeable_days(), 0.5)

        # 3 working days (Mon-Wed)
        app2 = self._create_app(
            category="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 4),
        )
        self.assertEqual(app2.chargeable_days(), 3.0)


if __name__ == "__main__":
    unittest.main()
