from core.api.exceptions import ConflictError, NotFoundError
from modules.phc.models import PHCAuditEvent


def audit(*, actor_user_id: int, action: str, object_type: str,
          object_id: int, metadata: dict | None = None) -> PHCAuditEvent:
    return PHCAuditEvent.objects.create(
        actor_user_id=actor_user_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        metadata=metadata or {},
    )


def get_locked(queryset, object_id: int, message: str):
    obj = queryset.select_for_update().filter(pk=object_id).first()
    if obj is None:
        raise NotFoundError(message, code="not_found")
    return obj


def conflict(message: str, code: str):
    raise ConflictError(message, code=code)
