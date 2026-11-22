"""Scheduled and event-triggered services for SLA reminders, renewals, and role reassignments.

(UC-SPACS-024, UC-SPACS-025, UC-SPACS-026, BR-SPACS-013, BR-SPACS-022).
"""
from __future__ import annotations

from datetime import timedelta
from django.utils import timezone

from modules.spacs.models import ScholarshipApplication, SchemePolicyVersion
from modules.spacs.services.audit import record_audit_event
from modules.spacs.services.notifications import notify


def send_sla_reminders() -> int:
    """Issues SLA reminder/escalation notifications for overdue tasks (UC-SPACS-024, BR-SPACS-013).

    Does not modify business task state.
    """
    now = timezone.now()
    reminders_sent = 0

    # 1. Overdue verification tasks
    pending_verifications = ScholarshipApplication.objects.filter(
        status__in=["submitted", "under_verification", "resubmitted"]
    ).select_related("policy_version")

    for app in pending_verifications:
        ref_time = app.resubmitted_at or app.submitted_at or app.created_at
        sla_days = app.policy_version.sla_verification_days
        if ref_time and (now - ref_time) > timedelta(days=sla_days):
            target_user = app.assigned_assistant_user_id or 1
            notify(
                recipient_user_id=target_user,
                recipient_role="spacs_assistant",
                event_type="sla.verification_overdue",
                title="SLA Alert: Application Verification Pending",
                message=f"Application {app.application_number} has been pending verification for over {sla_days} days.",
                reference_id=str(app.id),
            )
            reminders_sent += 1

    # 2. Overdue decision tasks
    pending_decisions = ScholarshipApplication.objects.filter(
        status__in=["verified", "verification_concern", "under_convener_review"]
    ).select_related("policy_version")

    for app in pending_decisions:
        ref_time = app.verified_at or app.updated_at
        sla_days = app.policy_version.sla_decision_days
        if ref_time and (now - ref_time) > timedelta(days=sla_days):
            notify(
                recipient_user_id=1,  # Convener role
                recipient_role="spacs_convener",
                event_type="sla.decision_overdue",
                title="SLA Alert: Scholarship Decision Pending",
                message=f"Application {app.application_number} has been awaiting decision for over {sla_days} days.",
                reference_id=str(app.id),
            )
            reminders_sent += 1

    return reminders_sent


def send_renewal_reminders() -> int:
    """Sends renewal reminders before applicable deadlines (UC-SPACS-025, BR-SPACS-017)."""
    now = timezone.now()
    reminders_sent = 0

    # Renewable schemes currently within renewal window
    active_versions = SchemePolicyVersion.objects.filter(
        is_renewable=True,
        status="published",
        renewal_window_start__lte=now,
        renewal_window_end__gte=now,
    ).select_related("scheme")

    for version in active_versions:
        # Students who received an award for this scheme
        approved_apps = ScholarshipApplication.objects.filter(
            scheme=version.scheme,
            status="approved",
        )
        for app in approved_apps:
            # Check if student already applied for renewal in this cycle
            already_applied = ScholarshipApplication.objects.filter(
                student_user_id=app.student_user_id,
                scheme=version.scheme,
                is_renewal=True,
                status__in=["submitted", "under_verification", "verified", "approved"],
            ).exists()
            if not already_applied:
                notify(
                    recipient_user_id=app.student_user_id,
                    recipient_role="student",
                    event_type="renewal.reminder",
                    title=f"Renewal Window Open: {version.scheme.name}",
                    message=f"The renewal window for your {version.scheme.name} scholarship is currently open until {version.renewal_window_end:%Y-%m-%d}.",
                    reference_id=str(app.id),
                )
                reminders_sent += 1

    return reminders_sent


def reassign_pending_tasks(
    *,
    role_code: str,
    from_user_id: int | None = None,
    to_user_id: int,
) -> int:
    """Reassigns pending role-based tasks to the new role holder while preserving history (UC-SPACS-026, BR-SPACS-022)."""
    reassigned = 0
    if role_code in ["spacs_assistant", "assistant"]:
        qs = ScholarshipApplication.objects.filter(
            status__in=["submitted", "under_verification", "resubmitted"]
        )
        if from_user_id is not None:
            qs = qs.filter(assigned_assistant_user_id=from_user_id)
        reassigned = qs.update(assigned_assistant_user_id=to_user_id)

    record_audit_event(
        actor_user_id=None,
        actor_role="system",
        action="tasks.reassigned",
        entity_type="role_assignment",
        entity_id=str(to_user_id),
        details={"role_code": role_code, "from_user_id": from_user_id, "reassigned_count": reassigned},
    )
    return reassigned
