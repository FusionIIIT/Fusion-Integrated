from datetime import date

import pytest

from modules.elm.models import AuthorityRoute, CalendarDay, LeaveEvent
from modules.elm.tests.test_api import api_as
from modules.elm.tests.test_submission import seed

pytestmark = pytest.mark.django_db


def test_calendar_publication_replaces_only_selected_kind(stub_iam):
    seed()
    old = CalendarDay.objects.create(
        date=date(2026, 11, 1), kind="RH", published=True, source="old"
    )
    CalendarDay.objects.create(
        date=date(2026, 11, 1), kind="CLOSED", published=True, source="academic"
    )
    CalendarDay.objects.create(
        date=date(2026, 11, 1), kind="VACATION", published=True, source="academic"
    )

    client = api_as(stub_iam, 201, ("elm.leave_policies.manage", "elm.leave_types.view"))
    response = client.post(
        "/api/v1/elm/calendar/publish/",
        {"year": 2026, "kind": "RH", "dates": ["2026-11-02"], "source": "Replacement"},
        format="json",
    )

    assert response.status_code == 200
    old.refresh_from_db()
    assert not old.published

    new_rh = CalendarDay.objects.get(date=date(2026, 11, 2), kind="RH", source="Replacement")
    assert new_rh.published

    closed = CalendarDay.objects.get(kind="CLOSED")
    vacation = CalendarDay.objects.get(kind="VACATION")
    assert closed.published and vacation.published

    leave_event = LeaveEvent.objects.filter(action="CALENDAR_PUBLISHED", actor=201).first()
    assert leave_event and leave_event.details["kind"] == "RH"


def test_calendar_publication_rejects_bad_payload_and_employee(stub_iam):
    seed()
    old = CalendarDay.objects.create(
        date=date(2026, 11, 1), kind="RH", published=True, source="old"
    )

    client = api_as(stub_iam, 201, ("elm.leave_policies.manage", "elm.leave_types.view"))
    # Invalid source
    response = client.post(
        "/api/v1/elm/calendar/publish/",
        {"year": 2026, "kind": "RH", "dates": ["2027-01-01"], "source": "x"},
        format="json",
    )
    assert response.status_code == 400
    old.refresh_from_db()
    assert old.published

    # Empty dates list
    response = client.post(
        "/api/v1/elm/calendar/publish/",
        {"year": 2026, "kind": "VACATION", "dates": [], "source": "academic"},
        format="json",
    )
    assert response.status_code == 400
    old.refresh_from_db()
    assert old.published

    # Employee without permissions
    employee_client = api_as(stub_iam, 101, ("elm.leave_types.view",))
    response = employee_client.post(
        "/api/v1/elm/calendar/publish/",
        {"year": 2026, "kind": "RH", "dates": ["2026-11-02"], "source": "Replacement"},
        format="json",
    )
    assert response.status_code == 403
    old.refresh_from_db()
    assert old.published


def test_hierarchy_changes_require_admin_and_are_audited(stub_iam):
    seed()

    client = api_as(stub_iam, 101, ("elm.leave_types.view",))
    response = client.post(
        "/api/v1/elm/routes/",
        {
            "employee": 101,
            "unit": "CSE",
            "leave_category": "EL",
            "unit_head": 201,
            "higher_authorities": [301],
        },
        format="json",
    )
    assert response.status_code == 403

    admin_client = api_as(stub_iam, 201, ("elm.leave_policies.manage",))
    response = admin_client.post(
        "/api/v1/elm/routes/",
        {
            "employee": 101,
            "unit": "CSE",
            "leave_category": "EL",
            "unit_head": 201,
            "higher_authorities": [301],
        },
        format="json",
    )
    assert response.status_code == 201

    route = AuthorityRoute.objects.get(employee=101, leave_category="EL")
    assert route.leave_category == "EL"

    leave_event = LeaveEvent.objects.filter(action="CONFIGURATION_CHANGED", actor=201).first()
    assert leave_event and leave_event.details["operation"] == "CREATE"
