"""VMS-specific domain errors.

Every one of these is rendered by core.api.exceptions into the platform's
single error envelope; services stay callable from tasks and commands.
"""
from __future__ import annotations

from rest_framework import status

from core.api.exceptions import ConflictError, DomainError


class VmsError(DomainError):
    code = "vms_error"
    message = "The visitor request could not be processed."


class BlacklistBlockedError(VmsError):
    """VMS-BR-004 / VMS-BR-024: an active registry match blocks registration."""

    code = "blacklist_blocked"
    status_code = status.HTTP_403_FORBIDDEN
    message = "This visitor matches an active blacklist entry."


class DuplicatePassError(ConflictError):
    """VMS-BR-020: one pass per visitor per day."""

    code = "duplicate_pass"
    message = "This visitor already has a pass today."


class DuplicateVisitError(ConflictError):
    """VMS-BR-017: a same-day visit already exists."""

    code = "duplicate_visit"
    message = "This visitor already has a visit today."


class MachineNotNominalError(VmsError):
    """VMS-BR-029: guest operations must use the nominal machine id."""

    code = "machine_not_nominal"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "This machine id is not valid for guest operations."


class SecurityMisconfiguredError(VmsError):
    """VMS-BR-025: no active, in-scope security assignment."""

    code = "security_misconfigured"
    status_code = status.HTTP_403_FORBIDDEN
    message = "The recording security personnel assignment is not valid."


class HostDisabledError(VmsError):
    """VMS-BR-026: a disabled host's check-in is not valid."""

    code = "host_disabled"
    status_code = status.HTTP_403_FORBIDDEN
    message = "The host for this visit is disabled."


class ZoneAccessDeniedError(VmsError):
    """VMS-BR-041 / VMS-BR-042: zone not on the pass and no elevation."""

    code = "zone_access_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "This pass does not permit that zone."


class PassStateError(ConflictError):
    """The pass is not in a state that allows the operation."""

    code = "pass_state"
    message = "The pass is not in a state that allows this."


class MusterStateError(ConflictError):
    code = "muster_state"
    message = "The muster is not in a state that allows this."
