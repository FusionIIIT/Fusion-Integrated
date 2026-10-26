from types import SimpleNamespace

import pytest

from modules.leave.api.views.leave import LeaveRequestViewSet, YearEndProcessingViewSet


class PrincipalStub:
    def __init__(self, permissions=()):
        self.permissions = frozenset(permissions)

    def has_module(self, code):
        return code == "leave_management"

    def has_permission(self, code):
        return code in self.permissions

    def has_any_permission(self, *codes):
        return any(code in self.permissions for code in codes)


@pytest.mark.parametrize(
    ("view_class", "action", "permission"),
    [
        (LeaveRequestViewSet, "create", "leave_management.leave_request.create"),
        (LeaveRequestViewSet, "withdraw", "leave_management.leave_request.withdraw_pending"),
        (YearEndProcessingViewSet, "run", "leave_management.year_end.process"),
    ],
)
def test_leave_actions_require_their_declared_permission(view_class, action, permission):
    view = view_class()
    view.action = action

    granted_request = SimpleNamespace(principal=PrincipalStub({permission}))
    denied_request = SimpleNamespace(principal=PrincipalStub())

    assert all(check.has_permission(granted_request, view) for check in view.get_permissions())
    assert not all(check.has_permission(denied_request, view) for check in view.get_permissions())


def test_undeclared_leave_actions_are_denied():
    view = LeaveRequestViewSet()
    view.action = "unmapped"
    request = SimpleNamespace(principal=PrincipalStub({"leave_management.leave_request.create"}))

    assert not any(check.has_permission(request, view) for check in view.get_permissions())
