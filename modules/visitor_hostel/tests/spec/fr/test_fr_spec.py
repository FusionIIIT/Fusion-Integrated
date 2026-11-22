"""Executable FR regressions: IAM identity, ownership, validation and permissions."""

import pytest
from rest_framework.test import APIClient

from modules.visitor_hostel.models import BookingRequest
from modules.visitor_hostel.tests.spec.conftest import endpoint

pytestmark = pytest.mark.django_db


def test_online_submission_uses_iam_id(actor, payload):
    """
    Test ID: FR-001
    Source ID: AFR-VH-001
    Purpose: Verify authenticated indenter can submit an online booking requisition using IAM identity.
    Preconditions: Authenticated user with active IAM session.
    Action: POST /api/v1/visitor-hostel/bookings/ with valid payload.
    Expected: HTTP 201 Created, status pending, not offline, audit event logged.
    """
    response = actor().post("/api/v1/visitor-hostel/bookings/", payload, format="json")
    assert response.status_code == 201, response.data
    booking = BookingRequest.objects.get()
    assert booking.indenter_id == 1001
    assert booking.status == "pending"
    assert not booking.is_offline
    assert booking.audit_events.get().action == "submitted"


@pytest.mark.parametrize("method", ["get", "patch"])
def test_other_indenter_cannot_access_booking(actor, booking, method):
    """
    Test ID: FR-002
    Source ID: AFR-VH-002
    Purpose: Verify indenter cannot view or modify bookings created by another indenter (IDOR prevention).
    Preconditions: Booking owned by user 1001; acting user is 2002.
    Action: GET or PATCH /api/v1/visitor-hostel/bookings/{id}/.
    Expected: HTTP 404 Not Found.
    """
    response = getattr(actor(user_id=2002), method)(endpoint(booking), {}, format="json")
    assert response.status_code == 404


def test_list_scoped_to_owner(actor, booking):
    """
    Test ID: FR-005
    Source ID: AFR-VH-005
    Purpose: Verify booking list is strictly scoped to the requesting indenter's own submissions.
    Preconditions: Booking exists for user 1001; acting user is 2002.
    Action: GET /api/v1/visitor-hostel/bookings/.
    Expected: HTTP 200 with empty results list.
    """
    response = actor(user_id=2002).get("/api/v1/visitor-hostel/bookings/")
    assert response.status_code == 200
    assert response.data["results"] == []


@pytest.mark.parametrize(
    "action,data",
    [
        ("route", {"action": "forward"}),
        ("decision", {"decision": "approve"}),
        ("allot", {"room_ids": [1]}),
        ("check-in", {}),
        ("check-out", {}),
        ("cancel/confirm", {}),
        ("meals", {}),
        ("settle", {}),
    ],
)
def test_indenter_cannot_execute_staff_actions(actor, booking, action, data):
    """
    Test ID: FR-004
    Source ID: AFR-VH-004
    Purpose: Verify regular indenter is denied execution of caretaker and in-charge actions.
    Preconditions: Standard student/indenter session.
    Action: POST to restricted staff endpoints (route, decision, allot, check-in, check-out, etc.).
    Expected: HTTP 403 Forbidden; booking state unchanged.
    """
    assert actor().post(endpoint(booking, action), data, format="json").status_code == 403
    booking.refresh_from_db()
    assert booking.status == "pending"


@pytest.mark.parametrize("kwargs", [{"modules": ()}, {"kind": "visitor"}])
def test_module_grant_and_institute_identity_required(actor, kwargs):
    """
    Test ID: FR-003
    Source ID: AFR-VH-003
    Purpose: Verify access is denied without active visitor_hostel module grant or valid institute identity.
    Preconditions: User without module grant or non-institute identity.
    Action: GET /api/v1/visitor-hostel/bookings/.
    Expected: HTTP 403 Forbidden.
    """
    assert actor(**kwargs).get("/api/v1/visitor-hostel/bookings/").status_code == 403


def test_anonymous_denied():
    """
    Test ID: FR-006
    Source ID: AFR-VH-006
    Purpose: Verify unauthenticated requests are rejected.
    Preconditions: No authorization header.
    Action: GET /api/v1/visitor-hostel/bookings/.
    Expected: HTTP 401 Unauthorized.
    """
    assert APIClient().get("/api/v1/visitor-hostel/bookings/").status_code == 401


