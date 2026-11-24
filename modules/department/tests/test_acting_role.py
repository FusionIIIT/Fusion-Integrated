"""Only the acting role counts, for every write (Step 5.1, BR-DEPT-024, R2-01, R2-02, R2-13)."""

from datetime import time, timedelta

import pytest
from django.utils import timezone

from modules.department.domain.roles import DEPT_ADMIN, FACULTY, HOD, STUDENT, ActorContext
from modules.department.models import (
    Announcement,
    Department,
    Feedback,
    FeedbackNote,
    InventoryItem,
    LabResource,
    OfficialChange,
    ProfileRecord,
    RoleTenure,
    StockMovement,
    StockRequest,
    TimetableSlot,
)
from modules.department.services import announcements, departments, feedback, inventory, resources
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"
MODELS = (
    Announcement,
    Department,
    Feedback,
    FeedbackNote,
    InventoryItem,
    LabResource,
    OfficialChange,
    ProfileRecord,
    RoleTenure,
    StockMovement,
    StockRequest,
    TimetableSlot,
)


def fingerprint():
    """Row counts and newest change per table: any write at all changes it."""
    out = []
    for model in MODELS:
        stamp = (
            "updated_at"
            if hasattr(model, "updated_at")
            else "created_at"
            if hasattr(model, "created_at")
            else None
        )
        latest = (
            model.objects.order_by(f"-{stamp}").values_list(stamp, flat=True).first()
            if stamp
            else None
        )
        out.append((model.__name__, model.objects.count(), latest))
    return out


@pytest.fixture
def rows(world):
    admin, hod = ActorContext(uid("admin"), DEPT_ADMIN, "CSE"), ActorContext(uid("hod"), HOD, "CSE")
    fac = ActorContext(uid("faculty"), FACULTY, "CSE")
    ann = announcements.publish(fac, title="t", body="b", audience_role="all")
    item = inventory.add_item(admin, name="Kit", unit="unit", quantity=10)
    pending = inventory.request_stock(fac, item_id=item.pk, quantity=1)
    approved = inventory.request_stock(fac, item_id=item.pk, quantity=1)
    inventory.decide(hod, approved.pk, approve=True)
    change = departments.propose(admin, field="core_policies", value="p")
    fb = feedback.submit(ActorContext(uid("student"), STUDENT, "CSE"), subject="s", body="b")
    feedback.review(admin, fb.pk)
    slot = resources.upload(
        admin,
        [
            {
                "kind": "class",
                "course_code": "C",
                "day_of_week": 0,
                "starts_at": time(9),
                "ends_at": time(10),
                "room": "R1",
            }
        ],
    )[0]
    lab = resources.save_lab(admin, name="Lab")
    profile = resources.create_profile(admin, kind="alumni", display_name="A")
    tenure = RoleTenure.objects.get(department=world["CSE"], role="hod")
    return {
        "ann": ann.pk,
        "item": item.pk,
        "pending": pending.pk,
        "approved": approved.pk,
        "change": change.pk,
        "fb": fb.pk,
        "slot": slot.pk,
        "lab": lab.pk,
        "profile": profile.pk,
        "tenure": tenure.pk,
    }


SLOT = {
    "kind": "class",
    "course_code": "Z",
    "day_of_week": 3,
    "starts_at": "14:00",
    "ends_at": "15:00",
}
LATER = (timezone.now() + timedelta(days=900)).isoformat()

