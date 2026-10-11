"""SLA reminder and escalation processing service."""

from __future__ import annotations

from django.utils import timezone

from modules.leave.models import LeaveTransition, SlaClock, SlaRule
from modules.leave.selectors.policy import get_active_policy


def process_sla_clocks() -> dict[str, int]:
    """Processes SLA reminders and escalations under EL-UC-021, BR-EL-032, and BR-EL-033."""
    now = timezone.now()
    policy = get_active_policy()
    rules_map: dict[str, SlaRule] = {}
    if policy:
        for r in SlaRule.objects.filter(policy=policy):
            rules_map[r.state] = r

    summary = {"reminded": 0, "escalated": 0}
    clocks = SlaClock.objects.select_related("request").filter(
        request__state__in=[
            "submitted_pending_substitute",
            "pending_review",
            "pending_routing",
            "pending_sanction",
            "cancellation_pending_review",
            "cancellation_pending_routing",
            "cancellation_pending_sanction",
            "extension_pending_substitute",
            "extension_pending_review",
            "extension_pending_routing",
            "extension_pending_sanction",
            "resumption_pending",
        ]
    )

    for clock in clocks:
        req = clock.request
        sla_rule = rules_map.get(clock.state)
        remind_hours = sla_rule.remind_after_hours if sla_rule else 48
        escalate_hours = sla_rule.escalate_after_hours if sla_rule else 96

        elapsed_hours = (now - clock.entered_at).total_seconds() / 3600.0

        # Reminder check (BR-EL-032)
        if not clock.reminded_at and elapsed_hours >= remind_hours:
            clock.reminded_at = now
            clock.save(update_fields=["reminded_at"])
            LeaveTransition.objects.create(
                request=req,
                from_state=req.state,
                to_state=req.state,
                event="sla_reminder",
                actor_role="System",
                remark=f"SLA reminder issued after {elapsed_hours:.1f} hours",
                workflow_ref="BR-EL-032",
            )
            summary["reminded"] += 1

        # Escalation check (BR-EL-033)
        if not clock.escalated_at and elapsed_hours >= escalate_hours:
            clock.escalated_at = now
            clock.save(update_fields=["escalated_at"])
            if sla_rule and sla_rule.escalate_to_designation:
                req.sanctioning_designation = sla_rule.escalate_to_designation
                req.save(update_fields=["sanctioning_designation", "updated_at"])

            LeaveTransition.objects.create(
                request=req,
                from_state=req.state,
                to_state=req.state,
                event="sla_escalation",
                actor_role="System",
                remark=f"SLA escalated after {elapsed_hours:.1f} hours",
                workflow_ref="BR-EL-033",
            )
            summary["escalated"] += 1

    return summary
