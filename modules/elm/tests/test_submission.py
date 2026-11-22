from datetime import date
from decimal import Decimal

import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from conftest import make_principal
from modules.directory.models import UserRef
from modules.elm.decisions import decide
from modules.elm.models import AuthorityRoute, LeaveBalance, LeaveEvent, LeaveRequest, LeaveType
from modules.elm.workflows import submit, substitute_response, withdraw


def seed():
    UserRef.objects.create(user_id=101, username="u101", kind="staff", department="CSE")
    UserRef.objects.create(user_id=201, username="u201", kind="staff", department="CSE")
    UserRef.objects.create(user_id=301, username="u301", kind="faculty", department="CSE")
    leave_type = LeaveType.objects.create(type="CL")
    AuthorityRoute.objects.create(
        employee=101, leave_category="", unit_head=201, higher_authorities=[201]
    )
    principal = make_principal(
        user_id=101,
        kind="staff",
        modules=("elm",),
        permissions=("elm.leave_requests.apply", "elm.leave_requests.view"),
    )
    return (leave_type, principal)


def test_submit_sets_owner_and_pending_route():
    leave_type, principal = seed()
    data = {
        "leave_type": leave_type,
        "start_date": date(2026, 11, 2),
        "end_date": date(2026, 11, 2),
        "purpose": "Family work",
        "employee": 999,
        "status": "APPROVED",
        "route": [999],
    }
    req = submit(data, principal)
    assert req.employee == 101
    assert req.status == "PENDING"
    assert req.route == [201]
    assert req.days == Decimal("1")
    assert LeaveBalance.objects.get(
        employee=101, leave_type=leave_type, year=2026
    ).balance == Decimal("8")
    assert LeaveEvent.objects.filter(
        request=req, action="TASK_ASSIGNED", details__recipient=201
    ).exists()


def test_optional_nominee_cannot_be_self():
    leave_type, principal = seed()
    data = {
        "leave_type": leave_type,
        "start_date": date(2026, 11, 2),
        "end_date": date(2026, 11, 2),
        "purpose": "Family",
        "substitute": 101,
    }
    with pytest.raises(ValidationError):
        submit(data, principal)
    assert LeaveRequest.objects.count() == 0


pytestmark = pytest.mark.django_db


def test_assigned_approval_debits_once():
    req, _applicant, authority, leave_type = pending_context()
    decide(req.pk, authority, "APPROVE")
    req.refresh_from_db()
    assert req.status == "APPROVED"
    assert LeaveBalance.objects.get(
        employee=101, leave_type=leave_type, year=2026
    ).balance == Decimal("7")


def test_unassigned_authority_cannot_approve():
    req, applicant, _authority, leave_type = pending_context()
    with pytest.raises(PermissionDenied):
        decide(req.pk, applicant, "APPROVE")
    req.refresh_from_db()
    assert req.status == "PENDING"
    assert LeaveBalance.objects.get(
        employee=101, leave_type=leave_type, year=2026
    ).balance == Decimal("8")


def test_withdraw_terminates_pending_approval():
    req, applicant, authority, leave_type = pending_context()
    withdraw(req.pk, applicant)
    req.refresh_from_db()
    assert req.status == "WITHDRAWN"
    with pytest.raises(ValidationError):
        decide(req.pk, authority, "APPROVE")
    assert LeaveBalance.objects.get(
        employee=101, leave_type=leave_type, year=2026
    ).balance == Decimal("8")


def test_nominee_consent_is_not_automatic():
    req, _applicant, authority, leave_type = pending_context(substitute=301)
    assert req.substitute_status == "PENDING"
    with pytest.raises(ValidationError):
        decide(req.pk, authority, "APPROVE")
    assert LeaveBalance.objects.get(
        employee=101, leave_type=leave_type, year=2026
    ).balance == Decimal("8")


def pending_context(substitute=None):
    leave_type, applicant = seed()
    data = {
        "leave_type": leave_type,
        "start_date": date(2026, 11, 2),
        "end_date": date(2026, 11, 2),
        "purpose": "Family",
    }
    if substitute:
        data["substitute"] = substitute
    req = submit(data, applicant)
    authority = make_principal(
        user_id=201, kind="staff", modules=("elm",), permissions=("elm.leave_requests.approve",)
    )
    return (req, applicant, authority, leave_type)


def test_accepted_substitute_allows_approval():
    req, _applicant, authority, leave_type = pending_context(substitute=301)
    nominee = make_principal(
        user_id=301, kind="faculty", modules=("elm",), permissions=("elm.leave_requests.view",)
    )
    substitute_response(req.pk, nominee, True)
    decide(req.pk, authority, "APPROVE")
    req.refresh_from_db()
    assert req.status == "APPROVED"
    assert LeaveBalance.objects.filter(employee=101, leave_type=leave_type, year=2026).exists()
    balance = LeaveBalance.objects.get(employee=101, leave_type=leave_type, year=2026)
    assert balance.balance == Decimal("7")


def test_approval_cannot_debit_twice():
    req, _applicant, authority, leave_type = pending_context()
    decide(req.pk, authority, "APPROVE")
    with pytest.raises(ValidationError):
        decide(req.pk, authority, "APPROVE")
    assert LeaveBalance.objects.get(
        employee=101, leave_type=leave_type, year=2026
    ).balance == Decimal("7")


def test_approval_permission_does_not_grant_unassigned_requests():
    req, _applicant, _authority, leave_type = pending_context()
    other = make_principal(
        user_id=301, kind="faculty", modules=("elm",), permissions=("elm.leave_requests.approve",)
    )
    with pytest.raises(PermissionDenied):
        decide(req.pk, other, "APPROVE")
    assert LeaveBalance.objects.get(employee=101, leave_type=leave_type, year=2026).balance == 8


def test_withdraw_with_nominee_notifies_all_without_debit():
    req, applicant, _authority, leave_type = pending_context(substitute=301)
    withdraw(req.pk, applicant)
    req.refresh_from_db()
    assert req.status == "WITHDRAWN"
    withdrawn_event = req.events.get(action="WITHDRAWN")
    assert withdrawn_event.details["recipients"] == [101, 201, 301]
    leave_balance = LeaveBalance.objects.get(employee=101, leave_type=leave_type, year=2026)
    assert leave_balance.balance == Decimal("8")
