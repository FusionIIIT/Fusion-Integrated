from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from modules.elm.domain import (
    half_days_overlap, leave_days, validate_balance, validate_rh_date,
    validate_scl, year_end_lapse)
from modules.elm.models import (
    LeaveApplication, LeaveBalance, LeaveTransaction, RestrictedHoliday)

from django.db import transaction, IntegrityError
from modules.elm.models import LeaveBalance, RestrictedHoliday, LeaveApplication, LeaveTransaction, ANNUAL_ENTITLEMENT
from modules.elm.domain import leave_days, half_days_overlap, validate_balance, validate_rh_date, validate_scl, year_end_lapse

def ensure_balances(user, year):
    balances = []
    for leave_type in ANNUAL_ENTITLEMENT:
        balance, created = LeaveBalance.objects.get_or_create(
            user=user,
            year=year,
            leave_type=leave_type,
            defaults={'entitled': ANNUAL_ENTITLEMENT[leave_type]}
        )
        balances.append(balance)
    return balances

def submit_application(user, leave_type, start_date, end_date, half_day="NONE",
                       special_purpose="", special_purpose_admissible=False):
    with transaction.atomic():
        days = leave_days(start_date, end_date, half_day)
        balances = ensure_balances(user, start_date.year)
        balance = next((b for b in balances if b.leave_type == leave_type), None)
        if balance is None:
            raise ValueError("Unknown leave type")

        pending = LeaveApplication.objects.filter(
            user=user, leave_type=leave_type, status="PENDING",
            start_date__year=start_date.year,
        ).aggregate(total=Sum("days"))["total"] or Decimal("0")
        validate_balance(days, balance.entitled, balance.used + pending)

        if leave_type == "RH":
            published = list(RestrictedHoliday.objects.filter(
                year=start_date.year, is_published=True,
            ).values_list("date", flat=True))
            for day in (start_date, end_date):
                validate_rh_date(day, published)

        if leave_type == "SCL":
            used_scl = LeaveApplication.objects.filter(
                user=user, leave_type="SCL",
                status__in=["PENDING", "APPROVED"],
                start_date__year=start_date.year,
            ).aggregate(total=Sum("days"))["total"] or Decimal("0")
            validate_scl(days, used_scl, special_purpose_admissible)

        for other in LeaveApplication.objects.filter(
                user=user, status__in=["PENDING", "APPROVED"],
                start_date__lte=end_date, end_date__gte=start_date):
            if half_days_overlap(start_date, end_date, half_day,
                                 other.start_date, other.end_date, other.half_day):
                raise ValueError("Overlaps with an existing application")

        return LeaveApplication.objects.create(
            user=user, leave_type=leave_type, start_date=start_date,
            end_date=end_date, half_day=half_day, days=days,
            special_purpose=special_purpose,
            special_purpose_admissible=special_purpose_admissible,
        )

def approve_application(application):
    with transaction.atomic():
        balance = LeaveBalance.objects.get(
            user=application.user,
            year=application.start_date.year,
            leave_type=application.leave_type
        )

        if application.status != 'PENDING':
            raise ValueError("Application is not pending")

        balance.used += application.days
        balance.save()

        LeaveTransaction.objects.create(
            balance=balance,
            application=application,
            kind='DEDUCT',
            days=application.days
        )

        application.status = 'APPROVED'
        application.save()

def run_year_end_lapse(year):
    with transaction.atomic():
        for leave_type in ['CL', 'RH']:
            balances = LeaveBalance.objects.filter(
                user__isnull=False,
                year=year,
                leave_type=leave_type
            )

            for balance in balances:
                lapse = year_end_lapse(balance.entitled, balance.used) - balance.lapsed
                if lapse > 0:
                    balance.lapsed += lapse
                    balance.save()

                    LeaveTransaction.objects.create(
                        balance=balance,
                        kind='LAPSE',
                        days=lapse
                    )
