"""Privilege escalation tests: verifying unauthorized roles are refused."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.dept.models import Department, InventoryItem, StockRequest

pytestmark = pytest.mark.django_db


@pytest.fixture
def cse_dept():
    return Department.objects.create(code="CSE", name="Computer Science and Engineering")


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_student_cannot_create_announcements(stub_iam, cse_dept):
    c = _client(
        stub_iam,
        user_id=1,
        modules=("dept",),
        permissions=("dept.announcement.view",),
        roles=("student",),
    )
    res = c.post(
        "/api/v1/dept/announcements/?department=CSE",
        {"title": "Student circular", "content": "Unauthorized post"},
        format="json",
    )
    assert res.status_code in {401, 403}


def test_faculty_cannot_approve_stock(stub_iam, cse_dept):
    item = InventoryItem.objects.create(
        department=cse_dept, item_code="PC-01", name="PC", quantity=5
    )
    sr = StockRequest.objects.create(
        department=cse_dept,
        inventory_item=item,
        requested_by_id="fac1",
        requested_quantity=1,
        purpose="Work",
    )

    c = _client(
        stub_iam,
        user_id=2,
        modules=("dept",),
        permissions=("dept.stock_request.view", "dept.stock_request.create"),
        roles=("faculty",),
    )
    res = c.post(
        f"/api/v1/dept/stock-requests/{sr.id}/decision/?department=CSE",
        {"decision": "APPROVE"},
        format="json",
    )
    assert res.status_code in {401, 403}


def test_faculty_cannot_issue_stock(stub_iam, cse_dept):
    item = InventoryItem.objects.create(
        department=cse_dept, item_code="PC-01", name="PC", quantity=5
    )
    sr = StockRequest.objects.create(
        department=cse_dept,
        inventory_item=item,
        requested_by_id="fac1",
        requested_quantity=1,
        purpose="Work",
        status="APPROVED",
    )

    c = _client(
        stub_iam,
        user_id=2,
        modules=("dept",),
        permissions=("dept.stock_request.view", "dept.stock_request.create"),
        roles=("faculty",),
    )
    res = c.post(
        f"/api/v1/dept/stock-requests/{sr.id}/issue/?department=CSE",
        {"notes": "Self issue"},
        format="json",
    )
    assert res.status_code in {401, 403}


def test_dept_admin_cannot_approve_official_changes(stub_iam, cse_dept):
    c = _client(
        stub_iam,
        user_id=3,
        modules=("dept",),
        permissions=("dept.detail.view", "dept.detail.update"),
        roles=("Dept_Admin",),
    )
    res = c.post(
        "/api/v1/dept/details/pending-changes/11111111-1111-1111-1111-111111111111/decision/?department=CSE",
        {"decision": "APPROVE"},
        format="json",
    )
    assert res.status_code in {401, 403}
