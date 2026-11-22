"""Builder actors fail immediately when their permission codes drift from the registry."""

from conftest import make_session as platform_session
from fusion_auth.principal import Principal as PlatformPrincipal
from modules.hreis.registry import PERMISSIONS

DECLARED = frozenset(code for code, _ in PERMISSIONS)


def _check(codes):
    assert set(codes) <= DECLARED, f"Undeclared HR-EIS test permissions: {set(codes) - DECLARED}"


class Principal(PlatformPrincipal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _check(self.permissions)


def make_session(**kwargs):
    kwargs.setdefault("permissions", ())
    session = platform_session(**kwargs)
    _check(session.permissions)
    return session


def make_principal(**kwargs):
    return Principal.from_session(make_session(**kwargs))
