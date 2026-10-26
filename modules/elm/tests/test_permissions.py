import pytest

from modules.elm.models import LeaveApplication

pytestmark = pytest.mark.django_db


def test_unrelated_employee_cannot_see_or_act(elm_client, elm_people):
    app = LeaveApplication.objects.create(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        num_days=1,
        substitute=elm_people[2],
        unit_head=elm_people[1],
        state="Awaiting Unit Head Review",
    )
    client = elm_client(elm_people[5])
    assert client.get(f"/api/v1/elm/applications/{app.id}/").status_code == 404
    assert (
        client.post(
            f"/api/v1/elm/applications/{app.id}/substitute-response/", {"accept": True}
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/elm/applications/{app.id}/unit-head-review/", {"decision": "Approve"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/elm/applications/{app.id}/final-decision/", {"decision": "Approve"}
        ).status_code
        == 404
    )
    assert all(
        row["id"] != str(app.id)
        for row in client.get("/api/v1/elm/applications/").json()["results"]
    )


def test_applicant_cannot_approve_as_unit_head(elm_client, elm_people):
    app = LeaveApplication.objects.create(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        num_days=1,
        unit_head=elm_people[1],
        state="Awaiting Unit Head Review",
    )
    assert (
        elm_client(elm_people[0])
        .post(f"/api/v1/elm/applications/{app.id}/unit-head-review/", {"decision": "Approve"})
        .status_code
        == 403
    )
