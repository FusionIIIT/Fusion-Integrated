import datetime as dt
from decimal import Decimal

import pytest

from modules.directory.models import UserRef
from modules.elm import services
from modules.elm.models import LeaveBalance

D = dt.date


@pytest.fixture
def person(db):
    return UserRef.objects.create(user_id=9001, username="t.user",
                                  display_name="Test User", kind="faculty")


def test_half_day_cl_costs_half_a_day(person):
    app = services.submit_application(person, "CL", D(2026, 3, 2), D(2026, 3, 2), "FIRST")
    assert app.days == Decimal("0.5")
    services.approve_application(app)
    bal = LeaveBalance.objects.get(user=person, year=2026, leave_type="CL")
    assert bal.used == Decimal("0.5")


def test_first_and_second_half_same_day_allowed(person):
    services.submit_application(person, "CL", D(2026, 3, 2), D(2026, 3, 2), "FIRST")
    services.submit_application(person, "CL", D(2026, 3, 2), D(2026, 3, 2), "SECOND")


def test_same_half_same_day_rejected(person):
    services.submit_application(person, "CL", D(2026, 3, 2), D(2026, 3, 2), "FIRST")
    with pytest.raises(ValueError):
        services.submit_application(person, "CL", D(2026, 3, 2), D(2026, 3, 2), "FIRST")


def test_cl_over_eight_days_rejected(person):
    with pytest.raises(ValueError):
        services.submit_application(person, "CL", D(2026, 3, 2), D(2026, 3, 10))


def test_rh_must_be_on_a_published_date(person):
    with pytest.raises(ValueError):
        services.submit_application(person, "RH", D(2026, 1, 26), D(2026, 1, 26))


def test_scl_needs_admissible_purpose(person):
    with pytest.raises(ValueError):
        services.submit_application(person, "SCL", D(2026, 4, 1), D(2026, 4, 2))


def test_year_end_lapse_records_and_is_idempotent(person):
    app = services.submit_application(person, "CL", D(2026, 3, 2), D(2026, 3, 3))
    services.approve_application(app)
    services.run_year_end_lapse(2026)
    bal = LeaveBalance.objects.get(user=person, year=2026, leave_type="CL")
    assert bal.lapsed == Decimal("6")
    services.run_year_end_lapse(2026)
    bal.refresh_from_db()
    assert bal.lapsed == Decimal("6")
