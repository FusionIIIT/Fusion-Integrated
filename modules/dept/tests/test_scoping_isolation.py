"""Multi-department isolation and scoping tests (AFR-DEPT-001, AFR-DEPT-003, CFR-DEPT-001)."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.dept.models import (
    Announcement,
    Department,
    InventoryItem,
    LabResource,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def depts():
    cse = Department.objects.create(code="CSE", name="Computer Science and Engineering")
    ece = Department.objects.create(code="ECE", name="Electronics and Communication Engineering")
    return cse, ece


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_announcements_isolated_by_department(stub_iam, depts):
    cse, ece = depts
    Announcement.objects.create(
        department=cse,
        title="CSE Notice",
        content="CSE Only",
        author_id="prof_cse",
        author_role="HOD",
    )
    Announcement.objects.create(
        department=ece,
        title="ECE Notice",
        content="ECE Only",
        author_id="prof_ece",
        author_role="HOD",
    )

    client_cse = _client(
        stub_iam,
        user_id=1,
        modules=("dept",),
        permissions=("dept.announcement.view",),
        roles=("student",),
    )
    res_cse = client_cse.get("/api/v1/dept/announcements/?department=CSE")
    assert res_cse.status_code == 200
    titles = [a["title"] for a in res_cse.json()]
    assert "CSE Notice" in titles
    assert "ECE Notice" not in titles

    res_ece = client_cse.get("/api/v1/dept/announcements/?department=ECE")
    assert res_ece.status_code == 200
    titles_ece = [a["title"] for a in res_ece.json()]
    assert "ECE Notice" in titles_ece
    assert "CSE Notice" not in titles_ece


def test_inventory_isolated_by_department(stub_iam, depts):
    cse, ece = depts
    InventoryItem.objects.create(
        department=cse, item_code="PC-CSE-01", name="CSE Desktop", quantity=10
    )
    InventoryItem.objects.create(
        department=ece, item_code="OSC-ECE-01", name="ECE Oscilloscope", quantity=5
    )

    c = _client(
        stub_iam,
        user_id=2,
        modules=("dept",),
        permissions=("dept.inventory.view",),
        roles=("faculty",),
    )
    res_cse = c.get("/api/v1/dept/inventory/?department=CSE")
    assert res_cse.status_code == 200
    items_cse = [i["item_code"] for i in res_cse.json()]
    assert "PC-CSE-01" in items_cse
    assert "OSC-ECE-01" not in items_cse


def test_lab_resources_isolated_by_department(stub_iam, depts):
    cse, ece = depts
    LabResource.objects.create(
        department=cse,
        lab_name="Systems Lab",
        location="Room 101",
        in_charge_id="faculty_1",
    )
    LabResource.objects.create(
        department=ece,
        lab_name="VLSI Lab",
        location="Room 201",
        in_charge_id="faculty_2",
    )

    c = _client(
        stub_iam,
        user_id=3,
        modules=("dept",),
        permissions=("dept.lab_resource.view",),
        roles=("faculty",),
    )
    res_cse = c.get("/api/v1/dept/labs/?department=CSE")
    assert res_cse.status_code == 200
    labs_cse = [lab["lab_name"] for lab in res_cse.json()]
    assert "Systems Lab" in labs_cse
    assert "VLSI Lab" not in labs_cse
