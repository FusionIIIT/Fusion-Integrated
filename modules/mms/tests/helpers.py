"""Shared helpers for the MMS suite.

Actors are built from the *real* role grants in `registry/permissions.json`, so
a test that says "as the warden" runs with exactly the permissions the warden
has in production — not with a hand-typed list that can drift from it.
"""
from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from conftest import make_principal

REGISTRY = Path(__file__).resolve().parents[3] / "registry" / "permissions.json"
MMS_REGISTRY = json.loads(REGISTRY.read_text())["modules"]["mms"]

ADMIN, CARETAKER, WARDEN, STUDENT = "mess_admin", "mess_caretaker", "mess_warden", "student"
ROLES = (ADMIN, CARETAKER, WARDEN, STUDENT)

# Fixed ids so assertions read as intent (`STUDENT_ID`) rather than magic numbers.
ADMIN_ID, CARETAKER_ID, WARDEN_ID = 9001, 9002, 9003
STUDENT_ID, OTHER_STUDENT_ID = 1001, 2002

_KIND = {ADMIN: "staff", CARETAKER: "staff", WARDEN: "staff", STUDENT: "student"}
_DEFAULT_ID = {ADMIN: ADMIN_ID, CARETAKER: CARETAKER_ID, WARDEN: WARDEN_ID, STUDENT: STUDENT_ID}

# "Today" for every time-sensitive test. A Wednesday, mid-month, so +/- a few days
# never crosses a month boundary by accident. Tests that want a boundary say so.
NOW = datetime(2026, 5, 13, 10, 0, tzinfo=UTC)
TODAY = NOW.date()


def grants(role: str) -> frozenset[str]:
    return frozenset(MMS_REGISTRY["grants"][role])


def actor(role: str, user_id: int | None = None):
    """A Principal holding exactly `role`'s MMS grants."""
    return make_principal(
        user_id=user_id or _DEFAULT_ID[role],
        permissions=grants(role),
        modules=("mms",),
        kind=_KIND[role],
        roles=(role,),
        active_role=role,
    )


def student(user_id: int = STUDENT_ID):
    return actor(STUDENT, user_id)


def caretaker():
    return actor(CARETAKER)


def warden():
    return actor(WARDEN)


def admin():
    return actor(ADMIN)


def days_from_today(n: int) -> date:
    return date.fromordinal(TODAY.toordinal() + n)
