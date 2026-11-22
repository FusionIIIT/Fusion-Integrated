"""MMS-UC-001 — role assignment. BR-MMS-002..007."""
import pytest

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.mms.models import MessRoleAssignment
from modules.mms.services import operations as svc
from modules.mms.tests.helpers import (
    ADMIN_ID,
    CARETAKER,
    STUDENT,
    WARDEN,
    actor,
    admin,
    caretaker,
    days_from_today,
    student,
    warden,
)

pytestmark = pytest.mark.django_db


def _assign(role="mess_caretaker", employee=500, **kw):
    kw.setdefault("start_date", days_from_today(0))
    kw.setdefault("end_date", days_from_today(180))
    return svc.assign_mess_role(actor=admin(), role_name=role, employee_user_id=employee, **kw)


def _active(role):
    return list(MessRoleAssignment.objects.filter(role_name=role, is_active=True))


def test_admin_assigns_a_caretaker():
    a = _assign()
    assert (a.role_name, a.assigned_user_id, a.is_active) == ("mess_caretaker", 500, True)
    assert a.assigned_by_user_id == ADMIN_ID


def test_assignment_notifies_the_employee(sent):
    _assign(employee=500)
    [n] = sent("role_assigned")
    assert n.recipient_user_id == 500


def test_br003_reassigning_the_caretaker_deactivates_the_previous_one():
    first = _assign(employee=500)
    second = _assign(employee=501)
    first.refresh_from_db()
    assert first.is_active is False
    assert _active("mess_caretaker") == [second]


def test_br004_reassigning_the_warden_deactivates_the_previous_one():
    first = _assign("mess_warden", 600)
    second = _assign("mess_warden", 601)
    first.refresh_from_db()
    assert first.is_active is False
    assert _active("mess_warden") == [second]


def test_roles_are_independent_of_each_other():
    """Replacing the warden must not touch the caretaker (exactly one of EACH)."""
    c = _assign("mess_caretaker", 500)
    _assign("mess_warden", 600)
    _assign("mess_warden", 601)
    c.refresh_from_db()
    assert c.is_active is True


def test_history_is_kept_when_a_role_is_reassigned():
    for employee in (500, 501, 502):
        _assign(employee=employee)
    assert MessRoleAssignment.objects.filter(role_name="mess_caretaker").count() == 3
    assert len(_active("mess_caretaker")) == 1


@pytest.mark.parametrize("sequence", [[500], [500, 501], [500, 501, 500, 502, 503]])
def test_exactly_one_active_of_each_role_after_any_sequence(sequence):
    for employee in sequence:
        _assign("mess_caretaker", employee)
        _assign("mess_warden", employee + 1000)
    assert len(_active("mess_caretaker")) == 1
    assert len(_active("mess_warden")) == 1


def test_the_same_employee_may_be_re_assigned_the_same_role():
    _assign(employee=500)
    again = _assign(employee=500)
    assert _active("mess_caretaker") == [again]


@pytest.mark.parametrize("bad_role", ["student", "mess_admin", "", "MESS_CARETAKER", "warden"])
def test_only_caretaker_and_warden_can_be_assigned(bad_role):
    with pytest.raises(BadRequestError):
        _assign(bad_role)
    assert MessRoleAssignment.objects.count() == 0


def test_end_before_start_is_refused_and_nothing_changes():
    existing = _assign(employee=500)
    with pytest.raises(BadRequestError):
        _assign(employee=501, start_date=days_from_today(10), end_date=days_from_today(5))
    existing.refresh_from_db()
    assert existing.is_active is True            # the refusal must not deactivate the incumbent
    assert MessRoleAssignment.objects.count() == 1


def test_a_one_day_assignment_is_allowed():
    a = _assign(start_date=days_from_today(0), end_date=days_from_today(0))
    assert a.start_date == a.end_date


@pytest.mark.parametrize("who", [caretaker(), warden(), student()],
                         ids=[CARETAKER, WARDEN, STUDENT])
def test_only_the_mess_admin_can_assign_roles(who):
    with pytest.raises(PermissionDeniedError):
        svc.assign_mess_role(actor=who, role_name="mess_caretaker", employee_user_id=1,
                             start_date=days_from_today(0), end_date=days_from_today(1))
    assert MessRoleAssignment.objects.count() == 0


def test_a_refused_assignment_sends_no_notification(sent):
    with pytest.raises(PermissionDeniedError):
        svc.assign_mess_role(actor=actor("student"), role_name="mess_caretaker",
                             employee_user_id=1, start_date=days_from_today(0),
                             end_date=days_from_today(1))
    assert sent() == []
