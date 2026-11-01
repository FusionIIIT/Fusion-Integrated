"""Seed the current configuration (BR-EL-030, BR-EL-038).

    manage.py seed_leave_policy            seed what is missing
    manage.py seed_leave_policy --replace  overwrite the configured values

Nothing here invents an entitlement: the numbers are the ones the business
rules state, and an administrator edits them afterwards (EL-UC-014).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from modules.leave.domain import categories as cat
from modules.leave.models import (
    LeaveHierarchyStep,
    LeavePolicy,
    SlaThreshold,
)

#: The hierarchy the synchronized baseline describes. Department Unit Head
#: designations are per institute practice and are edited, not guessed.
DEFAULT_HIERARCHY = [
    {"sequence": 10, "kind": "unit_head", "designation": "HOD (CSE)"},
    {"sequence": 20, "kind": "establishment", "designation": "Deputy Registrar (Estt.)"},
    {"sequence": 30, "kind": "final_authority", "designation": "Registrar"},
]

DEFAULT_THRESHOLDS = [
    {"task_class": "substitute_response", "reminder_hours": 24,
     "escalation_hours": 72},
    {"task_class": "unit_head_review", "reminder_hours": 48,
     "escalation_hours": 120},
    {"task_class": "establishment_routing", "reminder_hours": 24,
     "escalation_hours": 72},
    {"task_class": "final_sanction", "reminder_hours": 48, "escalation_hours": 168},
]


class Command(BaseCommand):
    help = "Seed the leave policy, hierarchy and SLA thresholds"

    def add_arguments(self, parser):
        parser.add_argument("--replace", action="store_true",
                            help="Overwrite values an administrator may have set.")

    @transaction.atomic
    def handle(self, *args, **opts):
        replace = opts["replace"]

        policy, created = LeavePolicy.objects.get_or_create(
            is_active=True,
            defaults={"entitlements": dict(cat.ANNUAL_ENTITLEMENT),
                      "substitute_required_categories": []})
        if created or replace:
            policy.entitlements = dict(cat.ANNUAL_ENTITLEMENT)
            policy.save(update_fields=["entitlements", "updated_at"])
        self.stdout.write(f"  policy            {'created' if created else 'present'}")

        if replace or not LeaveHierarchyStep.objects.exists():
            LeaveHierarchyStep.objects.all().delete()
            for step in DEFAULT_HIERARCHY:
                LeaveHierarchyStep.objects.create(**step)
            self.stdout.write(f"  hierarchy steps   {len(DEFAULT_HIERARCHY)}")
        else:
            self.stdout.write(f"  hierarchy steps   "
                              f"{LeaveHierarchyStep.objects.count()} (kept)")

        for threshold in DEFAULT_THRESHOLDS:
            SlaThreshold.objects.get_or_create(task_class=threshold["task_class"],
                                               defaults=threshold)
        self.stdout.write(f"  sla thresholds    {SlaThreshold.objects.count()}")

        self.stdout.write(self.style.SUCCESS("leave configuration seeded"))
