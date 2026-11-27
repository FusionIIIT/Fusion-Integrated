"""Tests for year-end leave balance processing (BR-EL-002..009, EL-UC-020)."""

import threading
from decimal import Decimal

import pytest
from django.core.management import call_command

from modules.leave.models import LeaveBalance, LeaveLedgerEntry, LeaveType
from modules.leave.services.year_end import process_year_end


@pytest.fixture
def leave_types(db):
    types = {}
    for code, name, carries, lapses in [
        ("CL", "Casual Leave", False, True),
        ("RH", "Restricted Holiday", False, True),
        ("SCL", "Special Casual Leave", False, True),
        ("EL", "Earned Leave", True, False),
        ("COL", "Commuted Leave", True, False),
        ("VL", "Vacation Leave", False, True),
    ]:
        lt, _ = LeaveType.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "carries_forward": carries,
                "lapses_at_year_end": lapses,
            },
        )
        types[code] = lt
    return types


@pytest.mark.django_db
def test_year_end_lapses_cl_rh_scl(leave_types):
    """CL, RH, and SCL lapse unused days at year end (BR-EL-002, 003, 004)."""
    user_id = 301
    from_year = 2026
    to_year = 2027

    b_cl = LeaveBalance.objects.create(
        user_id=user_id,
        leave_type=leave_types["CL"],
        year=from_year,
        credited_days=Decimal("8.0"),
        available_days=Decimal("3.5"),
    )
    b_rh = LeaveBalance.objects.create(
        user_id=user_id,
        leave_type=leave_types["RH"],
        year=from_year,
        credited_days=Decimal("2.0"),
        available_days=Decimal("1.0"),
    )
    b_scl = LeaveBalance.objects.create(
        user_id=user_id,
        leave_type=leave_types["SCL"],
        year=from_year,
        credited_days=Decimal("15.0"),
        available_days=Decimal("10.0"),
    )

    report = process_year_end(from_year=from_year, to_year=to_year, user_ids=[user_id])

    assert report.processed_users == 1
    assert report.total_lapsed["CL"] == Decimal("3.5")
    assert report.total_lapsed["RH"] == Decimal("1.0")
    assert report.total_lapsed["SCL"] == Decimal("10.0")

    # Verify balances were reset to 0.0
    b_cl.refresh_from_db()
    b_rh.refresh_from_db()
    b_scl.refresh_from_db()
    assert b_cl.available_days == Decimal("0.0")
    assert b_rh.available_days == Decimal("0.0")
    assert b_scl.available_days == Decimal("0.0")

    # Verify audit ledger entries
    cl_entries = LeaveLedgerEntry.objects.filter(balance=b_cl, entry_type="lapse")
    assert cl_entries.count() == 1
    entry = cl_entries.first()
    assert entry.amount == Decimal("-3.5")
    assert entry.balance_after == Decimal("0.0")
    assert entry.reference_type == "year_end"
    assert entry.reference_id == from_year


@pytest.mark.django_db
def test_faculty_vl_to_el_conversion_including_fractions(leave_types):
    """Unused faculty VL converts to EL at 2:1 ratio, preserving fractions (BR-EL-007, 008)."""
    user_id = 302
    from_year = 2026
    to_year = 2027

    b_vl = LeaveBalance.objects.create(
        user_id=user_id,
        leave_type=leave_types["VL"],
        year=from_year,
        credited_days=Decimal("60.0"),
        available_days=Decimal("15.0"),  # 15 / 2 = 7.5 EL
    )

    report = process_year_end(from_year=from_year, to_year=to_year, user_ids=[user_id])

    assert report.processed_users == 1
    assert report.total_converted["VL_TO_EL"] == Decimal("7.5")

    # from_year VL is reduced to 0.0
    b_vl.refresh_from_db()
    assert b_vl.available_days == Decimal("0.0")

    # to_year EL balance created with 7.5 days
    el_to_year = LeaveBalance.objects.get(
        user_id=user_id, leave_type=leave_types["EL"], year=to_year
    )
    assert el_to_year.available_days == Decimal("7.5")
    assert el_to_year.credited_days == Decimal("7.5")

    # Verify ledger entries on both sides
    vl_entry = LeaveLedgerEntry.objects.get(balance=b_vl, entry_type="conversion")
    assert vl_entry.amount == Decimal("-15.0")
    assert vl_entry.balance_after == Decimal("0.0")

    el_entry = LeaveLedgerEntry.objects.get(balance=el_to_year, entry_type="conversion")
    assert el_entry.amount == Decimal("7.5")
    assert el_entry.balance_after == Decimal("7.5")


