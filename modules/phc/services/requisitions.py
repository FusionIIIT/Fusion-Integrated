from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.phc.domain.requisitions import requisition_transition
from modules.phc.models import InventoryItem, InventoryRequisition, RequisitionLine
from modules.phc.services.common import audit
from modules.phc.services.notifications import enqueue


def submit_requisition(*, actor_user_id: int, lines: list[dict]):
    if not lines:
        raise ConflictError("Add at least one item and quantity before submitting.",
                            code="requisition_empty")
    with transaction.atomic():
        item_ids = sorted({line["item_id"] for line in lines})
        items = {item.pk: item for item in InventoryItem.objects.select_for_update()
                 .filter(pk__in=item_ids, is_active=True)}
        if set(items) != set(item_ids):
            raise NotFoundError("Choose active inventory items for the requisition.",
                                code="inventory_item_not_found")
        if len(item_ids) != len(lines):
            raise ConflictError("Use each inventory item once in a requisition.",
                                code="duplicate_requisition_item")
        requisition = InventoryRequisition.objects.create(
            originator_user_id=actor_user_id, state=InventoryRequisition.State.DRAFT,
            submitted_at=timezone.now())
        RequisitionLine.objects.bulk_create([
            RequisitionLine(requisition=requisition, item=items[line["item_id"]],
                            quantity=line["quantity"])
            for line in lines
        ])
        requisition.state = InventoryRequisition.State.PENDING
        requisition.save(update_fields=["state", "updated_at"])
        audit(actor_user_id=actor_user_id, action="requisition.submitted",
              object_type="inventory_requisition", object_id=requisition.pk,
              metadata={"line_count": len(lines)})
        return requisition


def transition_requisition(*, requisition_id: int, actor_user_id: int,
                           actor_role: str, event: str, scope):
    with transaction.atomic():
        requisition = scope.select_for_update().filter(pk=requisition_id).first()
        if requisition is None:
            raise NotFoundError("That requisition is not available.",
                                code="requisition_not_found")
        try:
            new_state = requisition_transition(requisition.state, event, actor_role)
        except PermissionError as exc:
            raise ConflictError(str(exc), code="actor_not_allowed") from exc
        except LookupError as exc:
            raise ConflictError(str(exc), code="invalid_transition") from exc
        previous = requisition.state
        requisition.state = new_state
        if event in ("approve", "reject"):
            requisition.decided_by_user_id = actor_user_id
        if event == "fulfill":
            requisition.fulfilled_by_user_id = actor_user_id
        requisition.save(update_fields=["state", "decided_by_user_id",
                                        "fulfilled_by_user_id", "updated_at"])
        audit(actor_user_id=actor_user_id, action=f"requisition.{event}",
              object_type="inventory_requisition", object_id=requisition.pk,
              metadata={"from": previous, "to": new_state})
        if event in ("approve", "reject"):
            enqueue(
                event_key=f"requisition:{requisition.pk}:{new_state}",
                recipient_user_id=requisition.originator_user_id,
                event_type="requisition_decision",
                payload={"target_type": "inventory_requisition",
                         "target_id": requisition.pk, "state": new_state},
            )
        return requisition
