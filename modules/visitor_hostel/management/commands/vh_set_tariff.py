"""Record a new tariff version. Tariffs are never edited (BR-VH-024).

    manage.py vh_set_tariff --category A --occupancy single --rate 1500 --from 2026-11-01
    manage.py vh_set_tariff --meal breakfast --rate 60 --from 2026-11-01
    manage.py vh_set_tariff --show
"""
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from core.api.exceptions import DomainError
from modules.visitor_hostel.domain import meals, tariffs
from modules.visitor_hostel.models import MealTariff, RoomTariff
from modules.visitor_hostel.services import configuration


class Command(BaseCommand):
    help = "Add a room or meal tariff with an effective-from date (UC-VH-011)"

    def add_arguments(self, parser):
        parser.add_argument("--category", choices=tariffs.CATEGORIES)
        parser.add_argument("--occupancy", choices=tariffs.OCCUPANCIES)
        parser.add_argument("--meal", choices=meals.PRICED_ITEMS)
        parser.add_argument("--rate")
        parser.add_argument("--from", dest="effective_from")
        parser.add_argument("--show", action="store_true")

    def handle(self, *args, **opts):
        if opts["show"]:
            for t in RoomTariff.objects.order_by("category", "occupancy", "effective_from"):
                self.stdout.write(f"  room {t.category}/{t.occupancy:<7} "
                                  f"{t.rate_per_day:>10}  from {t.effective_from}")
            for t in MealTariff.objects.order_by("item", "effective_from"):
                self.stdout.write(f"  meal {t.item:<9} {t.rate:>10}  from {t.effective_from}")
            return
        try:
            rate = Decimal(opts["rate"] or "")
            effective_from = date.fromisoformat(opts["effective_from"] or "")
        except (InvalidOperation, ValueError) as exc:
            raise CommandError("--rate must be a number and --from YYYY-MM-DD.") from exc
        try:
            if opts["meal"]:
                configuration.add_meal_tariff(item=opts["meal"], rate=rate,
                                              effective_from=effective_from)
            elif opts["category"] and opts["occupancy"]:
                configuration.add_room_tariff(category=opts["category"],
                                              occupancy=opts["occupancy"], rate=rate,
                                              effective_from=effective_from)
            else:
                raise CommandError("Give --meal, or both --category and --occupancy.")
        except DomainError as exc:
            raise CommandError(exc.message) from exc
        self.stdout.write(self.style.SUCCESS("  tariff recorded"))
