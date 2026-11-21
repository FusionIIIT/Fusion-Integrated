"""File archival service for FTS."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.fts.domain.entities import (
    validate_employee_operational_actor,
    validate_owner_archival,
)
from modules.fts.domain.errors import (
    FtsDomainError,
    OnlyOwnerMayArchiveError,
    SystemAdminOperationalActionProhibitedError,
)
from modules.fts.domain.state_machine import (
    ACTION_ARCHIVE,
    STATE_ARCHIVED,
    STATE_CIRCULATED,
    transition_state,
)
from modules.fts.models.files import File
from modules.fts.services.audit import record_audit
from modules.fts.services.notifications import trigger_notification


def _validate_archive_guards(file_obj: File, actor_user_id: int) -> str:
    """Verifies that the file is circulated and actor is the owner."""
    if file_obj.status == STATE_ARCHIVED:
        raise ConflictError(
            "This file is already archived and closed.",
            code="already_archived",
        )
    if file_obj.status != STATE_CIRCULATED:
        raise ConflictError(
            "Only completed circulated files can be archived. Circulate the file first.",
            code="cannot_archive_non_circulated",
        )
    try:
        validate_owner_archival(file_obj.owner_user_id, actor_user_id)
    except OnlyOwnerMayArchiveError as e:
        raise PermissionDeniedError(str(e), code="only_owner_may_archive") from e
    try:
        return transition_state(file_obj.status, ACTION_ARCHIVE)
    except FtsDomainError as e:
        raise ConflictError(str(e), code="invalid_state_transition") from e


def _persist_archive(
    file_obj: File,
    actor_user_id: int,
    actor_username: str,
    actor_role: str,
    target_status: str,
) -> File:
    """Updates file status to ARCHIVED and writes audit and notification events."""
    now = timezone.now()
    file_obj.status = target_status
    file_obj.archived_at = now
    file_obj.save(update_fields=["status", "archived_at", "updated_at"])
    record_audit(
        file_id=file_obj.id, action="FILE_ARCHIVED", actor_user_id=actor_user_id,
        actor_username=actor_username, actor_role=actor_role,
        details={"status": STATE_ARCHIVED, "archived_at": now.isoformat()},
    )
    trigger_notification(
        event_type="FILE_ARCHIVED", recipient_user_id=file_obj.owner_user_id,
        payload={
            "file_id": file_obj.id, "reference_number": file_obj.reference_number,
            "archived_by": actor_username,
        },
    )
    return file_obj


def archive_file(
    *,
    file_id: int,
    actor_user_id: int,
    actor_username: str,
    actor_role: str,
    actor_kind: str = "faculty",
    is_admin_actor: bool = False,
) -> File:
    """Archives a completed circulated file. Only the file owner may perform this action."""
    try:
        validate_employee_operational_actor(actor_kind, is_admin_actor)
    except SystemAdminOperationalActionProhibitedError as e:
        raise PermissionDeniedError(str(e), code="admin_operational_action_prohibited") from e

    with transaction.atomic():
        try:
            file_obj = File.objects.select_for_update().get(id=file_id)
        except File.DoesNotExist as e:
            raise NotFoundError(f"File #{file_id} was not found.") from e

        target_status = _validate_archive_guards(file_obj, actor_user_id)
        return _persist_archive(file_obj, actor_user_id, actor_username, actor_role, target_status)
