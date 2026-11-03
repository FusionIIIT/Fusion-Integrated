"""Transactional PMS use-case operations and the policy checks they share."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.pms.models import (
    Application,
    ApplicationDocument,
    ApplicationTransition,
    AttorneyAssignment,
    AttorneyProfile,
    BudgetProposal,
    Deadline,
    DirectorProfile,
    PatentAppeal,
    PatentFiling,
    PmsAuditEvent,
    PmsConfiguration,
    PmsNotification,
)


def _fail(message):
    raise ValidationError({"detail": message})


def _config(key, default=None):
    row = PmsConfiguration.objects.filter(key=key).first()
    return row.value if row else default


def _audit(app, actor_id, action, old="", new="", metadata=None):
    PmsAuditEvent.objects.create(
        actor_user_id=actor_id,
        application=app,
        action=action,
        previous_state=old,
        new_state=new,
        metadata=metadata or {},
    )


def _notify(app, user_id, event, subject, body):
    if user_id is None:
        return
    key = f"{app.pk}:{event}:{user_id}:{app.transitions.count()}"
    PmsNotification.objects.get_or_create(
        dedupe_key=key,
        defaults={
            "recipient_user_id": user_id,
            "application": app,
            "event": event,
            "subject": subject,
            "body": body,
        },
    )


def _transition(app, actor_id, action, to_status=None, justification="", metadata=None):
    old = app.status
    if to_status:
        app.status = to_status
        app.save(update_fields=["status", "updated_at"])
    ApplicationTransition.objects.create(
        application=app,
        from_status=old,
        to_status=app.status,
        actor_user_id=actor_id,
        action=action,
        justification=justification,
    )
    _audit(app, actor_id, action, old, app.status, metadata)
    return old


def _applicant(app, user_id):
    if app.applicant_user_id != user_id:
        raise PermissionDenied("You may only change your own application.")


def _business_days_after(start, days):
    holidays = set(_config("business_holidays", []))
    result = start
    count = 0
    while count < days:
        result += timedelta(days=1)
        if result.weekday() < 5 and result.isoformat() not in holidays:
            count += 1
    return result


def _complete_document_set(app):
    docs = app.documents.all()
    if not docs.exists():
        _fail("Upload the required supporting documents before submission.")
    if docs.filter(malware_scan_status="infected").exists():
        _fail("An infected document must be removed before submission.")
    if docs.exclude(malware_scan_status="clean").exists():
        _fail("Supporting documents must pass malware scanning before submission.")


def submit_application(app_id, actor_id):
    with transaction.atomic():
        app = Application.objects.select_for_update().get(pk=app_id)
        _applicant(app, actor_id)
        if app.status not in (Application.Status.DRAFT,):
            _fail("Only a draft application can be submitted.")
        if not all(
            [
                app.title.strip(),
                app.abstract.strip(),
                app.detailed_description.strip(),
                app.claims.strip(),
                app.technical_domain.strip(),
            ]
        ):
            _fail(
                "Title, abstract, detailed description, claims, and technical domain are required."
            )
        agreements = list(app.inventor_agreements.select_related("inventor"))
        if not agreements:
            _fail("Add at least one inventor before submitting.")
        if any(not a.inventor.full_name.strip() for a in agreements):
            _fail("Inventor information must be complete.")
        if sum((a.ownership_percent for a in agreements), Decimal("0")) != Decimal("100.00"):
            _fail("Inventor ownership percentages must total 100.")
        _complete_document_set(app)
        app.submitted_at = timezone.now()
        app.save(update_fields=["submitted_at", "updated_at"])
        _transition(app, actor_id, "application_submitted", Application.Status.SUBMITTED)
        _notify(
            app,
            app.applicant_user_id,
            "application.submitted",
            "Patent application submitted",
            f"{app.application_number} was submitted.",
        )
        return app


def assign_director(app_id, director_user_id, actor_id):
    with transaction.atomic():
        app = Application.objects.select_for_update().get(pk=app_id)
        if app.status not in (Application.Status.SUBMITTED, Application.Status.RESUBMITTED):
            _fail("Only submitted or resubmitted applications can be assigned for review.")
        director = DirectorProfile.objects.filter(user_id=director_user_id, active=True).first()
        if not director:
            _fail("The selected Director is not active in the PMS directory.")
        if app.inventor_agreements.filter(inventor__user_id=director_user_id).exists():
            _fail("A Director who is an inventor cannot review this application.")
        domains = {str(x).casefold() for x in director.expertise_domains}
        if app.technical_domain.casefold() not in domains:
            _fail("The selected Director must match the application expertise domain.")
        open_count = Application.objects.filter(
            assigned_director_user_id=director_user_id,
            status=Application.Status.UNDER_REVIEW,
        ).count()
        if open_count >= director.max_open_reviews:
            _fail("The selected Director has reached the configured review workload limit.")
        app.assigned_director_user_id = director_user_id
        app.assigned_at = timezone.now()
        app.review_due_at = timezone.make_aware(
            datetime.combine(_business_days_after(timezone.localdate(), 15), time.max)
        )
        _transition(
            app,
            actor_id,
            "director_assigned",
            Application.Status.UNDER_REVIEW,
            metadata={"director_user_id": director_user_id},
        )
        app.save(
            update_fields=[
                "assigned_director_user_id",
                "assigned_at",
                "review_due_at",
                "updated_at",
            ]
        )
        Deadline.objects.create(
            application=app,
            kind="director_review",
            due_at=app.review_due_at,
            responsible_user_id=director_user_id,
            source="15-business-day PMS review rule",
        )
        _notify(
            app,
            director_user_id,
            "application.director_assigned",
            "Patent application assigned",
            f"Review {app.application_number} by {app.review_due_at.date()}.",
        )
        return app


def review_application(app_id, actor_id, decision, justification):
    outcomes = {
        "approved": Application.Status.APPROVED,
        "rejected": Application.Status.REJECTED,
        "needs_revision": Application.Status.NEEDS_REVISION,
    }
    if decision not in outcomes:
        _fail("Decision must be approved, rejected, or needs_revision.")
    if len((justification or "").strip()) < 50:
        _fail("Director decisions require a justification of at least 50 characters.")
    with transaction.atomic():
        app = Application.objects.select_for_update().get(pk=app_id)
        if app.assigned_director_user_id != actor_id:
            raise PermissionDenied("Only the assigned Director may decide this application.")
        if app.status != Application.Status.UNDER_REVIEW:
            _fail("The application is not awaiting Director review.")
        now = timezone.now()
        review_was_late = bool(app.review_due_at and now > app.review_due_at)
        review_deadline = (
            Deadline.objects.filter(application=app, kind="director_review", status="open")
            .order_by("-created_at")
            .first()
        )
        if review_deadline:
            review_deadline.status = "missed" if review_was_late else "completed"
            review_deadline.save(update_fields=["status"])
        app.decision_at = now
        app.revision_due_at = (
            now + timedelta(days=60) if decision in ("rejected", "needs_revision") else None
        )
        _transition(
            app, actor_id, f"director_decision_{decision}", outcomes[decision], justification
        )
        app.save(update_fields=["decision_at", "revision_due_at", "updated_at"])
        if review_was_late:
            _audit(
                app,
                actor_id,
                "director_review_deadline_missed",
                app.status,
                app.status,
                {"review_due_at": app.review_due_at.isoformat()},
            )
        _notify(
            app,
            app.applicant_user_id,
            f"application.{decision}",
            "Patent application review decision",
            f"{app.application_number}: {decision}. {justification}",
        )
        return app


def resubmit_revision(app_id, actor_id, feedback_response):
    with transaction.atomic():
        app = Application.objects.select_for_update().get(pk=app_id)
        _applicant(app, actor_id)
        if app.status not in (Application.Status.NEEDS_REVISION, Application.Status.REJECTED):
            _fail("Only applications marked Needs Revision or Rejected may be resubmitted.")
        if not app.revision_due_at:
            _fail("PMS has no resubmission deadline recorded for this application.")
        if timezone.now() > app.revision_due_at:
            _transition(app, actor_id, "revision_deadline_expired", Application.Status.EXPIRED)
            return app
        if not (feedback_response or "").strip():
            _fail("Describe how the revision addresses the Director feedback.")
        _complete_document_set(app)
        app.revision_count += 1
        app.decision_at = None
        app.revision_due_at = None
        app.assigned_director_user_id = None
        app.assigned_at = None
        app.review_due_at = None
        _transition(
            app,
            actor_id,
            "application_resubmitted",
            Application.Status.RESUBMITTED,
            feedback_response,
        )
        app.save(
            update_fields=[
                "revision_count",
                "decision_at",
                "revision_due_at",
                "assigned_director_user_id",
                "assigned_at",
                "review_due_at",
                "updated_at",
            ]
        )
        return app


def withdraw_application(app_id, actor_id, reason, co_inventor_consents=False):
    with transaction.atomic():
        app = Application.objects.select_for_update().get(pk=app_id)
        _applicant(app, actor_id)
        if app.status in (
            Application.Status.FILED,
            Application.Status.GRANTED,
            Application.Status.ABANDONED,
            Application.Status.WITHDRAWN,
        ):
            _fail("Withdrawal is only available before filing.")
        eligible = _config("withdrawal_eligible_statuses", [])
        if app.status not in eligible:
            _fail("PMS has no configured rule that permits withdrawal in the current status.")
        if not (reason or "").strip():
            _fail("A withdrawal reason is required.")
        outstanding = app.inventor_agreements.exclude(inventor__user_id=actor_id)
        consent_required = _config("withdrawal_requires_co_inventor_consent", False)
        if consent_required and outstanding.exclude(agreement_status="accepted").exists():
            _fail("Required co-inventor consent must be recorded before withdrawal.")
        _transition(
            app,
            actor_id,
            "application_withdrawn",
            Application.Status.WITHDRAWN,
            reason,
            {
                "co_inventor_consents_recorded": consent_required
                and not outstanding.exclude(agreement_status="accepted").exists()
            },
        )
        _notify(
            app,
            app.applicant_user_id,
            "application.withdrawn",
            "Patent application withdrawn",
            f"{app.application_number}: {reason}",
        )
        return app


def assign_attorney(app_id, attorney_user_id, actor_id, panel_exception=""):
    with transaction.atomic():
        app = Application.objects.select_for_update().get(pk=app_id)
        if app.status != Application.Status.APPROVED:
            _fail("Attorney assignment is allowed only after Director approval.")
        profile = AttorneyProfile.objects.filter(user_id=attorney_user_id, active=True).first()
        if not profile:
            _fail("The selected Attorney is not active in the PMS directory.")
        if not profile.panel_approved and not (panel_exception or "").strip():
            _fail(
                "The Attorney must be on the approved panel or have a recorded "
                "institutional exception."
            )
        if app.inventor_agreements.filter(inventor__user_id=attorney_user_id).exists():
            _fail("An Attorney who is an inventor cannot be assigned to this application.")
        domains = {str(x).casefold() for x in profile.expertise_domains}
        if app.technical_domain.casefold() not in domains:
            _fail("The selected Attorney must match the application expertise domain.")
        count = AttorneyAssignment.objects.filter(
            attorney_user_id=attorney_user_id,
            status__in=[AttorneyAssignment.Status.OFFERED, AttorneyAssignment.Status.ACCEPTED],
        ).count()
        if count >= profile.max_open_matters:
            _fail("The selected Attorney has reached the configured workload limit.")
        assignment = AttorneyAssignment.objects.create(
            application=app,
            attorney_user_id=attorney_user_id,
            assigned_by_user_id=actor_id,
            panel_exception=panel_exception,
            preference_recorded=(app.preferred_attorney_user_id == attorney_user_id),
        )
        app.assigned_attorney_user_id = attorney_user_id
        app.save(update_fields=["assigned_attorney_user_id", "updated_at"])
        _audit(
            app,
            actor_id,
            "attorney_assignment_offered",
            app.status,
            app.status,
            {"attorney_user_id": attorney_user_id},
        )
        _notify(
            app,
            attorney_user_id,
            "application.attorney_assigned",
            "Patent matter assignment offered",
            f"Accept or decline {app.application_number}.",
        )
        return assignment


def respond_to_attorney_assignment(assignment_id, actor_id, accept):
    with transaction.atomic():
        assignment = (
            AttorneyAssignment.objects.select_for_update()
            .select_related("application")
            .get(pk=assignment_id)
        )
        if assignment.attorney_user_id != actor_id:
            raise PermissionDenied("Only the assigned Attorney may accept or decline this offer.")
        if assignment.status != AttorneyAssignment.Status.OFFERED:
            _fail("This Attorney assignment is no longer awaiting a response.")
        assignment.status = (
            AttorneyAssignment.Status.ACCEPTED if accept else AttorneyAssignment.Status.DECLINED
        )
        assignment.responded_at = timezone.now()
        assignment.save(update_fields=["status", "responded_at"])
        if not accept:
            assignment.application.assigned_attorney_user_id = None
            assignment.application.save(update_fields=["assigned_attorney_user_id", "updated_at"])
        _audit(
            assignment.application,
            actor_id,
            "attorney_assignment_accepted" if accept else "attorney_assignment_declined",
            assignment.application.status,
            assignment.application.status,
            {"assignment_id": assignment.pk},
        )
        return assignment


def propose_budget(app_id, actor_id, data):
    app = Application.objects.get(pk=app_id)
    if app.status != Application.Status.APPROVED:
        _fail("Budget proposals are permitted only for Director-approved applications.")
    proposal = BudgetProposal.objects.create(application=app, **data)
    _audit(
        app,
        actor_id,
        "budget_proposed",
        app.status,
        app.status,
        {"budget_id": proposal.pk, "total": str(proposal.total)},
    )
    return proposal


def decide_budget(budget_id, actor_id, decision, justification="", availability_confirmed=False):
    with transaction.atomic():
        budget = (
            BudgetProposal.objects.select_for_update()
            .select_related("application")
            .get(pk=budget_id)
        )
        app = Application.objects.select_for_update().get(pk=budget.application_id)
        if app.assigned_director_user_id != actor_id:
            raise PermissionDenied("Only the assigned Director may decide this budget.")
        if (
            app.status != Application.Status.APPROVED
            or budget.status != BudgetProposal.Status.PROPOSED
        ):
            _fail("This budget is not eligible for decision.")
        if not (justification or "").strip():
            _fail("Record the budget decision reason.")
        if _config("budget_availability_required", False) and not availability_confirmed:
            _fail("Confirm budget availability before making the decision.")
        threshold = _config("budget_escalation_threshold")
        escalation_recipients = []
        if threshold is not None and budget.total > Decimal(str(threshold)):
            escalation_recipients = _config("budget_escalation_user_ids", [])
            if not escalation_recipients:
                _fail("Configure a higher-authority recipient before escalating this budget.")
            budget.status = BudgetProposal.Status.ESCALATED
        else:
            budget.status = (
                BudgetProposal.Status.APPROVED
                if decision == "approved"
                else BudgetProposal.Status.REJECTED
            )
        if decision not in ("approved", "rejected"):
            _fail("Budget decision must be approved or rejected.")
        budget.availability_checked = bool(availability_confirmed)
        budget.decision_by_user_id = actor_id
        budget.decision_justification = justification.strip()
        budget.decided_at = timezone.now()
        budget.save()
        _audit(
            app,
            actor_id,
            f"budget_{budget.status}",
            app.status,
            app.status,
            {"budget_id": budget.pk, "total": str(budget.total)},
        )
        _notify(
            app,
            app.applicant_user_id,
            f"budget.{budget.status}",
            "Patent budget decision",
            f"{app.application_number}: {budget.status}.",
        )
        for recipient in escalation_recipients:
            PmsNotification.objects.get_or_create(
                dedupe_key=f"budget:{budget.pk}:escalation:{recipient}",
                defaults={
                    "recipient_user_id": recipient,
                    "application": app,
                    "event": "budget.escalated",
                    "subject": "Patent budget escalation",
                    "body": (
                        f"Budget {budget.pk} for {app.application_number} exceeds the "
                        "configured threshold and requires higher-authority review."
                    ),
                },
            )
        return budget


def record_filing(
    app_id,
    actor_id,
    *,
    jurisdiction,
    external_filing_id,
    filing_date,
    international_justification="",
    confirmation_reference="",
    format_validation_available=False,
    format_compliant=False,
):
    with transaction.atomic():
        app = Application.objects.select_for_update().get(pk=app_id)
        if app.assigned_attorney_user_id != actor_id:
            raise PermissionDenied("Only the assigned Attorney may record an external filing.")
        if app.status not in (Application.Status.ATTORNEY_ASSIGNED, Application.Status.APPROVED):
            _fail("Application is not in a pre-filing state.")
        if not app.attorney_assignments.filter(status=AttorneyAssignment.Status.ACCEPTED).exists():
            _fail("The assigned Attorney must accept the assignment before filing.")
        if not app.budgets.filter(status=BudgetProposal.Status.APPROVED).exists():
            _fail("Approved budget allocation is required before filing.")
        _complete_document_set(app)
        if app.inventor_agreements.exclude(agreement_status="accepted").exists():
            _fail("All inventor agreements must be accepted before filing.")
        if not jurisdiction or not external_filing_id:
            _fail("Jurisdiction and external filing ID are required.")
        if (
            jurisdiction.casefold() not in ("india", "in", "indian patent office")
            and not international_justification.strip()
        ):
            _fail("International filings require recorded additional justification.")
        if format_validation_available and not format_compliant:
            _fail("The filing package did not pass the available format validation.")
        filing = PatentFiling.objects.create(
            application=app,
            filed_by_user_id=actor_id,
            jurisdiction=jurisdiction,
            external_filing_id=external_filing_id,
            filing_date=filing_date,
            international_justification=international_justification,
            confirmation_reference=confirmation_reference,
            format_validation_available=format_validation_available,
            format_compliant=format_compliant,
        )
        app.filed_at = timezone.now()
        _transition(
            app,
            actor_id,
            "external_filing_recorded",
            Application.Status.FILED,
            metadata={"filing_id": filing.pk, "external_filing_id": external_filing_id},
        )
        app.save(update_fields=["filed_at", "updated_at"])
        _notify(
            app,
            app.applicant_user_id,
            "application.filed",
            "Patent filing recorded",
            f"{app.application_number} was recorded as filed.",
        )
        return filing


def file_appeal(app_id, actor_id, grounds, justification):
    with transaction.atomic():
        app = Application.objects.select_for_update().get(pk=app_id)
        _applicant(app, actor_id)
        if app.status != Application.Status.REJECTED:
            _fail("Only rejected applications may be appealed.")
        period = _config("appeal_period_days")
        if period is None:
            _fail("The applicable appeal period has not been configured in PMS.")
        if app.decision_at and timezone.now() > app.decision_at + timedelta(days=int(period)):
            _fail("The configured appeal period has expired.")
        if not grounds.strip() or not justification.strip():
            _fail("Appeal grounds and justification are required.")
        appeal = PatentAppeal.objects.create(
            application=app, filed_by_user_id=actor_id, grounds=grounds, justification=justification
        )
        _audit(app, actor_id, "appeal_filed", app.status, app.status, {"appeal_id": appeal.pk})
        return appeal


def decide_appeal(appeal_id, actor_id, outcome, justification):
    if not (justification or "").strip():
        _fail("Record the Director's appeal decision justification.")
    with transaction.atomic():
        appeal = (
            PatentAppeal.objects.select_for_update().select_related("application").get(pk=appeal_id)
        )
        app = Application.objects.select_for_update().get(pk=appeal.application_id)
        if app.assigned_director_user_id != actor_id:
            raise PermissionDenied("Only the assigned Director may decide this appeal.")
        if (
            app.status != Application.Status.REJECTED
            or appeal.outcome != PatentAppeal.Outcome.PENDING
        ):
            _fail("This appeal is not pending on a rejected application.")
        if outcome not in {
            x for x, _ in PatentAppeal.Outcome.choices if x != PatentAppeal.Outcome.PENDING
        }:
            _fail("Select a valid appeal outcome.")
        appeal.outcome = outcome
        appeal.decided_by_user_id = actor_id
        appeal.decision_justification = justification.strip()
        appeal.decided_at = timezone.now()
        appeal.save()
        next_status = {
            PatentAppeal.Outcome.UPHOLD: Application.Status.REJECTED,
            PatentAppeal.Outcome.REMAND: Application.Status.NEEDS_REVISION,
            PatentAppeal.Outcome.MODIFY: Application.Status.APPROVED,
        }[outcome]
        _transition(app, actor_id, f"appeal_{outcome}", next_status, justification)
        return appeal


def add_document(app_id, actor_id, uploaded_file, document_type, sensitivity):
    with transaction.atomic():
        app = Application.objects.select_for_update().get(pk=app_id)
        if app.applicant_user_id != actor_id and app.assigned_attorney_user_id != actor_id:
            raise PermissionDenied("You may not add documents to this application.")
        if app.applicant_user_id == actor_id and app.status not in (
            Application.Status.NEEDS_REVISION,
            Application.Status.DRAFT,
        ):
            _fail(
                "Applicants may upload documents only for drafts or applications marked "
                "Needs Revision."
            )
        if uploaded_file.size >= 50 * 1024 * 1024:
            _fail("Documents must be under 50 MB.")
        if not uploaded_file.name.lower().endswith(".pdf"):
            _fail("Application supporting documents must be PDF files.")
        header = uploaded_file.read(5)
        uploaded_file.seek(0)
        if header != b"%PDF-":
            _fail("The uploaded file does not contain a valid PDF signature.")
        if sensitivity not in ApplicationDocument.Sensitivity.values:
            _fail("Choose a supported document sensitivity level.")
        previous = (
            ApplicationDocument.objects.filter(application=app, document_type=document_type)
            .order_by("-version")
            .first()
        )
        return ApplicationDocument.objects.create(
            application=app,
            uploaded_by_user_id=actor_id,
            document_type=document_type,
            sensitivity=sensitivity,
            file=uploaded_file,
            original_filename=uploaded_file.name[:255],
            content_type="application/pdf",
            size_bytes=uploaded_file.size,
            version=(previous.version + 1 if previous else 1),
            previous_version=previous,
            malware_scan_status="pending",
        )
