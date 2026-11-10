"""Role-Based Access Control (RBAC) helpers for PCMS.

Provides a ``requires_role`` decorator that checks whether the current
user's role is in the set of allowed roles before executing a service
function.  For the demo, a simple in-memory user store and a thread-local
"current user" variable are used in place of real authentication.
"""

from __future__ import annotations

import functools
import threading
from typing import Optional

from .models import Role

# ---------------------------------------------------------------------------
# Thread-local storage for the "current user" (demo only)
# ---------------------------------------------------------------------------
_current = threading.local()


class User:
    """Minimal user representation."""

    def __init__(self, user_id: str, role: Role):
        self.user_id = user_id
        self.role = role

    def __repr__(self) -> str:
        return f"User(user_id={self.user_id!r}, role={self.role!r})"


# In-memory user store (demo purposes)
_users = {
    "admin": User("admin", Role.TPO),
    "student1": User("student1", Role.STUDENT),
    "company1": User("company1", Role.COMPANY),
    "chairman1": User("chairman1", Role.CHAIRMAN),
    "alumni1": User("alumni1", Role.ALUMNI),
}


def set_current_user(user_id: str) -> None:
    """Set the current user for the current thread (demo helper)."""
    if user_id not in _users:
        _users[user_id] = User(user_id, Role.TPO)  # default to TPO for demo
    _current.user = _users[user_id]


def get_current_user() -> User:
    """Return the current user, defaulting to admin/TPO if not set."""
    user = getattr(_current, "user", None)
    if user is None:
        set_current_user("admin")
        return _current.user
    return user


def requires_role(*allowed_roles: Role):
    """Decorator that restricts a function to users with specific roles.

    Usage::

        @requires_role(Role.TPO, Role.COMPANY)
        def create_job_posting(...):
            ...

    If the current user's role is not in *allowed_roles*, a
    ``PermissionError`` is raised.
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user.role not in allowed_roles:
                raise PermissionError(
                    f"User {user.user_id!r} with role {user.role.value!r} "
                    f"is not authorised to call {fn.__name__}. "
                    f"Allowed roles: {[r.value for r in allowed_roles]}"
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator
