"""Task reassignment routing service for SPACS.

Enforces:
- CFR-SPACS-018 / AFR-SPACS-052 (Role Reassignment Routing)
- BR-SPACS-022 (Role Reassignment Preserves History)
- UC-SPACS-026 (Reassign Pending Role-Based Tasks)
"""
from __future__ import annotations

import logging
from django.db import transaction
from modules.spacs.models import SpacsTask
from modules.spacs.services.audit import record_audit_event

log = logging.getLogger("fusion.spacs.routing")


def reassign_uncompleted_tasks(
    role_name: str,
    new_user_id: int,
    actor_user_id: int | None = None,
) -> int:
    """Routes uncompleted role-based tasks to the current role holder (UC-SPACS-026).

    Guarantees that past completed action actor history is never rewritten (BR-SPACS-022).
    """
    with transaction.atomic():
        pending_tasks = SpacsTask.objects.select_for_update().filter(
            assigned_role=role_name,
            status="pending",
        )
        count = pending_tasks.count()
        if count == 0:
            return 0

        task_ids = list(pending_tasks.values_list("id", flat=True))
        pending_tasks.update(assigned_user_id=new_user_id)

        record_audit_event(
            action="role.tasks_reassigned",
            entity_type="SpacsTask",
            entity_id="batch",
            actor_user_id=actor_user_id or new_user_id,
            actor_role="system",
            details={
                "role_name": role_name,
                "new_user_id": new_user_id,
                "reassigned_task_ids": task_ids,
                "task_count": count,
            },
        )

        log.info(
            "spacs.routing.reassigned role=%s new_user=%s count=%s",
            role_name, new_user_id, count
        )
        return count
