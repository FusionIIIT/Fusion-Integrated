from decimal import Decimal

from modules.elm.year_end import next_balances


def test_staff_closing():
    original = {
        "CL": Decimal("3"),
        "RH": Decimal("1"),
        "SCL": Decimal("4"),
        "EL": Decimal("7.5"),
        "COL": Decimal("2"),
    }
    result = next_balances("staff", original)
    assert result == {
        "CL": Decimal("8"),
        "RH": Decimal("2"),
        "SCL": Decimal("15"),
        "EL": Decimal("37.5"),
        "COL": Decimal("22"),
    }
    assert original == {
        "CL": Decimal("3"),
        "RH": Decimal("1"),
        "SCL": Decimal("4"),
        "EL": Decimal("7.5"),
        "COL": Decimal("2"),
    }


def test_faculty_closing():
    original = {
        "CL": Decimal("3"),
        "RH": Decimal("1"),
        "SCL": Decimal("4"),
        "EL": Decimal("7.5"),
        "COL": Decimal("2"),
        "VL": Decimal("5"),
    }
    result = next_balances("faculty", original)
    assert result == {
        "CL": Decimal("8"),
        "RH": Decimal("2"),
        "SCL": Decimal("15"),
        "EL": Decimal("10"),
        "COL": Decimal("22"),
        "VL": Decimal("60"),
    }
    assert original == {
        "CL": Decimal("3"),
        "RH": Decimal("1"),
        "SCL": Decimal("4"),
        "EL": Decimal("7.5"),
        "COL": Decimal("2"),
        "VL": Decimal("5"),
    }
