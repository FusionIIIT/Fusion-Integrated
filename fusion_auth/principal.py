"""The authenticated actor.

Called `principal`, not `user`, deliberately: there is no Django user behind
it. It is a value object built from what IAM said, and it is what every
permission check reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from fusion_auth.client import IamSession


@dataclass(frozen=True)
class Principal:
    user_id: int
    username: str
    display_name: str
    kind: str
    active_role: str | None
    roles: tuple[str, ...]
    permissions: frozenset[str]
    modules: tuple[str, ...]
    email: str = ""

    # DRF pokes at these on request.user
    is_authenticated: bool = True
    is_anonymous: bool = False

    @classmethod
    def from_session(cls, s: IamSession) -> Principal:
        return cls(
            user_id=s.user_id, username=s.username, display_name=s.display_name,
            kind=s.kind, active_role=s.active_role, roles=s.roles,
            permissions=s.permissions, modules=s.modules, email=s.email,
        )

    def has_permission(self, code: str) -> bool:
        return code in self.permissions

    def has_any_permission(self, *codes: str) -> bool:
        return any(c in self.permissions for c in codes)

    def has_module(self, code: str) -> bool:
        return code in self.modules

    def __str__(self) -> str:
        return f"{self.username}({self.user_id})"
