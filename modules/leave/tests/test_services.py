"""Leave service tests — uses the database."""
import datetime

import pytest

from modules.hr.contracts import EmploymentDTO
from modules.leave.models import LeaveBalance, LeaveRequest, LeaveType
from modules.leave.services import leave as services


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_hr_contracts(monkeypatch):
    """Mock HR contracts so leave tests do not touch hr.models directly."""
    def fake_get_employments(user_ids):
        res = {}
        for uid in user_ids:
            if uid == 9999:
                res[uid] = EmploymentDTO(
                    user_id=uid, is_employed=False, department_id=None,
                    department_name="", title="", kind="",
                )
            else:
                res[uid] = EmploymentDTO(
                    user_id=uid, is_employed=True, department_id=1,
                    department_name="CSE", title="Staff", kind="permanent",
                )
        return res

    monkeypatch.setattr("modules.hr.contracts.get_employments", fake_get_employments)


@pytest.fixture
def leave_type(db):
    return LeaveType.objects.create(
        code="CL", name="Casual Leave", annual_quota=12,
        allow_half_day=True,
    )


@pytest.fixture
def employed_user(db):
    """User 1001 has active employment."""
    return 1001


@pytest.fixture
def with_balance(leave_type, employed_user, db):
    return LeaveBalance.objects.create(
        user_id=employed_user, leave_type=leave_type,
        year=2026, credited=10, used=0,
    )


def _make_principal(user_id, permissions=()):
    class FakePrincipal:
        def __init__(self):
            self.user_id = user_id
            self._perms = set(permissions)

        def has_permission(self, perm):
            return perm in self._perms

    return FakePrincipal()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_apply_for_leave_creates_pending_request(leave_type, with_balance):
    actor = _make_principal(1001)
    req = services.apply_for_leave(
        actor=actor,
        leave_type_id=leave_type.pk,
        start_date=datetime.date(2026, 3, 1),
        end_date=datetime.date(2026, 3, 3),
    )
    assert req.status == "pending"
    assert float(req.days_requested) == 3.0


@pytest.mark.django_db
def test_apply_fails_for_unemployed_user(leave_type, db):
    actor = _make_principal(9999)
    from core.api.exceptions import ConflictError
    with pytest.raises(ConflictError, match="Only employed"):
        services.apply_for_leave(
            actor=actor,
            leave_type_id=leave_type.pk,
            start_date=datetime.date(2026, 3, 1),
            end_date=datetime.date(2026, 3, 3),
        )


@pytest.mark.django_db
def test_approve_deducts_balance(leave_type, with_balance):
    actor_req = _make_principal(1001)
    req = services.apply_for_leave(
        actor=actor_req, leave_type_id=leave_type.pk,
        start_date=datetime.date(2026, 3, 1),
        end_date=datetime.date(2026, 3, 2),  # 2 days
    )
    approver = _make_principal(9001, permissions={"leave.request.approve"})
    services.transition(request_id=req.pk, to_status="approved", actor=approver)

    balance = LeaveBalance.objects.get(
        user_id=1001, leave_type=leave_type, year=2026)
    assert float(balance.used) == 2.0


@pytest.mark.django_db
def test_cancel_approved_restores_balance(leave_type, with_balance):
    actor_req = _make_principal(1001)
    req = services.apply_for_leave(
        actor=actor_req, leave_type_id=leave_type.pk,
        start_date=datetime.date(2026, 4, 1),
        end_date=datetime.date(2026, 4, 2),  # 2 days
    )
    approver = _make_principal(9001, permissions={"leave.request.approve"})
    services.transition(request_id=req.pk, to_status="approved", actor=approver)

    services.transition(request_id=req.pk, to_status="cancelled", actor=actor_req)

    balance = LeaveBalance.objects.get(
        user_id=1001, leave_type=leave_type, year=2026)
    assert float(balance.used) == 0.0