def test_workflow_fields_cannot_be_mass_assigned(actor, booking):
    """
    Test ID: FR-007
    Source ID: AFR-VH-007
    Purpose: Verify client cannot mass-assign internal workflow or ownership fields.
    Preconditions: Existing booking.
    Action: PATCH /api/v1/visitor-hostel/bookings/{id}/ with status='approved', indenter_id=999.
    Expected: Status and indenter_id remain intact.
    """
    response = actor().patch(
        endpoint(booking),
        {
            "status": "approved",
            "indenter_id": 999,
            "is_offline": True,
            "cancellation_reason": "spoof",
        },
        format="json",
    )
    assert response.status_code == 200
    booking.refresh_from_db()
    assert (booking.status, booking.indenter_id, booking.is_offline) == ("pending", 1001, False)
    assert booking.cancellation_reason == ""


@pytest.mark.parametrize(
    "change",
    [
        {"number_of_rooms": 0},
        {"number_of_rooms": -1},
        {"number_of_occupants": 0},
        {"number_of_occupants": 3},
        {"visitor_category": "E"},
        {"occupancy": "triple"},
        {"billing_responsibility": "Gateway"},
        {"check_out_date": "2020-01-01"},
        {"check_in_date": "2020-01-01"},
        {"visitor_email": "invalid"},
    ],
)
def test_invalid_requisitions_rejected(actor, payload, change):
    """
    Test ID: FR-008
    Source ID: AFR-VH-008
    Purpose: Verify input validation rejects non-compliant requisitions.
    Preconditions: Various invalid payload variants.
    Action: POST /api/v1/visitor-hostel/bookings/ with malformed data.
    Expected: HTTP 400 Bad Request and no database record created.
    """
    response = actor().post("/api/v1/visitor-hostel/bookings/", payload | change, format="json")
    assert response.status_code == 400, response.data
    assert not BookingRequest.objects.exists()


def test_planned_times_and_occupants_persist(actor, payload):
    """
    Test ID: FR-009
    Source ID: AFR-VH-009
    Purpose: Verify planned check-in/out times and occupant count persist accurately.
    Preconditions: Valid requisition with arrival/departure times.
    Action: POST /api/v1/visitor-hostel/bookings/ with check_in_time and number_of_occupants.
    Expected: HTTP 201 Created with times and occupant count saved.
    """
    response = actor().post(
        "/api/v1/visitor-hostel/bookings/",
        payload
        | {
            "occupancy": "double",
            "number_of_occupants": 2,
            "check_in_time": "15:30",
            "check_out_time": "10:45",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["check_in_time"] == "15:30:00"
    assert response.data["number_of_occupants"] == 2


def test_offline_booking_is_caretaker_only(actor, payload):
    """
    Test ID: FR-011
    Source ID: AFR-VH-011
    Purpose: Verify offline booking submission is permitted only to caretaker role.
    Preconditions: Caretaker vs indenter session.
    Action: POST /api/v1/visitor-hostel/bookings/offline/.
    Expected: 403 for indenter, 201 for caretaker with is_offline=True.
    """
    url = "/api/v1/visitor-hostel/bookings/offline/"
    assert actor().post(url, payload, format="json").status_code == 403
    response = actor("vh_caretaker").post(url, payload, format="json")
    assert response.status_code == 201
    assert response.data["is_offline"] is True
    assert response.data["status"] == "pending"
    assert response.data["indenter_id"] is None


@pytest.mark.parametrize(
    "action,data",
    [
        ("route", {"action": "forward"}),
        ("check-in", {}),
        ("check-out", {}),
        ("allot", {"room_ids": [123]}),
        ("cancel/confirm", {}),
        ("settle", {}),
    ],
)
def test_missing_booking_is_404(actor, action, data):
    """
    Test ID: FR-012
    Source ID: AFR-VH-012
    Purpose: Verify operations on non-existent booking IDs return 400 or 404 without 500 errors.
    Preconditions: Non-existent booking id 999999.
    Action: Action endpoints on non-existent ID.
    Expected: HTTP 400 or 404.
    """
    response = actor("vh_caretaker").post(
        f"/api/v1/visitor-hostel/bookings/999999/{action}/", data, format="json"
    )
    assert response.status_code in (400, 404)

