"""Principals and permission sets the elm tests share.

A plain module rather than conftest: fixtures live in conftest.py, and tests
import these constants directly so a typo is a NameError, not a passing test.
"""
from conftest import make_session
from fusion_auth.principal import Principal

EMPLOYEE_PERMS = ("elm.application.create", "elm.application.view",
                  "elm.application.delete", "elm.balance.view")
APPROVER_PERMS = ("elm.application.view", "elm.application.approve",
                  "elm.balance.view")
ADMIN_PERMS = (*APPROVER_PERMS, "elm.balance.manage", "elm.policy.manage")


def principal(*, user_id: int, permissions=EMPLOYEE_PERMS, kind="staff",
              roles=("Employee",), active_role="Employee", modules=("elm",),
              **kw) -> Principal:
    return Principal.from_session(make_session(
        user_id=user_id, kind=kind, roles=roles, active_role=active_role,
        permissions=permissions, modules=modules, **kw))
