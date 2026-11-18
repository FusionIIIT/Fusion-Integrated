"""Idempotent annual entitlement rollover and VL-to-EL conversion."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.elm.domain.year_end import vl_to_el
from modules.elm.models import LedgerEntry, YearEndRun
from modules.elm.services import ledger


def _process_employee(employee, year: int) -> dict:
    user_id = employee.user_id
    result = {"lapsed": {}, "vl_converted": Decimal("0"), "credits_created": 0}
    for category in ("CL", "RH", "SCL"):
        balance = ledger.balance(user_id, category, year)
        if balance > 0:
            LedgerEntry.objects.get_or_create(
                user_id=user_id,
                category=category,
                year=year,
                entry_type="year_end_lapse",
                reference=f"year-end-{year}-{category}",
                defaults={
                    "delta": -balance,
                    "note": "Unused balance lapsed at year end",
                },
            )
            result["lapsed"][category] = balance

    # EL and COL are carried forward; annual credits are separate ledger rows.
    for category in ("EL", "COL"):
        carry = ledger.balance(user_id, category, year)
        if carry > 0:
            LedgerEntry.objects.get_or_create(
                user_id=user_id,
                category=category,
                year=year + 1,
                entry_type="adjustment",
                reference=f"year-end-{year}-{category}-carry",
                defaults={
                    "delta": carry,
                    "note": f"Unused {category} carried forward",
                },
            )

    vl_balance = ledger.balance(user_id, "VL", year)
    if vl_balance > 0:
        converted = vl_to_el(vl_balance)
        if converted > 0:
            LedgerEntry.objects.get_or_create(
                user_id=user_id,
                category="VL",
                year=year,
                entry_type="vl_conversion",
                reference=f"year-end-{year}-vl-to-el-out",
                defaults={"delta": -vl_balance, "note": "VL converted to EL at 2:1"},
            )
            LedgerEntry.objects.get_or_create(
                user_id=user_id,
                category="EL",
                year=year + 1,
                entry_type="vl_conversion",
                reference=f"year-end-{year}-vl-to-el-in",
                defaults={"delta": converted, "note": "EL credited from VL at 2:1"},
            )
            result["vl_converted"] = converted

    result["credits_created"] = ledger.ensure_annual_credits(
        user_id, year + 1, kind=employee.kind
    )
    return result


@transaction.atomic
def process(year: int | None = None) -> dict:
    year = year or timezone.localdate().year - 1
    run, created = YearEndRun.objects.get_or_create(
        year=year, defaults={"status": "running"}
    )
    if not created and run.status == "completed":
        return run.report

    report = {
        "year": year,
        "employees": 0,
        "lapsed": {},
        "vl_converted": "0",
        "credits_created": 0,
        "exceptions": [],
    }
    employees = directory.get_employees()
    for employee in employees:
        report["employees"] += 1
        try:
            # A failed employee rolls back to a savepoint; other employees can
            # still be processed and the failure is retained in the run report.
            with transaction.atomic():
                employee_result = _process_employee(employee, year)
        except Exception as exc:  # noqa: BLE001 - persisted in YearEndRun exceptions report
            report["exceptions"].append({
                "user_id": employee.user_id,
                "error_type": exc.__class__.__name__,
                "message": str(exc),
            })
            continue
        for category, amount in employee_result["lapsed"].items():
            current = Decimal(report["lapsed"].get(category, "0"))
            report["lapsed"][category] = str(current + amount)
        report["vl_converted"] = str(
            Decimal(report["vl_converted"]) + employee_result["vl_converted"]
        )
        report["credits_created"] += employee_result["credits_created"]

    run.status = "failed" if report["exceptions"] else "completed"
    run.report = report
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "report", "finished_at", "updated_at"])
    return report
