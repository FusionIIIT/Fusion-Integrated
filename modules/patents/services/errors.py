"""Turns domain rule violations into API refusals (422) without losing their specific type."""
from __future__ import annotations

from contextlib import contextmanager

from core.api.exceptions import DomainError
from modules.patents.domain import validation as val

_TRANSLATED: dict[type, type] = {}


def _translated_class(cls: type) -> type:
    if cls not in _TRANSLATED:
        _TRANSLATED[cls] = type(cls.__name__, (DomainError, cls), {})
    return _TRANSLATED[cls]


@contextmanager
def rule_errors():
    """Re-raise a domain validation error as a DomainError (HTTP 422 through the API).

    The raised object is still an instance of the original class, so callers that catch
    the specific rule error keep working.
    """
    try:
        yield
    except val.ValidationError as err:
        if isinstance(err, DomainError):
            raise
        raise _translated_class(type(err))(str(err), code="rule_violation") from err
