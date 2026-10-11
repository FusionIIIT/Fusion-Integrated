"""Apply the ELM calendar-year carry, lapse and vacation conversion rules."""

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from modules.elm.models import (
    LeaveAccount,
    LeaveCategory,
    LeaveReservation,
    LeaveTransaction,
    YearEndRun,
)

PROCESS_PERMISSION = "elm.system.process"


class Command(BaseCommand):
    help = "Process one completed leave year once (carry, lapse and VL-to-EL conversion)."

    def add_arguments(self, parser):
        parser.add_argument("year", type=int)

    @transaction.atomic
    def handle(self, *args, **options):
        year = options["year"]
        if year < 2000 or year > 2200:
            raise CommandError("Year must be between 2000 and 2200.")
        if YearEndRun.objects.filter(year=year, status="completed").exists():
            raise CommandError(f"Year-end processing for {year} is already complete.")
        run, created = YearEndRun.objects.get_or_create(year=year)
        if not created:
            run.status = "running"
            run.exceptions = []
        run.save(update_fields=["status", "exceptions"])
        categories = {row.code: row for row in LeaveCategory.objects.all()}
        earned = categories.get("EL")
        summary = {"carried": 0, "lapsed": 0, "converted": 0, "accounts": 0}
        exceptions = []
        accounts = (
            LeaveAccount.objects.select_for_update().filter(year=year).select_related("category")
        )
        for old in accounts:
            reserved = LeaveReservation.objects.filter(account=old, is_active=True).aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0")
            if reserved:
                exceptions.append(
                    {
                        "user_id": old.user_id,
                        "category": old.category.code,
                        "reason": "active_reservations",
                        "reserved": str(reserved),
                    }
                )
                continue
            ledger = old.transactions.aggregate(total=Sum("amount"))["total"] or Decimal("0")
            available = old.annual_entitlement + old.opening_balance + ledger
            if available < 0:
                exceptions.append(
                    {
                        "user_id": old.user_id,
                        "category": old.category.code,
                        "reason": "negative_balance",
                        "balance": str(available),
                    }
                )
                continue
            next_account, _ = LeaveAccount.objects.get_or_create(
                user_id=old.user_id,
                category=old.category,
                year=year + 1,
                defaults={"annual_entitlement": old.category.annual_entitlement},
            )
            summary["accounts"] += 1
            if old.category.code in {"EL", "COL"}:
                if available:
                    LeaveTransaction.objects.create(
                        account=next_account,
                        kind="credit",
                        amount=available,
                        reference=f"year-end:{year}",
                        note=f"Carry-forward from {year}.",
                    )
                    summary["carried"] += 1
            elif old.category.code == "VL":
                if earned is None:
                    exceptions.append(
                        {"user_id": old.user_id, "category": "VL", "reason": "EL_category_missing"}
                    )
                    continue
                target, _ = LeaveAccount.objects.get_or_create(
                    user_id=old.user_id,
                    category=earned,
                    year=year + 1,
                    defaults={"annual_entitlement": earned.annual_entitlement},
                )
                if available:
                    converted = available / Decimal("2")
                    LeaveTransaction.objects.create(
                        account=old,
                        kind="conversion",
                        amount=-available,
                        reference=f"year-end:{year}",
                        note="Unused VL converted at 2:1.",
                    )
                    LeaveTransaction.objects.create(
                        account=target,
                        kind="conversion",
                        amount=converted,
                        reference=f"year-end:{year}",
                        note=f"VL carry conversion from {year}.",
                    )
                    summary["converted"] += 1
            elif old.category.code in {"CL", "RH", "SCL"} and available:
                LeaveTransaction.objects.create(
                    account=old,
                    kind="lapse",
                    amount=-available,
                    reference=f"year-end:{year}",
                    note=f"Unused {old.category.code} lapsed.",
                )
                summary["lapsed"] += 1
        run.status = "completed"
        run.completed_at = timezone.now()
        run.summary = summary
        run.exceptions = exceptions
        run.save(update_fields=["status", "completed_at", "summary", "exceptions"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Year {year}: carried {summary['carried']}, lapsed {summary['lapsed']}, "
                f"converted {summary['converted']}; {len(exceptions)} exception(s)."
            )
        )
