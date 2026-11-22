"""Reject unknown filters rather than silently returning a different scope."""

from core.api.exceptions import DomainError


class UnknownQueryParameter(DomainError):
    code = "unknown_query_parameter"


def reject_unknown_query_params(request, *, allowed=("cursor",)) -> None:
    unknown = sorted(set(request.query_params) - set(allowed))
    if unknown:
        raise UnknownQueryParameter(f"Unsupported query parameter(s): {', '.join(unknown)}.")
