import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm import registry
from modules.elm.models import LeaveRequest

pytestmark = pytest.mark.django_db

URL = "/api/v1/elm/leave-requests/"
STAFF = ("elm.leave_request.view", "elm.leave_request.manage")
BODY = {"category": "CL", "start_date": "2026-11-02",
        "end_date": "2026-11-03", "reason": "Family function"}


def _as(stub_iam, uid=2001, perms=STAFF, modules=("elm",)):
    stub_iam(make_session(user_id=uid, kind="staff", roles=("staff",),
                          active_role="staff", modules=modules, permissions=perms))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def test_permission_codes_match_registry():
    declared = {code for code, _ in registry.PERMISSIONS}
    assert set(STAFF) <= declared
    assert set(registry.ROLE_GRANTS["staff"]) <= declared


def test_staff_applies_for_their_own_leave(stub_iam):
    response = _as(stub_iam).post(URL, {**BODY, "user_id": 9999}, format="json")

    assert response.status_code == 201, response.content
    row = LeaveRequest.objects.get()
    assert row.user_id == 2001 and row.status == "pending"
    assert response.json()["events"][0]["event_type"] == "submitted"
    event = row.events.get()
    assert event.event_type == "submitted"
    assert event.to_status == "pending"
    assert event.actor_user_id == 2001


def test_faculty_can_apply_for_their_own_leave(stub_iam):
    stub_iam(make_session(user_id=2002, kind="faculty", roles=("faculty",),
                          active_role="faculty", modules=("elm",),
                          permissions=STAFF))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")

    response = client.post(URL, BODY, format="json")

    assert response.status_code == 201, response.content
    assert LeaveRequest.objects.get().user_id == 2002


def test_end_before_start_is_refused(stub_iam):
    response = _as(stub_iam).post(
        URL, {**BODY, "end_date": "2026-11-01"}, format="json")

    assert response.status_code == 400


@pytest.mark.parametrize("status", ["pending", "approved"])
def test_active_leave_overlap_is_rejected(stub_iam, status):
    LeaveRequest.objects.create(
        user_id=2001,
        category="CL",
        status=status,
        start_date="2026-11-02",
        end_date="2026-11-03",
        reason="x",
    )

    overlapping = _as(stub_iam).post(
        URL,
        {**BODY, "start_date": "2026-11-03", "end_date": "2026-11-04"},
        format="json",
    )

    assert overlapping.status_code == 409
    assert overlapping.json()["error"]["code"] == "leave_request_overlap"
    assert LeaveRequest.objects.count() == 1


def test_rejected_leave_does_not_block_overlapping_request(stub_iam):
    LeaveRequest.objects.create(
        user_id=2001,
        category="CL",
        status="rejected",
        start_date="2026-11-02",
        end_date="2026-11-03",
        reason="x",
    )

    response = _as(stub_iam).post(URL, BODY, format="json")

    assert response.status_code == 201, response.content


def test_opposite_half_day_casual_leave_requests_do_not_overlap(stub_iam):
    client = _as(stub_iam)
    body = {**BODY, "start_date": "2026-11-02", "end_date": "2026-11-02"}
    first = client.post(URL, {**body, "day_part": "first_half"}, format="json")
    second = client.post(URL, {**body, "day_part": "second_half"}, format="json")

    assert first.status_code == 201, first.content
    assert second.status_code == 201, second.content
    assert [row.day_part for row in LeaveRequest.objects.order_by("pk")] == [
        "first_half",
        "second_half",
    ]

    duplicate_half = client.post(
        URL, {**body, "day_part": "first_half"}, format="json")

    assert duplicate_half.status_code == 409
    assert LeaveRequest.objects.count() == 2


@pytest.mark.parametrize(
    ("category", "start_date", "end_date"),
    [
        ("EL", "2026-11-02", "2026-11-02"),
        ("CL", "2026-11-02", "2026-11-03"),
    ],
)
def test_half_day_is_limited_to_single_day_casual_leave(
    stub_iam, category, start_date, end_date,
):
    response = _as(stub_iam).post(
        URL,
        {
            **BODY,
            "category": category,
            "start_date": start_date,
            "end_date": end_date,
            "day_part": "first_half",
        },
        format="json",
    )

    assert response.status_code == 400
    assert any(
        detail["field"] == "day_part"
        for detail in response.json()["error"]["details"]
    )


def test_without_manage_cannot_apply(stub_iam):
    client = _as(stub_iam, perms=("elm.leave_request.view",))

    assert client.post(URL, BODY, format="json").status_code == 403


def test_without_module_grant_is_refused(stub_iam):
    assert _as(stub_iam, modules=()).get(URL).status_code == 403


def test_another_persons_request_is_404(stub_iam):
    other = LeaveRequest.objects.create(user_id=3003, category="EL",
                                        start_date="2026-11-02",
                                        end_date="2026-11-02", reason="x")
    client = _as(stub_iam)

    assert client.get(URL).json()["results"] == []
    assert client.get(f"{URL}{other.pk}/").status_code == 404
    assert client.delete(f"{URL}{other.pk}/").status_code == 404
    assert client.post(f"{URL}{other.pk}/withdraw/").status_code == 404


def test_decided_request_cannot_be_edited(stub_iam):
    row = LeaveRequest.objects.create(user_id=2001, category="CL", status="approved",
                                      start_date="2026-11-02",
                                      end_date="2026-11-02", reason="x")

    response = _as(stub_iam).patch(f"{URL}{row.pk}/", {"reason": "y"}, format="json")

    assert response.status_code == 409


def test_pending_request_cannot_be_modified_or_deleted(stub_iam):
    row = LeaveRequest.objects.create(user_id=2001, category="CL",
                                      start_date="2026-11-02",
                                      end_date="2026-11-02", reason="x")
    client = _as(stub_iam)

    assert client.patch(f"{URL}{row.pk}/", {"reason": "y"},
                        format="json").status_code == 409
    assert client.delete(f"{URL}{row.pk}/").status_code == 409
    row.refresh_from_db()
    assert row.status == "pending"
    assert row.reason == "x"


def test_employee_can_withdraw_pending_request(stub_iam):
    client = _as(stub_iam)
    created = client.post(URL, BODY, format="json")
    assert created.status_code == 201, created.content
    row = LeaveRequest.objects.get()

    response = client.post(f"{URL}{row.pk}/withdraw/")

    assert response.status_code == 200, response.content
    row.refresh_from_db()
    assert row.status == "withdrawn"
    assert [event["event_type"] for event in response.json()["events"]] == [
        "submitted", "withdrawn",
    ]
    events = list(row.events.values_list("event_type", "from_status", "to_status"))
    assert events == [
        ("submitted", "", "pending"),
        ("withdrawn", "pending", "withdrawn"),
    ]


def test_decided_request_cannot_be_withdrawn(stub_iam):
    row = LeaveRequest.objects.create(user_id=2001, category="CL", status="approved",
                                      start_date="2026-11-02",
                                      end_date="2026-11-02", reason="x")

    response = _as(stub_iam).post(f"{URL}{row.pk}/withdraw/")

    assert response.status_code == 409
    row.refresh_from_db()
    assert row.status == "approved"
