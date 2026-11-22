"""All complaint reads go through scoped selectors."""

from django.db.models import QuerySet

from modules.complaints.models import Complaint


def own_complaints(*, user_id: int) -> QuerySet[Complaint]:
    return (
        Complaint.objects.filter(complainant_user_id=user_id)
        .prefetch_related("history", "feedback", "reopening_requests")
        .order_by("-submitted_at")
    )


def own_complaint(*, reference, user_id: int) -> Complaint | None:
    return own_complaints(user_id=user_id).filter(reference=reference).first()


def history(*, complaint: Complaint):
    return complaint.history.order_by("occurred_at", "pk")


def assigned_complaints(*, user_id: int) -> QuerySet[Complaint]:
    return (
        Complaint.objects.filter(assigned_to_user_id=user_id)
        .prefetch_related("history", "feedback", "reopening_requests")
        .order_by("sla_due_at", "submitted_at")
    )


def escalated_complaints() -> QuerySet[Complaint]:
    return (
        Complaint.objects.filter(escalations__isnull=False)
        .distinct()
        .prefetch_related("history", "feedback", "reopening_requests", "escalations")
        .order_by("sla_due_at", "submitted_at")
    )
