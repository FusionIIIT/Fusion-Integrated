"""Unit tests for ELM serializers and input validation."""
import pytest
from rest_framework.exceptions import ValidationError

from modules.elm.api.serializers import (
    ApprovalActionSerializer,
    LeaveApplicationCreateSerializer,
    LeaveCancelRequestSerializer,
    ReplacementSubstituteSerializer,
    SubstituteActionSerializer,
)


class TestLeaveApplicationCreateSerializer:
    def test_start_after_end_rejected(self):
        data = {
            "leave_type": "CL",
            "start_date": "2026-10-10",
            "end_date": "2026-10-05",
            "reason": "Test",
        }
        ser = LeaveApplicationCreateSerializer(data=data)
        with pytest.raises(ValidationError) as exc:
            ser.is_valid(raise_exception=True)
        assert "end_date" in exc.value.detail

    def test_half_day_non_cl_rejected(self):
        data = {
            "leave_type": "EL",
            "start_date": "2026-10-05",
            "end_date": "2026-10-05",
            "half_day": True,
            "half_day_type": "first_half",
            "reason": "Test",
        }
        ser = LeaveApplicationCreateSerializer(data=data)
        with pytest.raises(ValidationError) as exc:
            ser.is_valid(raise_exception=True)
        assert "half_day" in exc.value.detail

    def test_half_day_multi_date_rejected(self):
        data = {
            "leave_type": "CL",
            "start_date": "2026-10-05",
            "end_date": "2026-10-06",
            "half_day": True,
            "half_day_type": "first_half",
            "reason": "Test",
        }
        ser = LeaveApplicationCreateSerializer(data=data)
        with pytest.raises(ValidationError) as exc:
            ser.is_valid(raise_exception=True)
        assert "half_day" in exc.value.detail

    def test_station_leave_without_address_rejected(self):
        data = {
            "leave_type": "CL",
            "start_date": "2026-10-05",
            "end_date": "2026-10-05",
            "is_station_leave": True,
            "station_address": "   ",
            "reason": "Test",
        }
        ser = LeaveApplicationCreateSerializer(data=data)
        with pytest.raises(ValidationError) as exc:
            ser.is_valid(raise_exception=True)
        assert "station_address" in exc.value.detail


class TestSubstituteActionSerializer:
    def test_valid_actions(self):
        for act in ["accept", "decline"]:
            ser = SubstituteActionSerializer(data={"action": act, "comments": "ok"})
            assert ser.is_valid(), ser.errors

    def test_invalid_action_rejected(self):
        ser = SubstituteActionSerializer(data={"action": "invalid"})
        assert not ser.is_valid()
        assert "action" in ser.errors


class TestApprovalActionSerializer:
    def test_valid_actions(self):
        for act in ["approve", "reject", "recommend", "not_recommend"]:
            ser = ApprovalActionSerializer(data={"action": act, "comments": "ok"})
            assert ser.is_valid(), ser.errors

    def test_invalid_action_rejected(self):
        ser = ApprovalActionSerializer(data={"action": "forward"})
        assert not ser.is_valid()
        assert "action" in ser.errors


class TestReplacementSubstituteSerializer:
    def test_valid_replacement(self):
        ser = ReplacementSubstituteSerializer(data={"substitute_id": 105})
        assert ser.is_valid(), ser.errors

    def test_missing_substitute_rejected(self):
        ser = ReplacementSubstituteSerializer(data={})
        assert not ser.is_valid()
        assert "substitute_id" in ser.errors


class TestLeaveCancelRequestSerializer:
    def test_valid_cancellation(self):
        ser = LeaveCancelRequestSerializer(data={"reason": "Change of plans"})
        assert ser.is_valid(), ser.errors
