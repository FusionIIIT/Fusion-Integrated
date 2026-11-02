
import pytest

from core.api.exceptions import PermissionDeniedError
from modules.elm.services.authz import (
    require_assigned_authority,
    require_employee_access,
    require_permission,
)


PERMISSION = "elm.leave_application.create"


class FakePrincipal:
    def __init__(self, user_id, permissions=()):
        self.user_id = user_id
        self.permissions = frozenset(permissions)

    def has_permission(self, code):
        return code in self.permissions


def test_permission_is_granted():
    actor = FakePrincipal(10, {PERMISSION})
    require_permission(actor, PERMISSION)


def test_missing_actor_is_denied():
    with pytest.raises(PermissionDeniedError):
        require_permission(None, PERMISSION)


def test_missing_permission_is_denied():
    actor = FakePrincipal(10)
    with pytest.raises(PermissionDeniedError):
        require_permission(actor, PERMISSION)


def test_employee_can_access_own_record():
    actor = FakePrincipal(10, {PERMISSION})
    require_employee_access(
        actor,
        employee_id=10,
        permission_code=PERMISSION,
    )


def test_employee_cannot_access_another_employees_record():
    actor = FakePrincipal(10, {PERMISSION})
    with pytest.raises(PermissionDeniedError):
        require_employee_access(
            actor,
            employee_id=20,
            permission_code=PERMISSION,
        )


def test_assigned_authority_is_allowed():
    actor = FakePrincipal(30, {PERMISSION})
    require_assigned_authority(
        actor,
        assigned_user_id=30,
        permission_code=PERMISSION,
    )


def test_unassigned_actor_is_denied_even_with_permission():
    actor = FakePrincipal(30, {PERMISSION})
    with pytest.raises(PermissionDeniedError):
        require_assigned_authority(
            actor,
            assigned_user_id=40,
            permission_code=PERMISSION,
        )


def test_principal_without_permission_method_is_denied():
    class InvalidPrincipal:
        user_id = 10

    with pytest.raises(PermissionDeniedError):
        require_permission(InvalidPrincipal(), PERMISSION)
