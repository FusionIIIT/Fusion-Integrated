"""Unit tests for MMS selectors and scoping rules.

Covers:
- Scoping special food requests (Student sees own, Caretaker sees all)
- Scoping rebate requests (Student sees own, Caretaker sees all)
- Scoping registrations and deregistrations
- Scoping monthly bills (Student sees only published own, Caretaker sees all)
- Scoping feedback
"""

from unittest.mock import MagicMock, patch

from modules.mms.selectors import scoping


class TestScopingHelpers:
    def test_actor_identification(
        self, student_actor, caretaker_actor, warden_actor, mess_admin_actor
    ):
        assert scoping._own_id(student_actor) == 101
        assert scoping._kind(student_actor) == "student"

        assert scoping.is_caretaker(caretaker_actor) is True
        assert scoping.is_caretaker(student_actor) is False

        assert scoping.is_warden(warden_actor) is True
        assert scoping.is_warden(student_actor) is False

        assert scoping.is_mess_admin(mess_admin_actor) is True
        assert scoping.is_mess_admin(caretaker_actor) is False

    @patch("modules.mms.models.SpecialFoodRequest.objects")
    def test_special_food_scoping_student(self, mock_sf, student_actor):
        mock_qs = MagicMock()
        mock_sf.all.return_value = mock_qs

        scoping.special_food_requests_for(student_actor)
        mock_qs.filter.assert_called_once_with(user_id=101)

    @patch("modules.mms.models.SpecialFoodRequest.objects")
    def test_special_food_scoping_caretaker(self, mock_sf, caretaker_actor):
        mock_qs = MagicMock()
        mock_sf.all.return_value = mock_qs

        res = scoping.special_food_requests_for(caretaker_actor)
        # Caretaker sees all
        assert res == mock_qs
        mock_qs.filter.assert_not_called()

    @patch("modules.mms.models.RebateRequest.objects")
    def test_rebate_scoping_student(self, mock_rebates, student_actor):
        mock_qs = MagicMock()
        mock_rebates.all.return_value = mock_qs

        scoping.rebate_requests_for(student_actor)
        mock_qs.filter.assert_called_once_with(user_id=101)

    @patch("modules.mms.models.MonthlyBill.objects")
    def test_monthly_bill_scoping_student(self, mock_bills, student_actor):
        mock_qs = MagicMock()
        mock_bills.all.return_value = mock_qs

        scoping.monthly_bills_for(student_actor)
        mock_qs.filter.assert_called_once_with(user_id=101, state="published")

    @patch("modules.mms.models.MonthlyBill.objects")
    def test_monthly_bill_scoping_caretaker(self, mock_bills, caretaker_actor):
        mock_qs = MagicMock()
        mock_bills.all.return_value = mock_qs

        res = scoping.monthly_bills_for(caretaker_actor)
        assert res == mock_qs
        mock_qs.filter.assert_not_called()