@pytest.mark.django_db
def test_el_and_col_carry_forward_and_ceilings(leave_types):
    """EL and COL carry forward, respecting configured ceilings (BR-EL-005, 009)."""
    user_id = 303
    from_year = 2026
    to_year = 2027

    b_el = LeaveBalance.objects.create(
        user_id=user_id,
        leave_type=leave_types["EL"],
        year=from_year,
        credited_days=Decimal("30.0"),
        available_days=Decimal("25.0"),
    )
    b_col = LeaveBalance.objects.create(
        user_id=user_id,
        leave_type=leave_types["COL"],
        year=from_year,
        credited_days=Decimal("20.0"),
        available_days=Decimal("18.0"),
    )

    # Test with an EL ceiling of 20.0 days (so 25.0 -> 20.0 carried, 5.0 excess)
    report = process_year_end(
        from_year=from_year,
        to_year=to_year,
        user_ids=[user_id],
        ceilings={"EL": Decimal("20.0")},
    )

    assert report.processed_users == 1
    assert report.total_carried_forward["EL"] == Decimal("20.0")
    assert report.total_carried_forward["COL"] == Decimal("18.0")

    # Verify to_year balances
    el_2027 = LeaveBalance.objects.get(user_id=user_id, leave_type=leave_types["EL"], year=to_year)
    assert el_2027.available_days == Decimal("20.0")

    col_2027 = LeaveBalance.objects.get(
        user_id=user_id, leave_type=leave_types["COL"], year=to_year
    )
    assert col_2027.available_days == Decimal("18.0")

    # Verify from_year balances were transferred
    b_el.refresh_from_db()
    b_col.refresh_from_db()
    assert b_el.available_days == Decimal("0.0")
    assert b_col.available_days == Decimal("0.0")


@pytest.mark.django_db
def test_zero_balances_safe_handling(leave_types):
    """Zero balance accounts are processed safely without negative balances."""
    user_id = 304
    from_year = 2026
    to_year = 2027

    for code in ["CL", "EL", "VL"]:
        LeaveBalance.objects.create(
            user_id=user_id,
            leave_type=leave_types[code],
            year=from_year,
            credited_days=Decimal("10.0"),
            available_days=Decimal("0.0"),
        )

    report = process_year_end(from_year=from_year, to_year=to_year, user_ids=[user_id])
    assert report.processed_users == 1
    assert report.total_lapsed["CL"] == Decimal("0.0")
    assert report.total_converted.get("VL_TO_EL", Decimal("0.0")) == Decimal("0.0")
    assert report.total_carried_forward.get("EL", Decimal("0.0")) == Decimal("0.0")


@pytest.mark.django_db
def test_idempotent_duplicate_execution(leave_types):
    """Re-running year-end processing does not duplicate adjustments."""
    user_id = 305
    from_year = 2026
    to_year = 2027

    LeaveBalance.objects.create(
        user_id=user_id,
        leave_type=leave_types["CL"],
        year=from_year,
        credited_days=Decimal("8.0"),
        available_days=Decimal("4.0"),
    )
    LeaveBalance.objects.create(
        user_id=user_id,
        leave_type=leave_types["EL"],
        year=from_year,
        credited_days=Decimal("30.0"),
        available_days=Decimal("15.0"),
    )

    # First run
    report1 = process_year_end(from_year=from_year, to_year=to_year, user_ids=[user_id])
    assert report1.processed_users == 1
    assert report1.skipped_users == 0

    el_2027 = LeaveBalance.objects.get(user_id=user_id, leave_type=leave_types["EL"], year=to_year)
    assert el_2027.available_days == Decimal("15.0")
    ledger_count_1 = LeaveLedgerEntry.objects.count()

    # Second run (exact same parameters)
    report2 = process_year_end(from_year=from_year, to_year=to_year, user_ids=[user_id])
    assert report2.processed_users == 0
    assert report2.skipped_users == 1

    # Ledger and balances must remain identical
    el_2027.refresh_from_db()
    assert el_2027.available_days == Decimal("15.0")
    assert LeaveLedgerEntry.objects.count() == ledger_count_1


