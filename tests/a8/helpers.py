"""Common test helpers for Assignment 8 test suites."""
from dataclasses import dataclass, field


@dataclass
class Actor:
    user_id: int
    active_role: str = "user"
    permissions: set[str] = field(default_factory=set)
    department: str = "CSE"

    def has_permission(self, perm: str) -> bool:
        return perm in self.permissions


def make_actor(user_id=1, role="user", perms=(), dept="CSE") -> Actor:
    return Actor(user_id=user_id, active_role=role, permissions=set(perms), department=dept)


def sysadmin_actor(user_id=101, dept="IT") -> Actor:
    return make_actor(
        user_id=user_id,
        role="sysadmin",
        perms={
            "badms.backup.trigger",
            "badms.schedule.manage_local",
            "badms.archival.classify_authoritative",
            "badms.restoration.approve_sensitive",
            "badms.records.view_all",
        },
        dept=dept,
    )


def superadmin_actor(user_id=102, dept="ADMIN") -> Actor:
    return make_actor(
        user_id=user_id,
        role="superadmin",
        perms={
            "badms.backup.trigger",
            "badms.schedule.manage_global",
            "badms.schedule.manage_local",
            "badms.archival.classify_authoritative",
            "badms.special_archival.execute",
            "badms.records.view_all",
        },
        dept=dept,
    )


def hod_actor(user_id=103, dept="CSE") -> Actor:
    return make_actor(
        user_id=user_id,
        role="hod",
        perms={"badms.department.review"},
        dept=dept,
    )


def it_security_actor(user_id=104, dept="SECURITY") -> Actor:
    return make_actor(
        user_id=user_id,
        role="security",
        perms={"badms.security.manage"},
        dept=dept,
    )


def regular_user_actor(user_id=105, dept="CSE") -> Actor:
    return make_actor(
        user_id=user_id,
        role="student",
        perms=set(),
        dept=dept,
    )
