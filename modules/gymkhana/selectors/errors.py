"""Read failures shared by the Gymkhana selectors."""

from __future__ import annotations

from core.api.exceptions import DomainError


class DirectoryUnavailableError(DomainError):
    """The identity service did not answer, so nothing can be concluded about a person."""

    code = "directory_unavailable"
    status_code = 503
    message = "The institute directory is not available right now. Please try again shortly."
