"""Mint, list and revoke the credentials peer services use to read the directory.

    manage.py service_token --issue fusion-integrated
    manage.py service_token --list
    manage.py service_token --revoke fusion-integrated

The raw value is printed exactly once. It is stored only as a SHA-256 digest,
so losing it means issuing a new one — which is the point.
"""
from django.core.management.base import BaseCommand, CommandError

from iam.models import IamServiceToken


class Command(BaseCommand):
    help = "Manage IAM service tokens (server-to-server directory access)."

    def add_arguments(self, parser):
        g = parser.add_mutually_exclusive_group(required=True)
        g.add_argument("--issue", metavar="NAME",
                       help="Create a token and print it once.")
        g.add_argument("--rotate", metavar="NAME",
                       help="Replace an existing token's value, keeping its name.")
        g.add_argument("--revoke", metavar="NAME",
                       help="Deactivate a token. Existing callers start failing.")
        g.add_argument("--list", action="store_true",
                       help="Show every token, without its value.")

    def handle(self, *args, **opts):
        if opts["list"]:
            return self._list()
        if opts["revoke"]:
            return self._revoke(opts["revoke"])
        if opts["rotate"]:
            return self._rotate(opts["rotate"])
        return self._issue(opts["issue"])

    def _print_value(self, verb, name, raw):
        self.stdout.write(self.style.SUCCESS(f"\n{verb} service token {name!r}.\n"))
        self.stdout.write("  Put this in the calling service's environment:\n\n")
        self.stdout.write(f"      IAM_SERVICE_TOKEN={raw}\n\n")
        self.stdout.write(self.style.WARNING(
            "  Shown once. Only its digest is stored — there is no way to "
            "print it again.\n"))

    def _issue(self, name):
        existing = IamServiceToken.objects.filter(name=name).first()
        if existing is not None:
            # Revoking does not free the name: it is unique and the row stays.
            state = "active" if existing.is_active else "revoked"
            raise CommandError(
                f"A token named {name!r} already exists ({state}). Names are "
                f"unique, so replace its value with --rotate {name}, or issue "
                f"under a different name."
            )
        _, raw = IamServiceToken.issue(name)
        self._print_value("Issued", name, raw)

    def _rotate(self, name):
        token = IamServiceToken.objects.filter(name=name).first()
        if token is None:
            raise CommandError(
                f"No token named {name!r}. Create it with --issue {name}.")
        was_revoked = not token.is_active
        self._print_value("Rotated", name, token.rotate())
        if was_revoked:
            self.stdout.write("  It was revoked; rotating has made it active "
                              "again.\n")

    def _revoke(self, name):
        n = IamServiceToken.objects.filter(name=name, is_active=True).update(
            is_active=False)
        if not n:
            raise CommandError(f"No active token named {name!r}.")
        self.stdout.write(self.style.SUCCESS(f"Revoked {name!r}."))

    def _list(self):
        rows = list(IamServiceToken.objects.all())
        if not rows:
            self.stdout.write("No service tokens issued.")
            return
        self.stdout.write(f"{'NAME':<28} {'STATE':<9} {'CREATED':<18} LAST USED")
        for t in rows:
            state = "active" if t.is_active else "revoked"
            used = f"{t.last_used_at:%Y-%m-%d %H:%M}" if t.last_used_at else "never"
            self.stdout.write(f"{t.name:<28} {state:<9} "
                              f"{t.created_at:%Y-%m-%d %H:%M}   {used}")
