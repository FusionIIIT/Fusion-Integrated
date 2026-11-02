"""Deactivate auth_user rows that are import wreckage, not people."""
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models.erp import AuthUser, GlobalsExtrainfo, GlobalsHoldsdesignation


class Command(BaseCommand):
    help = "Find, and optionally deactivate, corrupt auth_user rows from a bad import."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix", action="store_true",
            help="Deactivate the rows. Without this, only reports.")

    def handle(self, *args, **opts) -> None:
        suspects = [
            u for u in AuthUser.objects.all().only("id", "username", "is_active")
            if "\t" in u.username or "\n" in u.username
        ]
        if not suspects:
            self.stdout.write(self.style.SUCCESS("  no malformed usernames"))
            self._report_duplicates()
            return

        classified = set(GlobalsExtrainfo.objects.values_list("user_id", flat=True))
        employed = set(GlobalsHoldsdesignation.objects.values_list("user_id", flat=True))

        artifacts, keep = [], []
        for u in suspects:
            intended = u.username.split("\t")[0].strip()
            twin = (AuthUser.objects.filter(username=intended, is_active=True)
                    .exclude(pk=u.pk).first())
            reasons = []
            if u.id in classified:
                reasons.append("has a globals_extrainfo row")
            if u.id in employed:
                reasons.append("holds a designation")
            if twin is None:
                reasons.append(f"no other active account under {intended!r}")
            (keep if reasons else artifacts).append((u, intended, twin, reasons))

        for u, intended, twin, _ in artifacts:
            state = "active" if u.is_active else "already inactive"
            self.stdout.write(
                f"  artifact  user {u.id} ({state}): {len(u.username)}-char username, "
                f"duplicate of user {twin.id} ({intended})")
        for u, intended, _, reasons in keep:
            self.stdout.write(self.style.WARNING(
                f"  LEFT ALONE user {u.id}: malformed username but {'; '.join(reasons)} "
                "— needs a person to look at it"))

        self._report_duplicates()

        live = [a for a in artifacts if a[0].is_active]
        if not opts["fix"]:
            self.stdout.write(self.style.WARNING(
                f"  {len(live)} row(s) would be deactivated — re-run with --fix"))
            return

        with transaction.atomic():
            AuthUser.objects.filter(pk__in=[a[0].pk for a in live]).update(is_active=False)
        self.stdout.write(self.style.SUCCESS(
            f"  deactivated {len(live)} row(s). Run sync_identity to carry it across."))

    def _whitespace_duplicates(self) -> list[tuple]:
        """Accounts that are the same username once trimmed."""
        by_trimmed: dict[str, list] = {}
        for u in AuthUser.objects.all().only("id", "username", "last_login", "is_active"):
            by_trimmed.setdefault(u.username.strip(), []).append(u)
        return [(k, v) for k, v in sorted(by_trimmed.items()) if len(v) > 1]

    def _report_duplicates(self) -> None:
        pairs = self._whitespace_duplicates()
        if not pairs:
            return
        employed = dict(
            GlobalsHoldsdesignation.objects.values_list("user_id", "designation_id"))
        classified = set(GlobalsExtrainfo.objects.values_list("user_id", flat=True))
        self.stdout.write(self.style.WARNING(
            f"\n  {len(pairs)} username(s) exist twice, differing only by whitespace. "
            "One person, two logins. Not touched -- which account keeps their "
            "designations is a decision about their role:"))
        for name, users in pairs:
            self.stdout.write(f"    {name!r}")
            for u in sorted(users, key=lambda x: x.id):
                marks = []
                if u.id in classified:
                    marks.append("has profile")
                if u.id in employed:
                    marks.append("holds designation")
                marks.append("has logged in" if u.last_login else "never logged in")
                if not u.is_active:
                    marks.append("inactive")
                self.stdout.write(
                    f"      user {u.id:<6} {u.username!r:<20} {', '.join(marks)}")