# (office that owns it, method, path, body)
WRITES = [
    ("hod", "patch", "announcements/{ann}", {"title": "changed"}),
    ("hod", "post", "announcements/{ann}/hide", {}),
    ("hod", "delete", "announcements/{ann}", None),
    ("hod", "post", "stock-requests/{pending}/decide", {"approve": True}),
    ("hod", "post", "official-changes/{change}/decide", {"approve": True}),
    ("hod", "post", "feedback/{fb}/dispose", {"outcome": "resolved"}),
    ("hod", "post", "feedback/{fb}/notes", {"body": "n"}),
    ("admin", "post", "inventory-items", {"name": "New", "quantity": 1}),
    ("admin", "post", "inventory-items/{item}/receipts", {"quantity": 1}),
    ("admin", "post", "stock-requests/{approved}/issue", {}),
    ("admin", "patch", "departments/CSE", {"description": "x"}),
    ("admin", "post", "official-changes", {"field": "name", "value": "N"}),
    ("admin", "post", "timetable-slots", {"slots": [SLOT]}),
    ("admin", "patch", "timetable-slots/{slot}", {"room": "R9"}),
    ("admin", "delete", "timetable-slots/{slot}", None),
    ("admin", "post", "lab-resources", {"name": "Other"}),
    ("admin", "patch", "lab-resources/{lab}", {"name": "Renamed"}),
    ("admin", "post", "profiles", {"kind": "alumni", "display_name": "B"}),
    ("admin", "patch", "profiles/{profile}", {"office": "x"}),
    (
        "central",
        "post",
        "role-assignments",
        {
            "department": "ECE",
            "role": "hod",
            "user_id": 3002,
            "valid_from": LATER,
            "valid_to": LATER.replace("20", "21", 1),
        },
    ),
    ("central", "patch", "role-assignments/{tenure}", {"valid_to": LATER}),
]
# The non-office role each office holder can switch to, as the IAM offers it.
PLAIN = {"hod": "faculty", "admin": "staff", "central": "staff"}


def _call(client, method, path, body, ids):
    url = f"{API}/{path.format(**ids)}"
    return (
        getattr(client, method)(url, body, format="json")
        if body is not None
        else getattr(client, method)(url)
    )


@pytest.mark.parametrize(("owner", "method", "path", "body"), WRITES)
def test_an_office_holder_acting_in_a_plain_role_cannot_write(rows, act, owner, method, path, body):
    before = fingerprint()
    r = _call(act(owner, active_role=PLAIN[owner]), method, path, body, rows)
    assert r.status_code in (403, 404), (owner, path, r.status_code, r.content)
    assert fingerprint() == before


@pytest.mark.parametrize(
    ("owner", "method", "path", "body"), [w for w in WRITES if w[0] in ("hod", "admin")]
)
@pytest.mark.parametrize("acting", ["office", "plain"])
def test_an_outgoing_holder_cannot_write_in_any_role(rows, act, owner, method, path, body, acting):
    # BR-DEPT-024, AFR-DEPT-049: once the tenure has ended, no office verb works, whatever the acting role
    RoleTenure.objects.filter(user_id=uid(owner)).update(
        valid_to=timezone.now() - timedelta(seconds=1)
    )
    before = fingerprint()
    client = act(owner) if acting == "office" else act(owner, active_role=PLAIN[owner])
    r = _call(client, method, path, body, rows)
    assert r.status_code in (403, 404, 422), (owner, acting, path, r.status_code, r.content)
    assert fingerprint() == before


def test_the_same_holders_succeed_in_their_office_role(rows, act):
    # The negative twin: the refusals above are about the role, not the request
    assert act("hod").post(f"{API}/announcements/{rows['ann']}/hide").status_code == 200
    assert (
        act("admin")
        .patch(f"{API}/lab-resources/{rows['lab']}", {"name": "Renamed"}, format="json")
        .status_code
        == 200
    )
    assert (
        act("central")
        .patch(f"{API}/role-assignments/{rows['tenure']}", {"valid_to": LATER}, format="json")
        .status_code
        == 200
    )


@pytest.mark.parametrize(
    ("who", "acting", "expected"),
    [
        ("hod", None, {"role": "hod", "department": "CSE"}),
        ("hod", "faculty", {"role": "faculty", "department": "CSE"}),
        ("admin", "staff", {"role": None, "department": None}),
        ("student", None, {"role": "student", "department": "CSE"}),
        ("central", None, {"role": "central", "department": None}),
    ],
)
def test_context_reports_the_acting_role(world, act, who, acting, expected):
    client = act(who, active_role=acting) if acting else act(who)
    assert client.get(f"{API}/context").json() == expected
