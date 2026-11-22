"""JSON serialization contracts for employee audit metadata."""

from datetime import date

from modules.hr.services.employees import _audit_snapshot


def test_employee_audit_snapshot_serializes_dates_as_iso_strings():
    values = {"appointment_start_date": date(2023, 1, 1), "department": "Math"}

    assert _audit_snapshot(values) == {
        "appointment_start_date": "2023-01-01",
        "department": "Math",
    }
