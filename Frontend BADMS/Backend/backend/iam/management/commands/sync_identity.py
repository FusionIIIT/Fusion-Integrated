"""Project ERP identity into IAM.

    manage.py sync_identity                        full sync
    manage.py sync_identity --status               how stale is the projection?
    manage.py sync_identity --status --max-age 1800    exit 1 when staler

Idempotent — safe to run on a schedule and safe to re-run after a failure.
Intended cadence: every 5-15 minutes via cron or a systemd timer. Nothing in
this service schedules it; see ops/systemd/.
"""
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from iam.models import IamRoleViolation
from iam.services import identity_freshness
from iam.sync import SuspectDeactivation, sync_all


class Command(BaseCommand):
    help = "Sync users, designations and module grants from the ERP into IAM"

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=500)
        parser.add_argument(
            "--keep-missing", action="store_true",
            help="Do not deactivate IAM users who are absent from the ERP.")
        parser.add_argument("--status", action="store_true",
                            help="Report freshness and exit.")
        parser.add_argument(
            "--max-age", type=int, default=None, metavar="SECONDS",
            help="With --status, exit 1 when the projection is older than "
                 "this. For a monitor: a dead timer is otherwise silent.")
        parser.add_argument(
            "--force-deactivate", action="store_true",
            help="Carry out a mass deactivation the safety check refused.")

    def handle(self, *args, **o):
        if o["status"]:
            f = identity_freshness()
            if not f["synced"]:
                self.stdout.write(self.style.ERROR("  never synced"))
                if o["max_age"] is not None:
                    sys.exit(1)
                return
            line = (f"  {f['users']} active users, last synced "
                    f"{f['age_seconds']}s ago")
            if o["max_age"] is not None and f["age_seconds"] > o["max_age"]:
                self.stdout.write(self.style.ERROR(
                    f"{line} — over the {o['max_age']}s limit"))
                sys.exit(1)
            self.stdout.write(line)
            return

        try:
            run = sync_all(batch_size=o["batch_size"],
                           deactivate_missing=not o["keep_missing"],
                           force_deactivate=o["force_deactivate"])
        except SuspectDeactivation as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            f"  users seen         {run.users_seen}\n"
            f"  users written      {run.users_written}\n"
            f"  designations       {run.designations_written}\n"
            f"  module grants      {run.module_grants_written}\n"
            f"  academic standings {run.academics_written}\n"
            f"  deactivated        {run.deactivated}\n"
            f"  took               {run.duration_seconds:.1f}s")

        if run.role_violations:
            verb = "refused" if settings.IAM_ENFORCE_ROLE_POLICY else "allowed"
            self.stdout.write(self.style.WARNING(
                f"  {run.role_violations} role(s) a basic role may not hold, "
                f"{verb} — see iam_role_violation:"))
            for v in IamRoleViolation.objects.all()[:20]:
                self.stdout.write(self.style.WARNING(
                    f"    {v.username} ({v.kind}) holds {v.designation}"))

        self.stdout.write(self.style.SUCCESS(f"  {run.status}"))
