"""Regression probes for the Student 1 independent-review technical findings."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.api.exceptions import BadRequestError, ConflictError
from modules.hreis.models import (
    AppraisalDetail,
    ApprovalRouteStep,
    EmployeeServiceRecord,
    HRPolicyVersion,
    HRRequest,
    Notification,
)
from modules.hreis.selectors.scoping import notifications_for
from modules.hreis.services import appraisals, notifications, policies
from modules.hreis.tests.actors import Principal, make_session
from modules.hreis.tests.test_appraisals_service import principal

pytestmark = pytest.mark.django_db


def _policy_manager():
    return Principal(
        user_id=99,
        username="synthetic-admin",
        display_name="Synthetic HR",
        kind="staff",
        active_role="hradmin",
        roles=("hradmin",),
        permissions=frozenset({"hreis.policy.manage"}),
        modules=("hreis",),
    )


def test_expired_policy_version_cannot_be_reused_or_return_http_500(stub_iam):
    """HR-UC-017: a family/version is immutable even after its window ends."""
    stub_iam(
        make_session(
            user_id=99,
            kind="staff",
            active_role="hradmin",
            roles=("hradmin",),
            permissions=("hreis.policy.manage",),
            modules=("hreis",),
        )
    )
    client = APIClient(raise_request_exception=False)
    client.credentials(HTTP_AUTHORIZATION="Token synthetic-test-token")
    now = timezone.now()
    original = {
        "family": "leave",
        "version": 1,
        "effective_from": (now - timedelta(days=3)).isoformat(),
        "effective_until": (now - timedelta(days=2)).isoformat(),
        "parameters": {"eligibility": {"staff": {"Casual": True}}},
    }
    assert client.post(
        "/api/v1/hreis/policies/", original, format="json",
        HTTP_IDEMPOTENCY_KEY="expired-version",
    ).status_code == 201
    successor = {
        **original,
        "effective_from": (now - timedelta(hours=1)).isoformat(),
        "effective_until": None,
    }
    response = client.post(
        "/api/v1/hreis/policies/", successor, format="json",
        HTTP_IDEMPOTENCY_KEY="attempt-reuse",
    )
    assert response.status_code == 409
    assert HRPolicyVersion.objects.filter(family="leave", version=1).count() == 1


def test_unbounded_reminder_interval_is_rejected_and_cannot_crash_worker():
    """HR-UC-021: reject unusable policy parameters before schedule arithmetic."""
    now = timezone.now()
    parameters = {
        "conditions": {
            "pending_reminder_after_hours": 10**100,
            "reminder_recipients": {"Registrar": [200]},
        }
    }
    with pytest.raises(BadRequestError) as error:
        policies.create_policy(
            _policy_manager(),
            family="leave",
            version=1,
            effective_from=now - timedelta(hours=1),
            effective_until=None,
            parameters=parameters,
            idempotency_key="oversize-reminder",
        )
    assert error.value.code == "invalid_reminder_config"
    assert not HRPolicyVersion.objects.exists()

    # A legacy row containing an invalid delay must not crash the scheduler.
    legacy = HRPolicyVersion.objects.create(
        family="leave",
        version=1,
        effective_from=now - timedelta(days=1),
        parameters=parameters,
        approved_by_user_id=99,
        approved_designation="hradmin",
    )
    request = HRRequest.objects.create(
        family="leave", user_id=10, state="pending_authority", policy_version=legacy,
    )
    ApprovalRouteStep.objects.create(
        request=request, position=0, designation="Registrar", policy_version_label="test",
    )
    HRRequest.objects.filter(pk=request.pk).update(updated_at=now - timedelta(days=2))
    assert notifications.create_pending_action_reminders(now=now) == 0


@pytest.fixture
def pending_appraisal():
    record = EmployeeServiceRecord.objects.create(
        user_id=10, department="CSE", designation_snapshot="Synthetic faculty",
    )
    row = HRRequest.objects.create(user_id=10, family="appraisal", state="submitted")
    AppraisalDetail.objects.create(
        request=row, employee_record=record, period_key="FY2026",
        submitted_form={"review": "Synthetic"}, reviewer_user_ids=[],
    )
    return row


def test_inactive_reviewers_cannot_be_assigned(pending_appraisal, monkeypatch):
    """HR-UC-007: IAM deactivated users cannot be assigned to ongoing reviews."""
    monkeypatch.setattr(
        appraisals,
        "get_users",
        lambda ids: {
            i: SimpleNamespace(kind="faculty", is_active=(i != 201))
            for i in ids
        },
    )
    with pytest.raises(ConflictError) as error:
        appraisals.assign_reviewers(
            principal(99, "hradmin", ("hreis.appraisal.assign",)),
            request_id=pending_appraisal.id,
            reviewer_user_ids=[201],
            idempotency_key="inactive-reviewer",
        )
    assert error.value.code == "reviewer_unknown"
    pending_appraisal.refresh_from_db()
    assert pending_appraisal.state == "submitted"
    assert pending_appraisal.appraisal.reviewer_user_ids == []


def test_authority_reminder_is_not_exposed_after_switching_to_staff_role():
    """HR-AFR-099: a reminder cannot reveal another employee's request by role switch."""
    request = HRRequest.objects.create(
        family="leave", user_id=10, state="pending_authority", route_step=0,
    )
    ApprovalRouteStep.objects.create(
        request=request, position=0, designation="Registrar", policy_version_label="test",
    )
    notice = Notification.objects.create(
        event_key="notification:reminder:role",
        recipient_user_id=200,
        request=request,
        title="HR-EIS action reminder",
        message="Review the assigned request",
    )
    general = Notification.objects.create(
        event_key="notification:policy:role",
        recipient_user_id=200,
        title="Policy notice",
        message="General configured notice",
    )

    def actor(role, permissions):
        return Principal(
            user_id=200,
            username="synthetic-reviewer",
            display_name="Reviewer",
            kind="staff",
            active_role=role,
            roles=("staff", "Registrar"),
            permissions=frozenset(permissions),
            modules=("hreis",),
        )

    staff = actor("staff", ("hreis.notification.view", "hreis.request.view"))
    registrar = actor(
        "Registrar",
        ("hreis.notification.view", "hreis.request.view", "hreis.leave.approve"),
    )
    assert list(notifications_for(staff)) == [general]
    assert set(notifications_for(registrar)) == {notice, general}
    # A matching authority may see its generic reminder without form-read rights.
    assert notifications_for(actor("Registrar", ("hreis.notification.view",))).filter(
        pk=notice.pk
    ).exists()
    assert not notifications_for(actor("Registrar", ())).exists()
