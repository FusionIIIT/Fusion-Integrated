from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from fusion_auth.client import IamUnavailable
from modules.directory.contracts import get_users
from modules.elm.domain.policy import convert_vl_to_el
from modules.elm.models import LeaveBalance, LeaveBalanceEvent, LeavePolicy


class Command(BaseCommand):
    help = "Carry balances and convert unused VL at the end of a leave year."

    def add_arguments(self, parser):
        parser.add_argument("--year", required=True, type=int)

    @transaction.atomic
    def handle(self, *args, **options):
        year = options["year"]
        if year < 1900 or year >= 9999:
            raise CommandError("Year must be between 1900 and 9998.")

        accounts = list(
            LeaveBalance.objects.select_for_update().filter(year=year)
        )
        user_ids = sorted({account.user_id for account in accounts})
        try:
            employees = get_users(user_ids)
        except IamUnavailable as exc:
            raise CommandError(
                "Fusion employee directory is unavailable; no balances were changed."
            ) from exc

        policies = {
            policy.leave_type_code: policy
            for policy in LeavePolicy.objects.filter(is_active=True)
        }
        processed = 0
        for account in accounts:
            employee = employees.get(account.user_id)
            if employee is None:
                raise CommandError(
                    f"Could not resolve employee {account.user_id}; "
                    "no balances were changed."
                )
            if account.reserved_days:
                raise CommandError(
                    f"Employee {account.user_id} has pending reserved "
                    f"{account.leave_type_code} leave; resolve it before year-end."
                )

            policy = policies.get(account.leave_type_code)
            if policy is None:
                continue
            output_note = (
                f"Year-end output of {account.leave_type_code} for {year}"
            )
            if LeaveBalanceEvent.objects.filter(
                balance=account,
                event_type="YEAR_END",
                note=output_note,
            ).exists():
                continue

            remaining = account.available_days
            if remaining < 0:
                raise CommandError(
                    f"Employee {account.user_id} has a negative "
                    f"{account.leave_type_code} balance."
                )

            conversion = Decimal("0")
            if account.leave_type_code == "VL":
                conversion = convert_vl_to_el(remaining)
                account.used_days += remaining
                account.save(update_fields=("used_days", "updated_at"))

            next_code = (
                policy.conversion_target_code
                if account.leave_type_code == "VL"
                else account.leave_type_code
            )
            next_policy = policies.get(next_code)
            if next_policy is None:
                raise CommandError(
                    f"No active policy exists for converted leave type {next_code}."
                )

            opening = (
                remaining if policy.carries_forward
                else conversion if conversion
                else Decimal("0")
            )
            employee_kind = employee.kind.lower()
            eligible = (
                not next_policy.employee_kinds
                or employee_kind in next_policy.employee_kinds
            )
            entitlement_by_kind = (
                next_policy.annual_entitlement_by_kind or {}
            )
            annual_credit = (
                Decimal(str(entitlement_by_kind.get(
                    employee_kind, next_policy.annual_entitlement or 0
                )))
            ) if eligible else Decimal("0")
            if not eligible and opening == 0:
                LeaveBalanceEvent.objects.create(
                    balance=account,
                    event_type="YEAR_END",
                    amount=remaining,
                    note=output_note,
                )
                processed += 1
                continue

            target, created = LeaveBalance.objects.select_for_update().get_or_create(
                user_id=account.user_id,
                leave_type_code=next_code,
                year=year + 1,
                defaults={
                    "opening_balance": opening,
                    "annual_credit": annual_credit,
                },
            )
            if not created and opening:
                target.opening_balance += opening
                target.save(update_fields=("opening_balance", "updated_at"))

            if opening:
                LeaveBalanceEvent.objects.create(
                    balance=target,
                    event_type="CONVERSION" if conversion else "CREDIT",
                    amount=opening,
                    note=(
                        f"Year-end input of {account.leave_type_code} "
                        f"from {year}"
                    ),
                )
            LeaveBalanceEvent.objects.create(
                balance=account,
                event_type="YEAR_END",
                amount=remaining,
                note=output_note,
            )
            processed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {processed} annual balance accounts for {year}."
            )
        )
