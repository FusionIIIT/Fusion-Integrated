from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import Account, Application, EmployeeConfiguration

pytestmark = pytest.mark.django_db
BASE = "/api/v1/elm/"


def client(
    stub_iam, *, user_id=1, role="staff", permissions=("elm.application.self",), modules=("elm",)
):
    stub_iam(
        make_session(
            user_id=user_id,
            kind="staff",
            roles=(role,),
            active_role=role,
            modules=modules,
            permissions=permissions,
        )
    )
    result = APIClient()
    result.credentials(HTTP_AUTHORIZATION="Token test-elm")
    return result


def test_employee_configuration_upsert_can_edit_existing_employee(elm, stub_iam):
    c = client(
        stub_iam, user_id=7, role="Leave Administrator", permissions=("elm.configuration.manage",)
    )
    config = EmployeeConfiguration.objects.get(user_id=1)
    values = {
        "user_id": 1,
        "unit": "Updated unit",
        "designation": "Employee",
        "coverage_required": False,
        "eligible_categories": config.eligible_categories,
        "routes": config.routes,
    }
    response = c.put(BASE + "configuration/", {"employee": values}, format="json")
    assert response.status_code == 204, response.content
    assert EmployeeConfiguration.objects.get(user_id=1).unit == "Updated unit"


def test_configuration_only_role_can_load_employee_picker(elm, stub_iam):
    c = client(
        stub_iam, user_id=7, role="Leave Administrator", permissions=("elm.configuration.manage",)
    )
    response = c.get(BASE + "employees/")
    assert response.status_code == 200, response.content
    assert len(response.json()) == 7


def test_own_history_filter_is_applied_before_pagination(elm, stub_iam):
    owned = elm["submit"]()
    foreign = Application.objects.create(
        user_id=4,
        category="CL",
        start_date=date(2026, 11, 3),
        end_date=date(2026, 11, 3),
        effective_end_date=date(2026, 11, 3),
        reason="Foreign",
    )
    from modules.elm.models import WorkflowTask

    WorkflowTask.objects.create(application=foreign, user_id=1, role="staff", stage="substitute")
    c = client(stub_iam, permissions=("elm.application.self", "elm.task.act"))
    response = c.get(BASE + "applications/?scope=mine")
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [owned.pk]


@pytest.mark.parametrize(
    "payload",
    [
        {
            "category": "CL",
            "start_date": "2026-11-03",
            "end_date": "2026-11-02",
            "reason": "Bad dates",
        },
        {
            "category": "EL",
            "start_date": "2026-11-02",
            "end_date": "2026-11-02",
            "half": "first",
            "reason": "Bad half",
        },
        {
            "category": "CL",
            "start_date": "2026-11-02",
            "end_date": "2026-11-02",
            "reason": "No details",
            "station_leave": True,
        },
    ],
)
def test_invalid_application_returns_controlled_error_without_writes(elm, stub_iam, payload):
    response = client(stub_iam).post(BASE + "applications/", payload, format="json")
    assert response.status_code in (400, 422), response.content
    assert "error" in response.json()
    assert not Application.objects.exists()
    assert not Account.objects.exists()


def test_api_approval_uses_role_and_prevents_replay(elm, stub_iam):
    app = elm["submit"]()
    c = client(stub_iam, user_id=2, role="Unit Head", permissions=("elm.task.act",))
    response = c.post(
        BASE + f"applications/{app.pk}/actions/",
        {"action": "approve", "revision": 1},
        format="json",
    )
    assert response.status_code == 200, response.content
    assert response.json()["status"] == "approved"
    repeat = c.post(
        BASE + f"applications/{app.pk}/actions/",
        {"action": "approve", "revision": 1},
        format="json",
    )
    assert repeat.status_code == 409


def test_foreign_application_is_404_and_module_is_required(elm, stub_iam):
    app = elm["submit"]()
    c = client(stub_iam, user_id=4)
    assert c.get(BASE + f"applications/{app.pk}/").status_code == 404
    c = client(stub_iam, modules=())
    assert c.get(BASE + "applications/").status_code == 403


def test_submitted_details_cannot_be_modified_in_place(elm, stub_iam):
    app = elm["submit"]()
    c = client(stub_iam)
    response = c.patch(BASE + f"applications/{app.pk}/", {"reason": "Changed"}, format="json")
    assert response.status_code == 405
    app.refresh_from_db()
    assert app.reason == "Leave required"


def test_export_is_downloadable_by_owner_but_not_another_employee(elm, stub_iam):
    app = elm["submit"]()
    c = client(stub_iam)
    response = c.get(BASE + f"applications/{app.pk}/export/")
    assert response.status_code == 200
    assert f"Employee Leave Application #{app.pk}" in response.content.decode()
    assert "attachment" in response["Content-Disposition"]
    c = client(stub_iam, user_id=4)
    assert c.get(BASE + f"applications/{app.pk}/export/").status_code == 404
