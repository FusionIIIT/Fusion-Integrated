from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from modules.elm.api.serializers import (
    ApplyLeaveInputSerializer,
    LeaveActionHistorySerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    ReviewActionInputSerializer,
    SubstituteActionInputSerializer,
    SubstituteAssignmentSerializer,
)
from modules.elm.models import LeaveActionHistory, LeaveBalance, LeaveRequest, SubstituteAssignment

pytestmark = pytest.mark.django_db


def _balance(**kwargs):
    return LeaveBalance.objects.create(
        user_id=kwargs.get("user_id", 101), category=kwargs.get("category", "CL"),
        year=kwargs.get("year", 2026), credited=kwargs.get("credited", Decimal("8")),
        availed=kwargs.get("availed", Decimal("0")), balance=kwargs.get("balance", Decimal("8")),
    )


def _request(**kwargs):
    return LeaveRequest.objects.create(
        user_id=kwargs.get("user_id", 101), category=kwargs.get("category", "CL"),
        start_date=kwargs.get("start_date", date(2026, 7, 1)),
        end_date=kwargs.get("end_date", date(2026, 7, 1)), leave_days=kwargs.get("leave_days", Decimal("1")),
        purpose=kwargs.get("purpose", "Testing"), status=kwargs.get("status", "under_review"),
        **{k: v for k, v in kwargs.items() if k not in {"user_id", "category", "start_date", "end_date", "leave_days", "purpose", "status"}},
    )


@pytest.mark.parametrize("category", ["CL", "RH", "SCL", "EL", "VL", "COL"])
def test_leave_balance_serializer_exposes_values_read_only(category):
    balance = _balance(category=category)
    serializer = LeaveBalanceSerializer(balance)
    assert serializer.data["category"] == category
    assert "balance" in serializer.data
    assert serializer.fields["balance"].read_only
    assert set(serializer.data) == {"id", "user_id", "category", "year", "credited", "availed", "balance", "created_at", "updated_at"}


def test_leave_balance_unique_per_user_category_year():
    _balance()
    with pytest.raises(IntegrityError), transaction.atomic():
        _balance()


@pytest.mark.parametrize("user_id,category,year", [(101, "EL", 2026), (102, "CL", 2026), (101, "CL", 2027)])
def test_leave_balance_unique_key_allows_different_key_dimensions(user_id, category, year):
    _balance()
    assert _balance(user_id=user_id, category=category, year=year).pk


def test_leave_request_serializer_embeds_substitute_and_action_history():
    req = _request()
    assignment = SubstituteAssignment.objects.create(leave_request=req, substitute_id=102)
    action = LeaveActionHistory.objects.create(leave_request=req, actor_id=101, action="submitted")
    payload = LeaveRequestSerializer(req).data
    assert payload["substitute_assignments"][0]["id"] == assignment.pk
    assert payload["actions"][0]["id"] == action.pk
    assert payload["user_id"] == 101


@pytest.mark.parametrize("field", ["id", "user_id", "leave_days", "status", "rejection_reason", "resumption_status", "created_at", "updated_at", "actions", "substitute_assignments"])
def test_leave_request_derived_and_identity_fields_are_read_only(field):
    assert LeaveRequestSerializer().fields[field].read_only


def test_leave_request_input_keeps_optional_fields_optional():
    serializer = ApplyLeaveInputSerializer(data={"category": "CL", "start_date": "2026-07-01", "end_date": "2026-07-01", "purpose": "Errand"})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["is_station_leave"] is False
    assert serializer.validated_data["destination"] == ""
    assert serializer.validated_data["emergency_contact"] == ""


@pytest.mark.parametrize("field,value", [("category", ""), ("category", "X" * 11), ("start_date", "not-a-date"), ("end_date", "2026-02-30"), ("purpose", "")])
def test_apply_input_rejects_invalid_required_fields(field, value):
    data = {"category": "CL", "start_date": "2026-07-01", "end_date": "2026-07-01", "purpose": "Errand"}
    data[field] = value
    serializer = ApplyLeaveInputSerializer(data=data)
    assert not serializer.is_valid()


@pytest.mark.parametrize("value", ["", None, "first", "second", "unknown"])
def test_apply_input_accepts_half_day_text_and_null(value):
    data = {"category": "CL", "start_date": "2026-07-01", "end_date": "2026-07-01", "purpose": "Errand", "half_day": value}
    serializer = ApplyLeaveInputSerializer(data=data)
    assert serializer.is_valid(), serializer.errors


@pytest.mark.parametrize("action", ["accept", "decline"])
def test_substitute_input_accepts_only_declared_actions(action):
    serializer = SubstituteActionInputSerializer(data={"action": action})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["remarks"] == ""


@pytest.mark.parametrize("action", ["approve", "reject", "recommend"])
def test_review_input_accepts_declared_actions(action):
    serializer = ReviewActionInputSerializer(data={"action": action})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["reason"] == ""


@pytest.mark.parametrize("action", ["", "approved", "withdraw", None])
def test_action_serializers_reject_unknown_actions(action):
    sub = SubstituteActionInputSerializer(data={"action": action})
    review = ReviewActionInputSerializer(data={"action": action})
    assert not sub.is_valid()
    assert not review.is_valid()


def test_substitute_and_history_serializer_read_only_contracts():
    req = _request()
    assignment = SubstituteAssignment.objects.create(leave_request=req, substitute_id=102)
    event = LeaveActionHistory.objects.create(leave_request=req, actor_id=101, action="submitted")
    assert SubstituteAssignmentSerializer(assignment).fields["id"].read_only
    assert SubstituteAssignmentSerializer(assignment).fields["created_at"].read_only
    assert all(f.read_only for f in LeaveActionHistorySerializer(event).fields.values())


def test_deleting_leave_request_cascades_assignments_and_history():
    req = _request()
    assignment = SubstituteAssignment.objects.create(leave_request=req, substitute_id=102)
    event = LeaveActionHistory.objects.create(leave_request=req, actor_id=101, action="submitted")
    req.delete()
    assert not SubstituteAssignment.objects.filter(pk=assignment.pk).exists()
    assert not LeaveActionHistory.objects.filter(pk=event.pk).exists()
