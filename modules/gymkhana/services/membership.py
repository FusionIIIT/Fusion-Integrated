from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from modules.gymkhana.models import Club, ClubCoordinatorAssignment, MembershipApplication


def _student_id(actor):
    user_id = getattr(actor, "user_id", None)
    if not user_id or getattr(actor, "kind", None) == "recruiter":
        raise PermissionDenied("An authenticated institute student is required.")
    if getattr(actor, "kind", None) != "student":
        raise PermissionDenied("Only students can apply for club membership.")
    return user_id


def apply(*, actor, club_id, achievements="", statement=""):
    student_id = _student_id(actor)
    try:
        club = Club.objects.get(pk=club_id, is_active=True)
    except Club.DoesNotExist:
        raise NotFound("Active club not found.")

    try:
        with transaction.atomic():
            return MembershipApplication.objects.create(
                club=club,
                student_id=student_id,
                achievements=achievements,
                statement=statement,
            )
    except IntegrityError:
        raise ValidationError({
            "club_id": "You already have an application for this club."
        })


def my_applications(*, actor):
    student_id = _student_id(actor)
    return MembershipApplication.objects.filter(
        student_id=student_id
    ).select_related("club").order_by("-created_at")


def review(*, actor, application_id, decision, remarks=""):
    reviewer_id = getattr(actor, "user_id", None)
    if not reviewer_id or getattr(actor, "kind", None) == "recruiter":
        raise PermissionDenied("An institute coordinator is required.")

    if decision not in (MembershipApplication.Status.APPROVED,
                        MembershipApplication.Status.REJECTED):
        raise ValidationError({"decision": "Use 'approved' or 'rejected'."})

    with transaction.atomic():
        try:
            application = (
                MembershipApplication.objects.select_for_update()
                .select_related("club")
                .get(pk=application_id)
            )
        except MembershipApplication.DoesNotExist:
            raise NotFound("Membership application not found.")

        assigned = ClubCoordinatorAssignment.objects.filter(
            club_id=application.club_id,
            user_id=reviewer_id,
            is_active=True,
        ).exists()
        if not assigned:
            raise PermissionDenied(
                "You are not an active coordinator for this club."
            )

        if application.status != MembershipApplication.Status.OPEN:
            raise ValidationError({
                "status": "This application has already been reviewed."
            })

        application.status = decision
        application.reviewed_by = reviewer_id
        application.reviewed_at = timezone.now()
        application.review_remarks = remarks
        application.save(update_fields=[
            "status", "reviewed_by", "reviewed_at",
            "review_remarks", "updated_at",
        ])
        return application


def bulk_review(*, actor, items):
    """Each item is independent: one invalid item does not abort the batch."""
    results = []
    for item in items:
        try:
            application = review(
                actor=actor,
                application_id=item["application_id"],
                decision=item["decision"],
                remarks=item.get("remarks", ""),
            )
            results.append({
                "application_id": application.pk,
                "status": application.status,
                "ok": True,
            })
        except Exception as exc:
            from rest_framework.exceptions import APIException
            if isinstance(exc, APIException):
                results.append({
                    "application_id": item["application_id"],
                    "ok": False,
                    "error": str(getattr(exc, "detail", exc)),
                })
            else:
                raise
    return results