@pytest.mark.django_db
def test_dry_run_rolls_back_changes(leave_types):
    """Dry-run rehearses processing without committing any database modifications."""
    user_id = 306
    from_year = 2026
    to_year = 2027

    b_cl = LeaveBalance.objects.create(
        user_id=user_id,
        leave_type=leave_types["CL"],
        year=from_year,
        credited_days=Decimal("8.0"),
        available_days=Decimal("5.0"),
    )

    report = process_year_end(
        from_year=from_year, to_year=to_year, user_ids=[user_id], dry_run=True
    )

    assert report.processed_users == 1
    assert report.total_lapsed["CL"] == Decimal("5.0")

    # DB remains unchanged
    b_cl.refresh_from_db()
    assert b_cl.available_days == Decimal("5.0")
    assert LeaveLedgerEntry.objects.filter(balance=b_cl).count() == 0


@pytest.mark.django_db
def test_missing_policy_or_user_configuration(leave_types):
    """Missing user balance records or leave types report exceptions cleanly."""
    report = process_year_end(from_year=2026, to_year=2027, user_ids=[99999])
    assert len(report.exceptions) == 1
    assert "No balances found for user 99999" in report.exceptions[0]


@pytest.mark.django_db(transaction=True)
def test_concurrent_year_end_execution_protection(leave_types):
    """Concurrent executions on the same employee are serialized and idempotent."""
    user_id = 307
    from_year = 2026
    to_year = 2027

    LeaveBalance.objects.create(
        user_id=user_id,
        leave_type=leave_types["EL"],
        year=from_year,
        credited_days=Decimal("30.0"),
        available_days=Decimal("20.0"),
    )

    barrier = threading.Barrier(2)
    results = []

    def run_worker():
        from django.db import connection

        try:
            barrier.wait()
            res = process_year_end(from_year=from_year, to_year=to_year, user_ids=[user_id])
            results.append(res)
        finally:
            connection.close()

    t1 = threading.Thread(target=run_worker)
    t2 = threading.Thread(target=run_worker)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Exactly one thread must process the user; the other must skip
    processed_count = sum(r.processed_users for r in results)
    skipped_count = sum(r.skipped_users for r in results)
    assert processed_count == 1
    assert skipped_count == 1

    # Carry forward must not be doubled (must be exactly 20.0, not 40.0)
    el_2027 = LeaveBalance.objects.get(user_id=user_id, leave_type=leave_types["EL"], year=to_year)
    assert el_2027.available_days == Decimal("20.0")


@pytest.mark.django_db
def test_leave_year_end_management_command(leave_types, capsys):
    """Test management command invocation and output formatting."""
    user_id = 308
    from_year = 2026
    to_year = 2027

    LeaveBalance.objects.create(
        user_id=user_id,
        leave_type=leave_types["CL"],
        year=from_year,
        credited_days=Decimal("8.0"),
        available_days=Decimal("3.0"),
    )

    # Test dry run
    call_command(
        "leave_year_end",
        year=from_year,
        to_year=to_year,
        user_id=user_id,
        dry_run=True,
    )
    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out
    assert "Processed employees: 1" in captured.out

    # Test real run
    call_command(
        "leave_year_end",
        year=from_year,
        to_year=to_year,
        user_id=user_id,
    )
    captured = capsys.readouterr()
    assert "Year-end processing completed successfully." in captured.out

    # Re-run should report skipped
    call_command(
        "leave_year_end",
        year=from_year,
        to_year=to_year,
        user_id=user_id,
    )
    captured = capsys.readouterr()
    assert "Skipped (already closed): 1" in captured.out
