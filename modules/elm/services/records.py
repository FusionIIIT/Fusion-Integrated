"""Authorized maintenance of existing leave records without sanctioning decisions."""
from django.db import transaction
from modules.elm.domain.policy import PolicyViolation
from modules.elm.models import LeaveTransition, OfflineLeaveRecord

@transaction.atomic
def maintain_offline_record(*, record_id: int, actor_user_id: int, actor_role: str = "",
                           sanction_reference: str | None = None, evidence: list | None = None,
                           note: str | None = None) -> OfflineLeaveRecord:
    row = OfflineLeaveRecord.objects.select_for_update().select_related("synced_request").filter(pk=record_id).first()
    if not row:
        raise OfflineLeaveRecord.DoesNotExist
    if not row.synced_request_id:
        raise PolicyViolation("record_not_synchronized", "Only records synchronized to a leave-history entry can be maintained.")
    changed = {}
    if sanction_reference is not None:
        if not sanction_reference.strip():
            raise PolicyViolation("sanction_reference_required", "Sanction reference cannot be blank.")
        row.sanction_reference = sanction_reference.strip(); changed["sanction_reference"] = row.sanction_reference
    if evidence is not None:
        if not evidence:
            raise PolicyViolation("evidence_required", "Evidence cannot be cleared through record maintenance.")
        row.evidence = evidence; changed["evidence"] = evidence
    if note is not None:
        row.note = note; changed["note"] = note
    if not changed:
        raise PolicyViolation("no_changes", "Provide at least one permitted record-maintenance field.")
    row.save()
    LeaveTransition.objects.create(request=row.synced_request, from_status=row.synced_request.status,
        to_status=row.synced_request.status, event="offline_record_maintained", actor_user_id=actor_user_id,
        actor_role=actor_role or "Leave Administrator", note=note or "Authorized offline record maintenance", data=changed)
    return row
