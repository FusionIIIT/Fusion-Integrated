from django.db import transaction

from modules.badms.models import ArchiveRequest
from modules.badms.services.audit import record


@transaction.atomic
def decide_archive(request_id, actor_id, action, *, classification=None, note=""):
    item = ArchiveRequest.objects.select_for_update().get(pk=request_id)
    if item.status != ArchiveRequest.Status.SUBMITTED:
        raise ValueError("Only submitted requests can receive a HoD decision.")
    if action not in {"approve", "reject"}:
        raise ValueError("Action must be approve or reject.")
    if action == "reject":
        item.status = ArchiveRequest.Status.HOD_REJECTED
    else:
        item.status = ArchiveRequest.Status.HOD_APPROVED
    item.decision_note = note
    item.save(update_fields=["status", "classification", "decision_note", "updated_at"])
    record(actor_id, f"archive.{action}", object_type="archive_request", object_id=item.pk,
           details={"status": item.status, "classification": item.classification})
    return item


@transaction.atomic
def classify_archive(request_id, actor_id, classification):
    item = ArchiveRequest.objects.select_for_update().get(pk=request_id)
    if item.status != ArchiveRequest.Status.HOD_APPROVED:
        raise ValueError("Only HoD-approved requests can be classified.")
    allowed = {choice for choice, _ in ArchiveRequest.Classification.choices}
    if classification not in allowed:
        raise ValueError("Choose a supported data classification.")
    item.classification = classification
    item.status = (ArchiveRequest.Status.SECURITY_REVIEW
                   if classification == ArchiveRequest.Classification.SENSITIVE
                   else ArchiveRequest.Status.CLASSIFIED)
    item.save(update_fields=["status", "classification", "updated_at"])
    record(actor_id, "archive.classified", object_type="archive_request", object_id=item.pk,
           details={"status": item.status, "classification": item.classification})
    return item


@transaction.atomic
def complete_sensitive_archive(request_id, actor_id):
    item = ArchiveRequest.objects.select_for_update().get(pk=request_id)
    if item.status != ArchiveRequest.Status.SECURITY_REVIEW:
        raise ValueError("Only Sensitive requests awaiting security review can be archived.")
    item.status = ArchiveRequest.Status.ARCHIVED
    item.save(update_fields=["status", "updated_at"])
    record(actor_id, "archive.sensitive.completed", object_type="archive_request",
           object_id=item.pk, details={"algorithm": "AES-256-GCM"})
    return item
