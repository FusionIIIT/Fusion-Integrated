from django.db import transaction
from django.utils import timezone

from .models import VisitRequest, VisitorPass, VisitLog


@transaction.atomic
def approve_visit(visit, user, note=""):
    if visit.status != VisitRequest.Status.PENDING:
        raise ValueError("Only pending visits can be approved.")

    now = timezone.now()

    visit.status = VisitRequest.Status.APPROVED
    visit.decision_at = now
    visit.decision_by = user
    visit.decision_note = note
    visit.save()

    VisitorPass.objects.create(
        visit_request=visit,
        pass_type=visit.visit_type,
        valid_from=visit.scheduled_start,
        valid_until=visit.scheduled_end,
        issued_by=user,
    )

    return visit


@transaction.atomic
def reject_visit(visit, user, note=""):
    if visit.status != VisitRequest.Status.PENDING:
        raise ValueError("Only pending visits can be rejected.")

    visit.status = VisitRequest.Status.REJECTED
    visit.decision_at = timezone.now()
    visit.decision_by = user
    visit.decision_note = note
    visit.save()

    return visit


@transaction.atomic
def check_in_visit(visit, user, checkpoint=""):
    now = timezone.now()

    if visit.status != VisitRequest.Status.APPROVED:
        raise ValueError("Visit is not approved.")

    visitor_pass = VisitorPass.objects.get(visit_request=visit)

    if not visitor_pass.is_active:
        raise ValueError("Visitor pass is inactive.")

    if now < visitor_pass.valid_from or now > visitor_pass.valid_until:
        raise ValueError("Visitor pass is outside its validity period.")

    visitor_pass.is_active = False
    visitor_pass.save()

    visit.status = VisitRequest.Status.ON_SITE
    visit.save()

    VisitLog.objects.create(
        visit_request=visit,
        event_type=VisitLog.EventType.CHECK_IN,
        performed_by=user,
        checkpoint=checkpoint,
    )

    return visit


@transaction.atomic
def check_out_visit(visit, user, checkpoint=""):
    if visit.status != VisitRequest.Status.ON_SITE:
        raise ValueError("Only on-site visits can be checked out.")

    visit.status = VisitRequest.Status.COMPLETED
    visit.save()

    VisitLog.objects.create(
        visit_request=visit,
        event_type=VisitLog.EventType.CHECK_OUT,
        performed_by=user,
        checkpoint=checkpoint,
    )

    return visit