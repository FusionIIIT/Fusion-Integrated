import pytest
import datetime
import decimal
from types import SimpleNamespace
from contextlib import nullcontext
from django.http import Http404
from rest_framework.exceptions import ValidationError
import modules.leave.api.views as views
from modules.leave.models import LeaveRequest, LeaveBalance, LeaveStatus


class FakeQuerySet:
    def __init__(self, obj=None):
        self.obj = obj

    def select_for_update(self):
        return self

    def get(self, pk=None, employee_id=None):
        if self.obj is None:
            raise LeaveRequest.DoesNotExist
        return self.obj

    def filter(self, **kwargs):
        return self

    def first(self):
        return self.obj


def test_approve_workflow(monkeypatch):
    """Sanctioning authority approves pending leave; balance is deducted."""
    leave_req = SimpleNamespace(
        id=1,
        employee_id="alice",
        leave_type="CL",
        status=LeaveStatus.PENDING,
        duration=lambda: decimal.Decimal("1.0"),
        save=lambda **kw: None,
    )
    balance_obj = SimpleNamespace(
        employee_id="alice",
        leave_type="CL",
        balance=decimal.Decimal("5.0"),
        save=lambda **kw: None,
    )

    monkeypatch.setattr(views.LeaveRequest, "objects", FakeQuerySet(leave_req))
    monkeypatch.setattr(views.LeaveBalance, "objects", FakeQuerySet(balance_obj))
    monkeypatch.setattr(views, "transaction", SimpleNamespace(atomic=nullcontext))
    monkeypatch.setattr(
        views,
        "LeaveRequestSerializer",
        lambda obj: SimpleNamespace(data={"status": obj.status, "id": obj.id}),
    )

    view = views.LeaveRequestViewSet()
    view.action = "approve"
    perms = view.get_permissions()
    assert any("leave_cell.requests.sanction" in p.codes for p in perms if hasattr(p, "codes"))

    request = SimpleNamespace(
        principal=SimpleNamespace(
            username="director",
            has_permission=lambda code: code == "leave_cell.requests.sanction",
        )
    )
    res = view.approve(request, pk="1")
    assert res.status_code == 200
    assert leave_req.status == LeaveStatus.APPROVED
    assert balance_obj.balance == decimal.Decimal("4.0")


def test_approve_insufficient_balance(monkeypatch):
    """Approval fails if balance is insufficient."""
    leave_req = SimpleNamespace(
        id=2,
        employee_id="alice",
        leave_type="CL",
        status=LeaveStatus.PENDING,
        duration=lambda: decimal.Decimal("3.0"),
        save=lambda **kw: None,
    )
    balance_obj = SimpleNamespace(
        employee_id="alice",
        leave_type="CL",
        balance=decimal.Decimal("1.0"),
        save=lambda **kw: None,
    )

    monkeypatch.setattr(views.LeaveRequest, "objects", FakeQuerySet(leave_req))
    monkeypatch.setattr(views.LeaveBalance, "objects", FakeQuerySet(balance_obj))
    monkeypatch.setattr(views, "transaction", SimpleNamespace(atomic=nullcontext))

    view = views.LeaveRequestViewSet()
    request = SimpleNamespace(principal=SimpleNamespace(username="director"))
    with pytest.raises(ValidationError) as exc:
        view.approve(request, pk="2")
    assert "Insufficient balance" in str(exc.value)


def test_reject_workflow(monkeypatch):
    """Sanctioning authority rejects pending leave with reason."""
    leave_req = SimpleNamespace(
        id=3,
        employee_id="alice",
        leave_type="CL",
        status=LeaveStatus.PENDING,
        rejection_reason="",
        save=lambda **kw: None,
    )

    monkeypatch.setattr(views.LeaveRequest, "objects", FakeQuerySet(leave_req))
    monkeypatch.setattr(views, "transaction", SimpleNamespace(atomic=nullcontext))
    monkeypatch.setattr(
        views,
        "LeaveRequestSerializer",
        lambda obj: SimpleNamespace(data={"status": obj.status, "rejection_reason": obj.rejection_reason}),
    )

    view = views.LeaveRequestViewSet()
    request = SimpleNamespace(
        principal=SimpleNamespace(username="director"),
        data={"reason": "Operational necessity"},
    )
    res = view.reject(request, pk="3")
    assert res.status_code == 200
    assert leave_req.status == LeaveStatus.REJECTED
    assert leave_req.rejection_reason == "Operational necessity"


def test_cancel_approved_leave_future_date(monkeypatch):
    """Applicant cancels approved leave before start date; balance restored."""
    future_date = datetime.date.today() + datetime.timedelta(days=5)
    leave_req = SimpleNamespace(
        id=4,
        employee_id="alice",
        leave_type="EL",
        start_date=future_date,
        status=LeaveStatus.APPROVED,
        duration=lambda: decimal.Decimal("2.0"),
        save=lambda **kw: None,
    )
    balance_obj = SimpleNamespace(
        employee_id="alice",
        leave_type="EL",
        balance=decimal.Decimal("8.0"),
        save=lambda **kw: None,
    )

    monkeypatch.setattr(views.LeaveRequest, "objects", FakeQuerySet(leave_req))
    monkeypatch.setattr(views.LeaveBalance, "objects", FakeQuerySet(balance_obj))
    monkeypatch.setattr(views, "transaction", SimpleNamespace(atomic=nullcontext))
    monkeypatch.setattr(
        views,
        "LeaveRequestSerializer",
        lambda obj: SimpleNamespace(data={"status": obj.status}),
    )

    view = views.LeaveRequestViewSet()
    request = SimpleNamespace(principal=SimpleNamespace(username="alice"))
    res = view.cancel(request, pk="4")
    assert res.status_code == 200
    assert leave_req.status == LeaveStatus.CANCELLED
    assert balance_obj.balance == decimal.Decimal("10.0")


def test_cancel_approved_leave_past_date(monkeypatch):
    """Applicant cannot cancel leave that has already commenced."""
    past_date = datetime.date.today() - datetime.timedelta(days=2)
    leave_req = SimpleNamespace(
        id=5,
        employee_id="alice",
        leave_type="EL",
        start_date=past_date,
        status=LeaveStatus.APPROVED,
        duration=lambda: decimal.Decimal("2.0"),
        save=lambda **kw: None,
    )

    monkeypatch.setattr(views.LeaveRequest, "objects", FakeQuerySet(leave_req))
    monkeypatch.setattr(views, "transaction", SimpleNamespace(atomic=nullcontext))

    view = views.LeaveRequestViewSet()
    request = SimpleNamespace(principal=SimpleNamespace(username="alice"))
    with pytest.raises(ValidationError) as exc:
        view.cancel(request, pk="5")
    assert "already commenced" in str(exc.value)
