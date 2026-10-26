# Management command for year-end leave balance rollover (BR-EL-002..008)
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from modules.leave.domain.constants import (
    DEFAULT_ANNUAL_ENTITLEMENTS,
    LEAVE_TYPE_CL,
    LEAVE_TYPE_COL,
    LEAVE_TYPE_EL,
    LEAVE_TYPE_RH,
    LEAVE_TYPE_SCL,
    LEAVE_TYPE_VL,
)
from modules.leave.models import LeaveBalance


class Command(BaseCommand):
    help = (
        "Process annual rollover: lapse CL/RH/SCL, carry over EL/COL, convert VL to EL (2:1)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=date.today().year,
            help="Year to close (defaults to current year).",
        )
        parser.add_argument(
            "--next-year",
            type=int,
            default=None,
            help="Year to initialize (defaults to year + 1).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate rollover calculations without committing to the database.",
        )

    def handle(self, *args, **options):
        year = options["year"]
        next_year = options["next_year"] or (year + 1)
        dry_run = options["dry_run"]

        self.stdout.write(
            f"Processing leave rollover from year {year} to {next_year} (dry-run={dry_run})..."
        )

        user_ids = list(
            LeaveBalance.objects.filter(year=year).values_list("user_id", flat=True).distinct()
        )
        self.stdout.write(f"Found {len(user_ids)} employee accounts with balances for {year}.")

        with transaction.atomic():
            for uid in user_ids:
                balances = {
                    b.leave_type: b
                    for b in LeaveBalance.objects.filter(user_id=uid, year=year)
                }

                # Calculate remaining balances
                rem_cl = (
                    balances[LEAVE_TYPE_CL].available if LEAVE_TYPE_CL in balances else Decimal(0)
                )
                rem_rh = (
                    balances[LEAVE_TYPE_RH].available if LEAVE_TYPE_RH in balances else Decimal(0)
                )
                rem_scl = (
                    balances[LEAVE_TYPE_SCL].available if LEAVE_TYPE_SCL in balances else Decimal(0)
                )
                rem_el = (
                    balances[LEAVE_TYPE_EL].available if LEAVE_TYPE_EL in balances else Decimal(0)
                )
                rem_vl = (
                    balances[LEAVE_TYPE_VL].available if LEAVE_TYPE_VL in balances else Decimal(0)
                )
                rem_col = (
                    balances[LEAVE_TYPE_COL].available if LEAVE_TYPE_COL in balances else Decimal(0)
                )

                # Faculty VL to EL conversion at 2:1 ratio (BR-EL-007, BR-EL-008)
                vl_to_el = (rem_vl / Decimal("2")) if rem_vl > Decimal("0.00") else Decimal("0.00")

                # Next year entitlements
                # CL, RH, SCL lapse (no carryover)
                next_cl = DEFAULT_ANNUAL_ENTITLEMENTS[LEAVE_TYPE_CL]
                next_rh = DEFAULT_ANNUAL_ENTITLEMENTS[LEAVE_TYPE_RH]
                next_scl = DEFAULT_ANNUAL_ENTITLEMENTS[LEAVE_TYPE_SCL]

                # EL carries forward + converted VL
                base_el = DEFAULT_ANNUAL_ENTITLEMENTS[LEAVE_TYPE_EL]
                next_el = base_el + max(Decimal("0.00"), rem_el) + vl_to_el

                # COL carries forward
                base_col = DEFAULT_ANNUAL_ENTITLEMENTS[LEAVE_TYPE_COL]
                next_col = base_col + max(Decimal("0.00"), rem_col)

                # VL resets to standard 60 (VL itself does not carry forward)
                next_vl = DEFAULT_ANNUAL_ENTITLEMENTS[LEAVE_TYPE_VL]

                self.stdout.write(
                    f"User {uid}: CL lapsed={rem_cl}, RH lapsed={rem_rh}, SCL lapsed={rem_scl}, "
                    f"VL converted ({rem_vl}->{vl_to_el}), New EL={next_el}, New COL={next_col}"
                )

                if not dry_run:
                    allocations = [
                        (LEAVE_TYPE_CL, next_cl),
                        (LEAVE_TYPE_RH, next_rh),
                        (LEAVE_TYPE_SCL, next_scl),
                        (LEAVE_TYPE_EL, next_el),
                        (LEAVE_TYPE_VL, next_vl),
                        (LEAVE_TYPE_COL, next_col),
                    ]
                    for ltype, alloc in allocations:
                        LeaveBalance.objects.update_or_create(
                            user_id=uid,
                            leave_type=ltype,
                            year=next_year,
                            defaults={"allocated": alloc, "used": Decimal("0.00")},
                        )

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry run complete. No changes saved."))
            else:
                msg = f"Successfully processed rollover for {len(user_ids)} users to {next_year}."
                self.stdout.write(self.style.SUCCESS(msg))
