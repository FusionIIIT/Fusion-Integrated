from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.leave_elm.models import (
    LeaveBalance,
    LeaveBalanceTransaction,
    YearEndProcessingRun,
)


class Command(BaseCommand):
    help = "Apply year-end leave lapses, carry-forwards, and VL conversion"

    def add_arguments(self, parser):
        parser.add_argument("year", type=int)

    @transaction.atomic
    def handle(self, *args, **options):
        year = options["year"]
        if YearEndProcessingRun.objects.filter(year=year).exists():
            raise CommandError(f"Leave year {year} has already been processed.")
        balances = list(LeaveBalance.objects.filter(year=year).select_related("category"))
        if not balances:
            raise CommandError(f"No leave balances found for {year}.")
        next_balances = {}
        for balance in balances:
            code = balance.category.code
            remaining = balance.closing_balance
            if code in {"CL", "RH", "SCL"}:
                if remaining:
                    LeaveBalanceTransaction.objects.create(
                        balance=balance,
                        transaction_type="lapse",
                        amount=-remaining,
                        note=f"Year-end lapse {year}",
                    )
                balance.closing_balance = Decimal("0")
                balance.save(update_fields=["closing_balance", "updated_at"])
            elif code == "VL":
                converted = remaining / Decimal("2")
                if remaining:
                    LeaveBalanceTransaction.objects.create(
                        balance=balance,
                        transaction_type="conversion",
                        amount=-remaining,
                        note=f"VL converted at 2:1 at year end {year}",
                    )
                balance.closing_balance = Decimal("0")
                balance.save(update_fields=["closing_balance", "updated_at"])
                if converted:
                    next_balance = self._next_balance(
                        balance.user_id, "EL", year + 1, next_balances
                    )
                    next_balance.credited += converted
                    next_balance.closing_balance += converted
                    next_balance.save(update_fields=["credited", "closing_balance", "updated_at"])
                    LeaveBalanceTransaction.objects.create(
                        balance=next_balance,
                        transaction_type="conversion",
                        amount=converted,
                        note=f"Converted from VL in {year}",
                    )
            elif code in {"EL", "COL"}:
                next_balance = self._next_balance(balance.user_id, code, year + 1, next_balances)
                next_balance.opening_balance += remaining
                next_balance.credited += balance.category.annual_entitlement
                next_balance.closing_balance += remaining + balance.category.annual_entitlement
                next_balance.save(
                    update_fields=["opening_balance", "credited", "closing_balance", "updated_at"]
                )
                if remaining:
                    LeaveBalanceTransaction.objects.create(
                        balance=next_balance,
                        transaction_type="carry_forward",
                        amount=remaining,
                        note=f"Carried forward from {year}",
                    )
                if balance.category.annual_entitlement:
                    LeaveBalanceTransaction.objects.create(
                        balance=next_balance,
                        transaction_type="accrual",
                        amount=balance.category.annual_entitlement,
                        note=f"Annual entitlement for {year + 1}",
                    )

        YearEndProcessingRun.objects.create(year=year)
        self.stdout.write(self.style.SUCCESS(f"Processed leave year {year}."))

    @staticmethod
    def _next_balance(user_id, code, year, cache):
        key = (user_id, code, year)
        if key not in cache:
            source = LeaveBalance.objects.filter(category__code=code).first()
            if source is None:
                raise CommandError(f"Leave category {code} has not been seeded.")
            category = source.category
            balance, _ = LeaveBalance.objects.get_or_create(
                user_id=user_id,
                category=category,
                year=year,
                defaults={"opening_balance": 0, "credited": 0, "used": 0, "closing_balance": 0},
            )
            cache[key] = balance
        return cache[key]
