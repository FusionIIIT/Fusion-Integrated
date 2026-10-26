import pytest
from types import SimpleNamespace
from contextlib import nullcontext
from django.http import Http404
from rest_framework.exceptions import ValidationError
import modules.leave.api.views as views
from modules.leave.models import LeaveRequest

class FakeManager:
    def __init__(self, obj=None, exc=None):
        self.obj = obj
        self.exc = exc
    def select_for_update(self):
        return self
    def get(self, pk=None, employee_id=None):
        assert employee_id == "alice"
        if self.exc:
            raise self.exc
        return self.obj

# Test 1: permission codes for withdraw action

def test_withdraw_permission_codes():
    view = views.LeaveRequestViewSet()
    view.action = "withdraw"
    perms = view.get_permissions()
    assert len(perms) == 2
    # The second permission should be HasPermission with the correct code
    assert perms[1].codes == ("leave_cell.requests.manage",)

# Test 2: successful withdrawal

def test_withdraw_success(monkeypatch):
    # Prepare a pending leave request
    pending = SimpleNamespace(status="pending", updated_at=None)
    def save(update_fields=None):
        pending.update_fields = update_fields
    pending.save = save

    manager = FakeManager(obj=pending)
    monkeypatch.setattr(views.LeaveRequest, "objects", manager)
    monkeypatch.setattr(views, "transaction", SimpleNamespace(atomic=nullcontext))
    monkeypatch.setattr(views, "LeaveRequestSerializer", lambda obj: SimpleNamespace(data={"status": obj.status}))

    view = views.LeaveRequestViewSet()
    request = SimpleNamespace(principal=SimpleNamespace(username="alice"))
    response = view.withdraw(request, pk="1")

    assert response.status_code == 200
    assert response.data["status"] == "withdrawn"
    assert pending.update_fields == ["status", "updated_at"]

# Test 3: invalid status and not found

def test_withdraw_invalid_and_not_found(monkeypatch):
    # Approved status should raise ValidationError
    approved = SimpleNamespace(status="approved", updated_at=None)
    def save(update_fields=None):
        approved.update_fields = update_fields
    approved.save = save
    manager = FakeManager(obj=approved)
    monkeypatch.setattr(views.LeaveRequest, "objects", manager)
    monkeypatch.setattr(views, "transaction", SimpleNamespace(atomic=nullcontext))
    monkeypatch.setattr(views, "LeaveRequestSerializer", lambda obj: SimpleNamespace(data={"status": obj.status}))

    view = views.LeaveRequestViewSet()
    request = SimpleNamespace(principal=SimpleNamespace(username="alice"))
    with pytest.raises(ValidationError):
        view.withdraw(request, pk="1")

    # Now test DoesNotExist leading to Http404
    manager_not_found = FakeManager(exc=LeaveRequest.DoesNotExist)
    monkeypatch.setattr(views.LeaveRequest, "objects", manager_not_found)
    with pytest.raises(Http404):
        view.withdraw(request, pk="2")
