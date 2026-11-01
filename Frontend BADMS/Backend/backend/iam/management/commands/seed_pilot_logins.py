"""Seed a handful of working ERP-user logins for local pilot/course use.

    manage.py seed_pilot_logins [--password PASSWORD]
                                [--extra "uid:username:display_name:kind:discipline:batch_year"]...

Not the real ERP sync (that is sync_identity, which reads fusionlab). This
command writes directly to IamUser with a known password, so a pair testing
ELM locally does not need the full fusion-dev.dump restored to get a working
login. Idempotent — safe to re-run after wiping a local DB.

Deliberately does not touch IamUserDesignation: every account it creates
starts with zero held designations beyond its basic kind. Use assign_role to
grant whatever designation an ELM implementation invents.
"""
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from iam.models import IamUser

DEFAULT_PASSWORD = "pilot123"

#: Mirrors Fusion-Integrated's devtools/.../seed_demo.py UserRef rows, so the
#: same ids resolve to the same people in both services.
DEFAULT_ACCOUNTS = [
    (1001, "u1001", "Asha Verma", "student", "CSE", 2023),
    (1002, "u1002", "Bo Li", "student", "CSE", 2023),
    (1003, "u1003", "Chandra Rao", "student", "ECE", 2023),
    (9001, "u9001", "Dr. Meera Nair", "faculty", "", None),
]


class Command(BaseCommand):
    help = "Seed a handful of local ERP-user test logins with no designations"

    def add_arguments(self, parser):
        parser.add_argument("--password", default=DEFAULT_PASSWORD,
                            help=f"Password for every seeded account (default: {DEFAULT_PASSWORD})")
        parser.add_argument("--extra", action="append", default=[],
                            help="uid:username:display_name:kind:discipline:batch_year, repeatable")

    def _parse_extra(self, raw):
        parts = raw.split(":")
        if len(parts) != 6:
            raise CommandError(
                f"--extra {raw!r} needs 6 colon-separated fields: "
                "uid:username:display_name:kind:discipline:batch_year")
        uid, username, display_name, kind, discipline, batch_year = parts
        try:
            uid = int(uid)
        except ValueError:
            raise CommandError(f"--extra {raw!r}: uid must be an integer")
        if kind not in dict(IamUser.KINDS):
            raise CommandError(f"--extra {raw!r}: kind must be one of {list(dict(IamUser.KINDS))}")
        return (uid, username, display_name, kind, discipline,
                int(batch_year) if batch_year else None)

    @transaction.atomic
    def handle(self, *args, **opts):
        password = opts["password"]
        accounts = list(DEFAULT_ACCOUNTS)
        accounts += [self._parse_extra(raw) for raw in opts["extra"]]

        password_hash = make_password(password)
        rows = []
        for uid, username, display_name, kind, discipline, batch_year in accounts:
            user, _ = IamUser.objects.update_or_create(
                erp_user_id=uid,
                defaults={
                    "username": username, "display_name": display_name,
                    "kind": kind, "is_active": True,
                    "password_hash": password_hash,
                    "discipline": discipline, "batch_year": batch_year,
                },
            )
            rows.append(user)

        self.stdout.write(self.style.SUCCESS(f"{len(rows)} login(s) ready, password {password!r}:"))
        for user in rows:
            self.stdout.write(f"  {user.username:10s} {user.display_name:20s} {user.kind}")
