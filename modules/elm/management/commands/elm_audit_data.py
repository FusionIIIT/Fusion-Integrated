"""Report Phase-1 data that needs reconciliation before production use."""

import json

from django.core.management.base import BaseCommand, CommandError

from modules.elm.domain.state_machine import PENDING
from modules.elm.models import AccountEntry, EmployeeRecord, LeaveBalance, LeaveRequest


class Command(BaseCommand):
    help = "Read-only ELM data preflight. Does not guess identity mappings or rewrite accounts."

    def handle(self, *args, **options):
        issues = []
        known = set(EmployeeRecord.objects.filter(is_active=True).values_list("user_id", flat=True))
        for req in LeaveRequest.objects.all():
            if not req.applicant_user_id.isdecimal() or req.applicant_user_id not in known:
                issues.append(
                    {"request": str(req.pk), "issue": "Unmapped or inactive employee identity"}
                )
            if req.status in PENDING and (not req.route or not req.current_approver_user_id):
                issues.append({"request": str(req.pk), "issue": "Unresolved legacy workflow"})
        for b in LeaveBalance.objects.all():
            if b.user_id not in known:
                issues.append({"balance": str(b.pk), "issue": "Unmapped or inactive account owner"})
            if not AccountEntry.objects.filter(
                user_id=b.user_id, leave_type=b.leave_type, year=b.year
            ).exists():
                issues.append(
                    {
                        "balance": str(b.pk),
                        "issue": "Legacy account lacks audited opening entries; "
                        "reconcile entitlement and usage",
                    }
                )
            if b.credited < b.availed + b.pending:
                issues.append({"balance": str(b.pk), "issue": "Overdrawn ledger"})
        self.stdout.write(json.dumps({"issues": issues}, indent=2))
        if issues:
            raise CommandError(
                "Preflight failed; reconcile the reported records before deployment."
            )
        self.stdout.write("ELM data preflight passed.")
