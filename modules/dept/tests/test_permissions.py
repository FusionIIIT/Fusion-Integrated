import pytest
from django.db import connection
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import IamUnavailable
from fusion_auth.client import UserRef as IamUserRef
from modules.dept.api.views import DeptView
from modules.dept.models import Announcement, Department
from modules.directory.models import UserRef

pytestmark = pytest.mark.django_db


def test_dept_reads_and_writes_use_separate_throttle_scopes():
    view = DeptView()
    for method, expected in (("GET", "dept_read"), ("POST", "dept_write")):
        view.request = type("Request", (), {"method": method})()
        view.get_throttles()
        assert view.throttle_scope == expected


def auth(
    stub_iam,
    *,
    modules,
    permissions,
    kind="student",
    active_role="student",
    assignments=(),
    department="Computer Science",
):
    stub_iam(
        make_session(
            user_id=7,
            modules=modules,
            permissions=permissions,
            kind=kind,
            roles=(kind, active_role),
            active_role=active_role,
            department=department,
            department_assignments=assignments,
            department_contexts=({"code": "CSE", "name": department},),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test")
    return client


def test_module_grant_and_permission_are_both_required(stub_iam):
    Department.objects.create(code="CSE", name="Computer Science")
    missing_module = auth(stub_iam, modules=(), permissions=("dept.announcement.view",))
    assert missing_module.get("/api/v1/dept/announcements/?department_code=CSE").status_code == 403
    missing_permission = auth(stub_iam, modules=("dept",), permissions=())
    assert (
        missing_permission.get("/api/v1/dept/announcements/?department_code=CSE").status_code == 403
    )


@pytest.mark.skipif(
    connection.vendor == "sqlite",
    reason="JSON array containment is supported by the production PostgreSQL backend, not SQLite.",
)
def test_announcement_reads_are_department_and_audience_scoped(stub_iam):
    cse = Department.objects.create(code="CSE", name="Computer Science")
    ece = Department.objects.create(code="ECE", name="Electronics")
    visible = Announcement.objects.create(
        department=cse,
        author_user_id=9,
        title="CSE notice",
        body="For students",
        target_roles=["student"],
    )
    Announcement.objects.create(
        department=ece,
        author_user_id=9,
        title="ECE secret",
        body="Private",
        target_roles=["student"],
    )
    client = auth(stub_iam, modules=("dept",), permissions=("dept.announcement.view",))
    response = client.get("/api/v1/dept/announcements/?department_code=CSE")
    assert response.status_code == 200
    assert [row["id"] for row in response.data] == [visible.pk]
    assert client.get("/api/v1/dept/announcements/?department_code=ECE").status_code == 404


def test_department_admin_permission_without_active_appointment_is_not_scope(stub_iam):
    Department.objects.create(code="CSE", name="Computer Science")
    client = auth(
        stub_iam,
        modules=("dept",),
        permissions=("dept.stock_item.view",),
        kind="faculty",
        active_role="Dept_Admin",
        assignments=(),
    )
    assert client.get("/api/v1/dept/inventory/?department_code=CSE").status_code == 404


def test_academic_info_falls_back_when_directory_profile_is_missing(stub_iam, monkeypatch):
    Department.objects.create(code="CSE", name="Computer Science")
    client = auth(
        stub_iam,
        modules=("dept",),
        permissions=("dept.department.view",),
        department="Computer Science",
    )
    monkeypatch.setattr("modules.dept.api.views.get_users", lambda user_ids: {})

    response = client.get("/api/v1/dept/academic-info/?department_code=CSE")

    assert response.status_code == 200
    assert response.data == {
        "programme": "",
        "discipline": "",
        "batch_year": None,
        "department": "Computer Science",
    }


def test_department_details_still_load_when_iam_appointments_are_unavailable(stub_iam):
    Department.objects.create(
        code="CSE",
        name="Computer Science",
        general_info={"description": "CSE department demo"},
    )
    fake = stub_iam(
        make_session(
            modules=("dept",),
            permissions=("dept.department.view",),
            department="CSE",
        )
    )

    def unavailable(_department_code):
        raise IamUnavailable("IAM appointment route is unavailable")

    fake.get_department_appointments = unavailable
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test")
    response = client.get("/api/v1/dept/details/?department_code=CSE")

    assert response.status_code == 200
    assert response.data["code"] == "CSE"
    assert response.data["head_user_id"] is None


def test_student_profiles_match_directory_department_code(stub_iam):
    Department.objects.create(code="CSE", name="Computer Science and Engineering")
    users = {
        7: IamUserRef(
            user_id=7, username="student7", display_name="Current Student", kind="student",
            department="CSE", discipline="CSE",
        ),
        8: IamUserRef(
            user_id=8, username="student8", display_name="Classmate", kind="student",
            department="CSE", discipline="CSE",
        ),
    }
    stub_iam(
        make_session(
            user_id=7,
            modules=("dept",),
            permissions=("dept.profile.view",),
            kind="student",
            active_role="student",
            department="CSE",
            department_contexts=({"code": "CSE", "name": "Computer Science and Engineering"},),
        ),
        users=users,
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test")

    response = client.get("/api/v1/dept/profiles/?department_code=CSE")

    assert response.status_code == 200
    assert list(UserRef.objects.values_list("user_id", "department", "kind")) == [
        (7, "CSE", "student"), (8, "CSE", "student")
    ]
    assert [profile["display_name"] for profile in response.data] == [
        "Current Student", "Classmate"
    ]
