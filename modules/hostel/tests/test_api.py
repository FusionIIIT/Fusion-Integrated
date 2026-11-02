"""API endpoint tests for Hostel Management."""

import pytest
from datetime import date, timedelta
from rest_framework.test import APIRequestFactory
from fusion_auth.principal import Principal
from modules.hostel.api.views import (
    HostelListCreateView,
    LeaveDecisionView,
    LeaveRequestListCreateView,
    RoomExchangeView,
)
from modules.hostel.domain.constants import LeaveStatus
from modules.hostel.services import (
    create_hostel,
    create_room,
    record_allotment_decision,
    submit_accommodation_request,
)


def make_principal(user_id=1, username="admin", kind="staff", role="Super Admin", permissions=None):
    if permissions is None:
        permissions = {
            "hostel.master.manage", "hostel.role_binding.manage",
            "hostel.accommodation.apply", "hostel.accommodation.view",
            "hostel.allotment.manage", "hostel.room.manage", "hostel.room.view",
            "hostel.attendance.record", "hostel.attendance.view",
            "hostel.leave.apply", "hostel.leave.review", "hostel.leave.view",
            "hostel.complaint.submit", "hostel.complaint.resolve", "hostel.complaint.view",
            "hostel.guest_room.request", "hostel.guest_room.review", "hostel.guest_room.view",
            "hostel.extended_stay.apply", "hostel.extended_stay.review", "hostel.extended_stay.view",
            "hostel.fine.record", "hostel.fine.view", "hostel.inventory.manage",
            "hostel.inventory.view", "hostel.staff.manage", "hostel.staff.view",
            "hostel.security.manage", "hostel.security.view", "hostel.notice.publish",
            "hostel.notice.view", "hostel.report.view",
        }
    return Principal(
        user_id=user_id,
        username=username,
        display_name=username.title(),
        kind=kind,
        active_role=role,
        roles=(role,),
        permissions=frozenset(permissions),
        modules=("hostel",),
    )


@pytest.mark.django_db
class TestHostelApi:
    def test_list_and_create_hostel(self):
        p = make_principal(role="Super Admin")
        create_hostel("Hall of Residence 1", "H1", capacity=150)

        factory = APIRequestFactory()
        req = factory.get("/api/v1/hostel/hostels/")
        req.principal = p
        view = HostelListCreateView.as_view()
        res = view(req)
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["code"] == "H1"

        # Create hostel via POST
        post_req = factory.post("/api/v1/hostel/hostels/", {
            "name": "Hall of Residence 2",
            "code": "H2",
            "capacity": 200,
        }, format="json")
        post_req.principal = p
        post_res = view(post_req)
        assert post_res.status_code == 201
        assert post_res.data["code"] == "H2"

    def test_room_exchange_api(self):
        p = make_principal(role="Hostel Caretaker", permissions={"hostel.room.manage", "hostel.room.view"})
        h = create_hostel("Hall 2", "H2", capacity=50)
        r1 = create_room(h.id, "201", capacity=2)
        r2 = create_room(h.id, "202", capacity=2)

        req1 = submit_accommodation_request(501, "24BCS001", "Alice", "2026", "1")
        req2 = submit_accommodation_request(502, "24BCS002", "Bob", "2026", "1")
        record_allotment_decision(1, req1.id, r1.id)
        record_allotment_decision(1, req2.id, r2.id)

        factory = APIRequestFactory()
        request = factory.post("/api/v1/hostel/rooms/exchange/", {
            "hostel_id": h.id,
            "student_user_id_1": 501,
            "target_room_id": r2.id,
            "student_user_id_2": 502,
            "reason": "Test swap",
        }, format="json")
        request.principal = p
        view = RoomExchangeView.as_view()
        res = view(request)
        assert res.status_code == 200
        assert res.data["student_1"]["room"] == r2.id

    def test_leave_api_lifecycle(self):
        student_p = make_principal(user_id=501, username="24bcs001", kind="student", role="student", permissions={"hostel.leave.apply", "hostel.leave.view"})
        caretaker_p = make_principal(user_id=201, username="caretaker1", kind="staff", role="Hostel Caretaker", permissions={"hostel.leave.review", "hostel.leave.view"})

        h = create_hostel("Hall 3", "H3")

        # 1. Student submits leave
        factory = APIRequestFactory()
        req1 = factory.post("/api/v1/hostel/leaves/", {
            "hostel_id": h.id,
            "leave_type": "home",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=2)),
            "reason": "Family function",
        }, format="json")
        req1.principal = student_p
        res1 = LeaveRequestListCreateView.as_view()(req1)
        assert res1.status_code == 201
        leave_id = res1.data["id"]

        # 2. Caretaker approves leave
        req2 = factory.post(f"/api/v1/hostel/leaves/{leave_id}/decision/", {
            "decision": "approved",
            "remarks": "Approved by Caretaker",
        }, format="json")
        req2.principal = caretaker_p
        res2 = LeaveDecisionView.as_view()(req2, pk=leave_id)
        assert res2.status_code == 200
        assert res2.data["status"] == "approved"
