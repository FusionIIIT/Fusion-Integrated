import pytest

from modules.elm.models import LeaveApplication

pytestmark = pytest.mark.django_db


def test_put_refused_and_unchanged(elm_client, elm_people):
    app = LeaveApplication.objects.create(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        num_days=1,
        state="Awaiting Unit Head Review",
    )
    response = elm_client(elm_people[0]).put(
        f"/api/v1/elm/applications/{app.id}/", {"remarks": "changed"}, format="json"
    )
    app.refresh_from_db()
    assert response.status_code in (404, 405)
    assert app.remarks == ""


def test_patch_refused_and_unchanged(elm_client, elm_people):
    app = LeaveApplication.objects.create(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        num_days=1,
        state="Awaiting Unit Head Review",
    )
    response = elm_client(elm_people[0]).patch(
        f"/api/v1/elm/applications/{app.id}/", {"remarks": "changed"}, format="json"
    )
    app.refresh_from_db()
    assert response.status_code in (404, 405)
    assert app.remarks == ""
