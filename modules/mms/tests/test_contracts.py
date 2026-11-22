"""Unit tests for MMS contracts.py public surface.

Ensures contracts functions return expected DTO structures and are plural by signature.
"""

from unittest.mock import MagicMock, patch

from modules.mms import contracts


class TestContracts:
    def test_empty_inputs(self):
        assert contracts.get_users([]) == {}
        assert contracts.get_special_food_charges([], "2026-11-01") == {}
        assert contracts.get_menu_for_days([]) == {}
        assert contracts.get_vacation_survey_summaries([]) == {}

    @patch("modules.directory.contracts.get_users")
    def test_get_users(self, mock_dir_get_users):
        mock_dir_row = MagicMock(username="stu101", display_name="Student 101", kind="student")
        mock_dir_get_users.return_value = {101: mock_dir_row}

        res = contracts.get_users([101])
        assert 101 in res
        brief = res[101]
        assert brief.user_id == 101
        assert brief.username == "stu101"
        assert brief.display_name == "Student 101"
        assert brief.kind == "student"

    @patch("modules.mms.models.SpecialFoodCharge.objects")
    def test_get_special_food_charges(self, mock_sf):
        mock_charge = MagicMock(
            request_id=1,
            student_user_id=101,
            month="2026-11-01",
            amount="120.00",
        )
        mock_qs = MagicMock()
        mock_qs.order_by.return_value = [mock_charge]
        mock_sf.filter.return_value = mock_qs

        res = contracts.get_special_food_charges([101], "2026-11-01")
        assert 101 in res
        assert len(res[101]) == 1
        assert res[101][0].request_id == 1
        assert res[101][0].amount == "120.00"

    @patch("modules.mms.models.MenuItem.objects")
    def test_get_menu_for_days(self, mock_menu):
        mock_item = MagicMock(
            day="2026-11-23",
            meal="breakfast",
            item="Poha",
        )
        mock_qs = MagicMock()
        mock_qs.order_by.return_value = [mock_item]
        mock_menu.filter.return_value = mock_qs

        res = contracts.get_menu_for_days(["2026-11-23"])
        assert "2026-11-23" in res
        day_dto = res["2026-11-23"]
        assert day_dto.day == "2026-11-23"
        assert "breakfast" in day_dto.meals
        assert day_dto.meals["breakfast"] == ["Poha"]
