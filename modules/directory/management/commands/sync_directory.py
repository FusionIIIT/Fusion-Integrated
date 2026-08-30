"""Pull the payroll into the local projection.

The projection normally fills in lazily, one batch of ids at a time, as screens
ask for names. That is right for display and wrong for anything that acts on
"every employee": leave credits a year's entitlement to all of them, and a
projection holding whoever happened to be looked at would credit a fraction of
the institute and report success.

Run it after sync_identity on the IAM, and whenever staff join.
"""
from django.core.management.base import BaseCommand, CommandError

from fusion_auth.client import IamUnavailable, get_client
from modules.directory.models import UserRef
from modules.directory.services.sync import upsert


class Command(BaseCommand):
    help = "Refresh the local employee directory from the identity service."

    def add_arguments(self, parser):
        parser.add_argument("--page-size", type=int, default=500)
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would change and write nothing.")

    def handle(self, *args, **opts) -> None:
        before = UserRef.objects.filter(kind__in=("faculty", "staff")).count()
        try:
            fetched = list(get_client().iter_employees(page_size=opts["page_size"]))
        except IamUnavailable as exc:
            raise CommandError(
                f"The identity service is unreachable: {exc}. Nothing was changed."
            ) from exc

        if not fetched:
            raise CommandError(
                "The identity service reports no employees. Run sync_identity there "
                "first.")

        if opts["dry_run"]:
            known = set(UserRef.objects.values_list("user_id", flat=True))
            new = [r for r in fetched if r.user_id not in known]
            self.stdout.write(
                f"  reported    {len(fetched)}\n"
                f"  already had {len(fetched) - len(new)}\n"
                f"  would add   {len(new)}\n")
            self.stdout.write(self.style.WARNING("  dry run — nothing was written"))
            return

        rejected: list[tuple[int, str]] = []
        written = upsert(fetched, rejected=rejected)
        after = UserRef.objects.filter(kind__in=("faculty", "staff")).count()
        self.stdout.write(
            f"  reported  {len(fetched)}\n"
            f"  written   {written}\n"
            f"  employees {before} -> {after}\n")
        if rejected:
            self.stdout.write(self.style.ERROR(
                f"  {len(rejected)} record(s) could not be stored and were skipped. "
                "Fix them in the IAM — until then those people have no directory "
                "entry here, so their name will not render and they cannot be "
                "credited leave:"))
            for user_id, problem in rejected[:10]:
                self.stdout.write(self.style.ERROR(f"    user {user_id}: {problem}"))

        without_unit = UserRef.objects.filter(
            kind__in=("faculty", "staff"), department="").count()
        if without_unit:
            # Their leave has no unit, so no unit head's queue will show it.
            self.stdout.write(self.style.WARNING(
                f"  {without_unit} employee(s) have no department — their leave "
                "cannot be routed to a unit head until one is set in the IAM"))
        self.stdout.write(self.style.SUCCESS("  directory refreshed"))
