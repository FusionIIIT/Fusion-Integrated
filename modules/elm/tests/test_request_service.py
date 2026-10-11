
from datetime import date
from types import SimpleNamespace

import pytest

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.elm.models import LeaveRequest, LeaveRequestTransition
from modules.elm.services.requests import transition

pytestmark = pytest.mark.django_db


def make_request(user_id=201, status="draft"):
    return LeaveRequest.objects.create(
        user_id=user_id,
        leave_type="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        status=status,
    )


def make_actor(user_id, *permissions):
    grants = set(permissions)
    return SimpleNamespace(
        user_id=user_id,
        kind="user",
        has_permission=lambda permission: permission in grants,
    )


def test_owner_can_submit_and_transition_is_audited():
    request = make_request()
    actor = make_actor(201, "elm.leave.apply")

    result = transition(
        request_id=request.pk,
        action="submit",
        actor=actor,
    )

    assert result.status == "submitted"
    assert result.submitted_at is not None

    event = LeaveRequestTransition.objects.get(leave_request=request)
    assert event.from_status == "draft"
    assert event.to_status == "submitted"
    assert event.actor_user_id == 201


def test_other_employee_cannot_submit_request():
    request = make_request(user_id=201)
    actor = make_actor(202, "elm.leave.apply")

    with pytest.raises(PermissionDeniedError):
        transition(request_id=request.pk, action="submit", actor=actor)

    request.refresh_from_db()
    assert request.status == "draft"
    assert not LeaveRequestTransition.objects.filter(
        leave_request=request
    ).exists()


def test_owner_without_permission_cannot_submit():
    request = make_request()
    actor = make_actor(201)

    with pytest.raises(PermissionDeniedError):
        transition(request_id=request.pk, action="submit", actor=actor)

    request.refresh_from_db()
    assert request.status == "draft"


def test_approver_cannot_approve_own_request():
    request = make_request(user_id=201, status="pending")
    actor = make_actor(201, "elm.leave.approve")

    with pytest.raises(PermissionDeniedError, match="own leave request"):
        transition(request_id=request.pk, action="approve", actor=actor)

    request.refresh_from_db()
    assert request.status == "pending"
    assert not LeaveRequestTransition.objects.filter(
        leave_request=request
    ).exists()


def test_rejection_requires_reason():
    request = make_request(user_id=201, status="pending")
    actor = make_actor(202, "elm.leave.approve")

    with pytest.raises(ConflictError, match="reason is required"):
        transition(
            request_id=request.pk,
            action="reject",
            actor=actor,
        )

    request.refresh_from_db()
    assert request.status == "pending"
    assert not LeaveRequestTransition.objects.filter(
        leave_request=request
    ).exists()


def test_approver_can_reject_with_reason_and_audit():
    request = make_request(user_id=201, status="pending")
    actor = make_actor(202, "elm.leave.approve")

    result = transition(
        request_id=request.pk,
        action="reject",
        actor=actor,
        reason="Insufficient supporting information",
    )

    assert result.status == "rejected"
    event = LeaveRequestTransition.objects.get(leave_request=request)
    assert event.from_status == "pending"
    assert event.to_status == "rejected"
    assert event.actor_user_id == 202
    assert event.reason == "Insufficient supporting information"


def test_invalid_transition_does_not_change_request():
    request = make_request(status="draft")
    actor = make_actor(202, "elm.leave.approve")

    with pytest.raises(ConflictError) as exc_info:
        transition(
            request_id=request.pk,
            action="approve",
            actor=actor,
        )

    assert exc_info.value.code == "invalid_transition"
    request.refresh_from_db()
    assert request.status == "draft"
    assert not LeaveRequestTransition.objects.filter(
        leave_request=request
    ).exists()


def test_request_outside_supplied_scope_returns_not_found():
    request = make_request(user_id=201)
    actor = make_actor(202, "elm.leave.approve")
    restricted_scope = LeaveRequest.objects.none()

    from core.api.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        transition(
            request_id=request.pk,
            action="approve",
            actor=actor,
            scope=restricted_scope,
        )

    request.refresh_from_db()
    assert request.status == "draft"
    assert not LeaveRequestTransition.objects.filter(
        leave_request=request
    ).exists()
