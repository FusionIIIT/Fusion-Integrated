"""Shared choke-point plumbing: locking a visible row and translating domain refusals."""
from __future__ import annotations

from contextlib import contextmanager

from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.iaa.domain import state_machine as sm
from modules.iaa.domain.policy import Policy
from modules.iaa.selectors import policy as policy_selectors

RECORD_NOT_FOUND = "That request or claim does not exist, or is not visible to your role."


@contextmanager
def domain_errors():
    try:
        yield
    except sm.ActorNotAllowed as exc:
        raise PermissionDeniedError(str(exc), code="actor_not_allowed") from exc
    except sm.InvalidTransition as exc:
        raise ConflictError(f"{exc} Refresh the page to see its current state.",
                            code="invalid_transition") from exc


def lock(queryset, pk: int, not_found: str = RECORD_NOT_FOUND):
    row = queryset.select_for_update().filter(pk=pk).first()
    if row is None:
        raise NotFoundError(not_found)
    return row


def current_policy() -> Policy:
    version = policy_selectors.current_version()
    if version is None:
        raise ConflictError(
            "No IAA policy has been published yet, so this cannot proceed. Ask the IAA System "
            "Admin to publish one under Configuration.", code="policy_missing")
    return policy_selectors.to_policy(version)


def now():
    return timezone.now()
