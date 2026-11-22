"""Read-only audit review (VMS-UC-004, CFR-005).

Deliberately has no function that changes or removes an AuditLog row.
"""
from __future__ import annotations

from modules.vms.selectors import admin as selectors
from modules.vms.services.common import authz

PERM = "vms.audit.view"
#: Ids and codes only. `detail` is excluded from the export so it carries no
#: personal data.
EXPORT_HEADER = ["id", "created_at", "actor_user_id", "actor_role", "action",
                 "entity_type", "entity_id"]
EXPORT_LIMIT = 50_000


def search(*, actor, **filters):
    authz.require(actor, PERM)
    return selectors.audit_rows(**filters)


def export_rows(*, actor, **filters):
    """Rows for `core.api.csv.stream`, oldest first, capped at EXPORT_LIMIT."""
    # Authorise eagerly: a generator would raise only after the response began.
    qs = search(actor=actor, **filters).order_by("id")[:EXPORT_LIMIT]
    return ([r.pk, r.created_at.isoformat(), r.actor_user_id, r.actor_role,
             r.action, r.entity_type, r.entity_id] for r in qs.iterator())
