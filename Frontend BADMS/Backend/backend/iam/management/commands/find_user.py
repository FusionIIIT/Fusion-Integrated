"""Look up a username to pass to assign_role.

    manage.py find_user --kind faculty
    manage.py find_user --kind staff --q "mehta"
    manage.py find_user --q "verma"

After a fusion-dev.dump restore + sync_identity, nobody has a roster of 3277
usernames — students only know the stuNNNNN pattern, not faculty/staff ones.
This searches display_name as well as username, which search_directory
(iam/services.py, used by the HTTP API) does not: that one is username-only,
built for a client that already has a name-to-username mapping elsewhere.
"""
from django.core.management.base import BaseCommand

from iam.models import IamUser


class Command(BaseCommand):
    help = "Search the synced directory for a username, by name or kind"

    def add_arguments(self, parser):
        parser.add_argument("--kind", choices=[k for k, _ in IamUser.KINDS],
                            help="Restrict to student / faculty / staff / ...")
        parser.add_argument("--q", default="",
                            help="Substring match on username or display name")
        parser.add_argument("--limit", type=int, default=25)

    def handle(self, *args, **opts):
        qs = IamUser.objects.filter(is_active=True)
        if opts["kind"]:
            qs = qs.filter(kind=opts["kind"])
        q = opts["q"].strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(username__icontains=q) | Q(display_name__icontains=q))
        qs = qs.order_by("display_name")[:opts["limit"]]

        rows = list(qs)
        if not rows:
            self.stdout.write(self.style.WARNING("No match."))
            return
        for u in rows:
            where = u.discipline or u.department or ""
            self.stdout.write(
                f"  {u.username:12s} {u.display_name:28s} {u.kind:8s} {where}")
        self.stdout.write(self.style.SUCCESS(f"{len(rows)} match(es)"))
