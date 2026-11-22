import pytest
from django.core.management import call_command
from django.test import override_settings
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from core.api.exceptions import ConflictError
from fusion_auth.client import IamUnavailable
from modules.dept.models import (
    Announcement,
    Department,
    Feedback,
    InventoryItem,
    StockMovement,
    StockRequest,
)
from modules.dept.selectors.scoping import department_scope
from modules.dept.services.operations import (
    decide_stock,
    issue_stock,
    request_stock,
    submit_feedback,
)

pytestmark = pytest.mark.django_db


def test_regular_user_department_code_bootstraps_local_scope(stub_iam):
    student = make_principal(kind="student", department="CSE")

    dept = department_scope(student, "CSE")

    assert (dept.code, dept.name) == ("CSE", "CSE")


@override_settings(DEPT_DEMO_USER_DEPARTMENTS={5328: "CSE", 6565: "CSE"})
def test_local_demo_student_and_faculty_receive_cse_scope():
    from conftest import make_principal

    for user_id, kind in ((5328, "faculty"), (6565, "student")):
        actor = make_principal(user_id=user_id, kind=kind, department="")
        assert department_scope(actor).code == "CSE"


def test_cse_demo_seed_populates_department_pages_idempotently():
    call_command("seed_dept_demo", verbosity=0)
    call_command("seed_dept_demo", verbosity=0)

    department = Department.objects.get(code="CSE")
    assert department.name == "Computer Science and Engineering"
    assert Announcement.objects.filter(department=department, published=True).count() == 1
    assert InventoryItem.objects.filter(department=department, name="HDMI cable").count() == 1


def test_stock_approval_reserves_once_and_issuance_is_audited(stub_iam):
    fake = stub_iam()
    fake.department_appointments["CSE"] = [
        {"user_id": 20, "role": "HOD"},
        {"user_id": 30, "role": "Dept_Admin"},
    ]
    dept = Department.objects.create(code="CSE", name="Computer Science")
    item = InventoryItem.objects.create(department=dept, name="Cable", on_hand=5)
    faculty = make_principal(
        user_id=10,
        kind="faculty",
        active_role="faculty",
        permissions=("dept.stock_request.create",),
    )
    req = request_stock(actor=faculty, department=dept, item_id=item.pk, quantity=3)
    assert req.status == "pending"

    hod = make_principal(
        user_id=20, kind="faculty", active_role="HOD", permissions=("dept.stock_request.approve",)
    )
    req = decide_stock(actor=hod, request_id=req.pk, department=dept, approve=True)
    item.refresh_from_db()
    assert req.status == "approved"
    assert (item.on_hand, item.reserved) == (5, 3)
    with pytest.raises(ConflictError):
        decide_stock(actor=hod, request_id=req.pk, department=dept, approve=True)

    admin = make_principal(
        user_id=30,
        kind="faculty",
        active_role="Dept_Admin",
        permissions=("dept.stock_request.update",),
    )
    req = issue_stock(actor=admin, request_id=req.pk, department=dept)
    item.refresh_from_db()
    assert req.status == "issued"
    assert (item.on_hand, item.reserved) == (2, 0)
    assert list(
        StockMovement.objects.filter(request=req)
        .order_by("created_at", "pk")
        .values_list("kind", flat=True)
    ) == ["reserve", "issue"]
    movement = StockMovement.objects.filter(request=req).first()
    movement.note = "tamper"
    with pytest.raises(ValueError, match="immutable"):
        movement.save()


def test_request_fails_closed_when_requesting_more_than_stock(stub_iam):
    dept = Department.objects.create(code="ECE", name="Electronics")
    item = InventoryItem.objects.create(department=dept, name="Board", on_hand=2)
    actor = make_principal(
        kind="faculty", active_role="faculty", permissions=("dept.stock_request.create",)
    )
    with pytest.raises(ConflictError):
        request_stock(actor=actor, department=dept, item_id=item.pk, quantity=3)
    assert StockRequest.objects.count() == 0


def test_students_only_receive_their_own_feedback(stub_iam):
    dept = Department.objects.create(code="CSE", name="Computer Science")
    own = Feedback.objects.create(department=dept, submitter_user_id=1, title="Own", body="Mine")
    Feedback.objects.create(department=dept, submitter_user_id=2, title="Private", body="Secret")
    stub_iam(
        make_session(
            user_id=1,
            modules=("dept",),
            permissions=("dept.feedback.view",),
            department="Computer Science",
            department_contexts=({"code": "CSE", "name": "Computer Science"},),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test")
    response = client.get("/api/v1/dept/feedback/?department_code=CSE")
    assert response.status_code == 200
    assert [r["id"] for r in response.data] == [own.pk]


def test_feedback_submission_survives_unavailable_iam_reviewer_lookup(stub_iam):
    fake = stub_iam()

    def unavailable(_department_code):
        raise IamUnavailable("IAM appointment route is unavailable")

    fake.get_department_appointments = unavailable
    department = Department.objects.create(code="CSE", name="Computer Science")
    student = make_principal(
        user_id=6565,
        kind="student",
        active_role="student",
        permissions=("dept.feedback.create",),
    )

    feedback = submit_feedback(
        actor=student,
        department=department,
        title="Feedback",
        body="Please improve the lab schedule.",
    )

    assert Feedback.objects.filter(pk=feedback.pk).exists()
