"""Is the scheduled work actually happening?

    manage.py scheduled_work_status
    manage.py scheduled_work_status --max-lag 600     non-zero exit past that

Beat not running is silent by nature: nothing errors, work simply stops. The
symptoms show up as an outbox that only grows and offers that never expire, so
those are what this reports. Suitable for a cron or a monitoring check.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.placement.models import NotificationOutbox, Offer, PlacementStatsSnapshot


class Command(BaseCommand):
    help = "Report outbox lag, overdue offers and snapshot staleness"

    def add_arguments(self, parser):
        parser.add_argument("--max-lag", type=int, default=0,
                            help="Exit 1 if the oldest pending row is older "
                                 "than this many seconds.")

    def handle(self, *args, **opts):
        now = timezone.now()
        problems = []

        pending = NotificationOutbox.objects.filter(status="pending")
        oldest = pending.order_by("created_at").values_list(
            "created_at", flat=True).first()
        lag = int((now - oldest).total_seconds()) if oldest else 0
        self.stdout.write(f"  outbox pending    {pending.count()}")
        self.stdout.write(f"  oldest pending    {lag}s")
        if opts["max_lag"] and lag > opts["max_lag"]:
            problems.append(f"outbox lag {lag}s exceeds {opts['max_lag']}s — is "
                            f"the notifications worker draining?")

        # The one that costs a student their place: an issued offer past its
        # deadline still blocks their pool until the sweep retires it.
        overdue = Offer.objects.filter(status="issued", respond_by__lt=now).count()
        self.stdout.write(f"  offers overdue    {overdue}")
        if overdue:
            problems.append(f"{overdue} issued offer(s) are past respond_by and "
                            f"still open — expire_overdue_offers is not running.")

        newest = PlacementStatsSnapshot.objects.order_by("-computed_at") \
            .values_list("computed_at", flat=True).first()
        age = int((now - newest).total_seconds()) if newest else None
        self.stdout.write(f"  stats age         {age}s" if age is not None
                          else "  stats age         never computed")

        if problems:
            self.stdout.write("")
            for p in problems:
                self.stdout.write(self.style.ERROR(f"  {p}"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("\n  scheduled work looks healthy"))
