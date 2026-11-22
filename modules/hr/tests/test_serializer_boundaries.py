"""Serializer boundary behavior for HR request payloads."""

import pytest

from modules.hr.api.serializers import (
    AppraisalWindowWriteSerializer,
    ClaimCreateSerializer,
    EmployeeRecordPatchSerializer,
    EmployeeRecordWriteSerializer,
    LeaveBalanceManageSerializer,
    NoticeWriteSerializer,
    WorkflowRouteWriteSerializer,
)


@pytest.mark.parametrize(
    "serializer_class",
    [EmployeeRecordWriteSerializer, EmployeeRecordPatchSerializer],
)
def test_employee_serializers_reject_end_date_before_start_date(serializer_class):
    payload = {
        "appointment_start_date": "2026-08-01",
        "appointment_end_date": "2026-07-31",
    }
    if serializer_class is EmployeeRecordWriteSerializer:
        payload.update(user_id=1001, department="Research", designation="Officer")
    serializer = serializer_class(
        data=payload, partial=serializer_class is EmployeeRecordPatchSerializer
    )
    assert not serializer.is_valid()
    assert "appointment_end_date" in serializer.errors


def test_employee_serializers_accept_missing_or_ordered_appointment_dates():
    create = EmployeeRecordWriteSerializer(
        data={"user_id": 1001, "department": "Research", "designation": "Officer"}
    )
    patch = EmployeeRecordPatchSerializer(
        data={"appointment_start_date": "2020-01-01", "appointment_end_date": "2026-01-01"},
        partial=True,
    )
    assert create.is_valid(), create.errors
    assert patch.is_valid(), patch.errors


@pytest.mark.parametrize(
    ("link", "error_text"),
    [
        ("http://drive.google.com/file/d/abcdefghij/view", "https://"),
        ("https://evil.example/file/d/abcdefghij", "Only Google Drive links"),
        ("https://drive.google.com/drive/folders/abcdefghij", "folder"),
        ("https://drive.google.com/open?id=short", "does not point at a file"),
    ],
)
def test_claim_serializer_rejects_invalid_supporting_document(link, error_text):
    serializer = ClaimCreateSerializer(
        data={"request_type": "cpda_advance", "supporting_document_links": [link]}
    )
    assert not serializer.is_valid()
    assert error_text in str(serializer.errors["supporting_document_links"])


def test_claim_serializer_canonicalizes_valid_drive_links_and_defaults_optional_fields():
    serializer = ClaimCreateSerializer(
        data={
            "request_type": "cpda_advance",
            "supporting_document_links": [
                "https://drive.google.com/file/d/abcdefghij123/view?usp=sharing#fragment"
            ],
        }
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["purpose"] == ""
    assert serializer.validated_data["supporting_document_links"] == [
        "https://drive.google.com/file/d/abcdefghij123/view?usp=sharing#fragment"
    ]


def test_appraisal_window_serializer_requires_strictly_increasing_times():
    serializer = AppraisalWindowWriteSerializer(
        data={
            "period": "2026",
            "opens_at": "2026-01-02T00:00:00Z",
            "closes_at": "2026-01-02T00:00:00Z",
        }
    )
    assert not serializer.is_valid()
    assert "closes_at" in serializer.errors


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        (
            {
                "employee_user_id": 0,
                "leave_type": "casual",
                "available_days": "0",
                "is_eligible": True,
            },
            "employee_user_id",
        ),
        (
            {
                "employee_user_id": 1,
                "leave_type": "unknown",
                "available_days": "0",
                "is_eligible": True,
            },
            "leave_type",
        ),
        (
            {
                "employee_user_id": 1,
                "leave_type": "casual",
                "available_days": "-1",
                "is_eligible": True,
            },
            "available_days",
        ),
    ],
)
def test_leave_balance_serializer_rejects_invalid_identity_type_or_negative_balance(payload, field):
    serializer = LeaveBalanceManageSerializer(data=payload)
    assert not serializer.is_valid()
    assert field in serializer.errors


def test_notice_and_route_serializers_enforce_required_shape_and_choices():
    notice = NoticeWriteSerializer(data={"recipient_user_ids": [], "subject": "", "body": ""})
    route = WorkflowRouteWriteSerializer(
        data={"employee_category": "students", "request_type": "made_up", "steps": []}
    )
    assert not notice.is_valid()
    assert not route.is_valid()
    assert {"recipient_user_ids", "subject", "body"}.intersection(notice.errors)
    assert {"employee_category", "request_type", "steps"}.intersection(route.errors)
