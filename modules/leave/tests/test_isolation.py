"""Person A never sees person B's leave, by list, by filter, by id, by queue or by export."""
import pytest

from modules.leave.tests.conftest import (
    FACULTY_CSE,
    FACULTY_CSE_2,
    HOD_CSE,
    HRADMIN,
    REGISTRAR,
    apply_payload,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def two_requests(configured, client_for):
    a = client_for(FACULTY_CSE).post("/api/v1/leave/requests", apply_payload(),
                                     format="json").json()
    b = client_for(FACULTY_CSE_2).post("/api/v1/leave/requests",
                                       apply_payload(start="2026-03-11"), format="json").json()
    return a, b


def test_list_shows_only_own(two_requests, client_for):
    a, _b = two_requests
    rows = client_for(FACULTY_CSE).get("/api/v1/leave/requests").json()
    assert [r["id"] for r in rows] == [a["id"]]
    rows = client_for(FACULTY_CSE).get("/api/v1/leave/requests?status=awaiting_unit_head").json()
    assert [r["id"] for r in rows] == [a["id"]]


def test_detail_and_export_of_another_are_404(two_requests, client_for):
    _, b = two_requests
    c = client_for(FACULTY_CSE)
    assert c.get(f"/api/v1/leave/requests/{b['id']}").status_code == 404
    assert c.get(f"/api/v1/leave/requests/{b['id']}/document").status_code == 404


def test_ledger_is_own(two_requests, client_for):
    rows = client_for(FACULTY_CSE).get("/api/v1/leave/ledger").json()["results"]
    assert rows and all(r["note"].startswith("Annual") for r in rows)
    from modules.leave.models import LedgerEntry

    ids = {r["id"] for r in rows}
    assert ids == set(LedgerEntry.objects.filter(user_id=FACULTY_CSE).values_list("pk",
                                                                                   flat=True))


def test_unit_head_sees_their_unit_and_nobody_elses(two_requests, client_for):
    a, b = two_requests
    hod = client_for(HOD_CSE)
    assert {t["request"]["id"] for t in hod.get("/api/v1/leave/queue").json()} == {a["id"],
                                                                                  b["id"]}
    reg = client_for(REGISTRAR)
    assert reg.get("/api/v1/leave/queue").json() == []
    assert reg.get(f"/api/v1/leave/requests/{a['id']}").status_code == 404


def test_substitute_sees_only_the_request_they_cover(configured, client_for):
    r = client_for(FACULTY_CSE).post("/api/v1/leave/requests",
                                     apply_payload(substitute_user_id=FACULTY_CSE_2),
                                     format="json").json()
    other = client_for(FACULTY_CSE).post("/api/v1/leave/requests",
                                         apply_payload(start="2026-03-12"),
                                         format="json").json()
    sub = client_for(FACULTY_CSE_2)
    assert [s["request"]["id"] for s in sub.get("/api/v1/leave/substitutions").json()] == [r["id"]]
    assert sub.get(f"/api/v1/leave/requests/{r['id']}").status_code == 200
    assert sub.get(f"/api/v1/leave/requests/{other['id']}").status_code == 404


def test_employee_search_reveals_names_not_leave(configured, client_for):
    rows = client_for(FACULTY_CSE).get("/api/v1/leave/employees?q=Person").json()
    assert rows and FACULTY_CSE not in {r["user_id"] for r in rows}
    assert set(rows[0]) == {"user_id", "display_name", "username", "kind", "department"}


def test_records_holder_sees_any_employee(two_requests, client_for):
    _, b = two_requests
    r = client_for(HRADMIN).get(f"/api/v1/leave/admin/records?user_id={FACULTY_CSE_2}")
    assert [x["id"] for x in r.json()["requests"]] == [b["id"]]
