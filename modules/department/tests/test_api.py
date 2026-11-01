"""DRF API tests for Department module."""
import datetime
import pytest
from rest_framework.test import APIClient
from conftest import make_session

from modules.department.models.seminar import (
    SeminarSchedulingRequest,
    GraduateSeminar,
)
from modules.department.models.allocation import (
    TAAllocation,
    ThesisSupervisorAllocation,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token fake-token")
    return c


def test_student_submit_seminar_request(stub_iam):
    c = _client(
        stub_iam,
        user_id=101,
        kind="student",
        modules=("department",),
        permissions=("department.seminar.request", "department.seminar.view_self"),
    )

    payload = {
        "topic": "Graph Neural Networks for Traffic Prediction",
        "abstract": "We evaluate spatial-temporal GNN architectures on benchmark datasets.",
        "programme": "M.Tech",
        "department": "CSE",
        "preferred_date": "2026-11-20",
    }
    resp = c.post("/api/v1/department/requests/", data=payload, format="json")
    assert resp.status_code == 201
    data = resp.json()
    assert data["student_id"] == 101
    assert data["status"] == "AWAITING_SCHEDULING"
    assert data["topic"] == payload["topic"]


def test_student_sees_only_own_requests(stub_iam):
    # Two requests from two different students
    SeminarSchedulingRequest.objects.create(
        student_id=101,
        student_name="Student 101",
        topic="Topic 101",
        abstract="Abstract 101",
        status="AWAITING_SCHEDULING",
    )
    SeminarSchedulingRequest.objects.create(
        student_id=202,
        student_name="Student 202",
        topic="Topic 202",
        abstract="Abstract 202",
        status="AWAITING_SCHEDULING",
    )

    c = _client(
        stub_iam,
        user_id=101,
        kind="student",
        modules=("department",),
        permissions=("department.seminar.view_self",),
    )
    resp = c.get("/api/v1/department/requests/")
    assert resp.status_code == 200
    rows = resp.json()
    results = rows.get("results", rows) if isinstance(rows, dict) else rows
    assert len(results) == 1
    assert results[0]["student_id"] == 101


def test_admin_schedules_seminar(stub_iam):
    req = SeminarSchedulingRequest.objects.create(
        student_id=101,
        student_name="Student 101",
        topic="Federated Learning in Edge IoT",
        abstract="Privacy-preserving federated aggregation across mobile devices.",
        programme="Ph.D.",
        status="AWAITING_SCHEDULING",
    )

    admin_client = _client(
        stub_iam,
        user_id=901,
        kind="staff",
        roles=("department_admin",),
        active_role="department_admin",
        modules=("department",),
        permissions=(
            "department.seminar.schedule",
            "department.seminar.view_all",
            "department.seminar.view",
        ),
    )

    # 1. Admin sees it in pending queue
    pending_resp = admin_client.get("/api/v1/department/pending/")
    assert pending_resp.status_code == 200
    p_data = pending_resp.json()
    p_results = p_data.get("results", p_data) if isinstance(p_data, dict) else p_data
    assert any(r["id"] == req.id for r in p_results)

    # 2. Admin schedules seminar
    schedule_payload = {
        "scheduled_date": "2026-11-25",
        "start_time": "14:30:00",
        "end_time": "16:00:00",
        "venue": "Seminar Hall CSE-1",
        "session_chair": "Prof. Session Chair",
        "remarks": "Approved by HOD",
    }
    sch_resp = admin_client.post(
        f"/api/v1/department/requests/{req.id}/schedule/",
        data=schedule_payload,
        format="json",
    )
    assert sch_resp.status_code == 201
    sem_data = sch_resp.json()
    assert sem_data["venue"] == "Seminar Hall CSE-1"
    assert sem_data["request_id"] == req.id

    # 3. Seminar request status updated
    req.refresh_from_db()
    assert req.status == "SCHEDULED"


def test_faculty_views_scheduled_seminars(stub_iam):
    req = SeminarSchedulingRequest.objects.create(
        student_id=101,
        student_name="Student 101",
        topic="Topic Scheduled",
        abstract="Abstract Scheduled",
        status="SCHEDULED",
    )
    GraduateSeminar.objects.create(
        request=req,
        title=req.topic,
        speaker_id=101,
        speaker_name="Student 101",
        scheduled_date=datetime.date(2026, 11, 28),
        start_time=datetime.time(11, 0),
        end_time=datetime.time(12, 0),
        venue="Room 201",
        scheduled_by_id=901,
    )

    faculty_client = _client(
        stub_iam,
        user_id=501,
        kind="faculty",
        roles=("faculty",),
        active_role="faculty",
        modules=("department",),
        permissions=("department.seminar.view",),
    )

    resp = faculty_client.get("/api/v1/department/seminars/")
    assert resp.status_code == 200
    data = resp.json()
    results = data.get("results", data) if isinstance(data, dict) else data
    assert len(results) == 1
    assert results[0]["title"] == "Topic Scheduled"


def test_unauthorized_access_denied(stub_iam):
    # User without department module grant gets 403
    unauth_client = _client(
        stub_iam,
        user_id=888,
        modules=("other_module",),
        permissions=(),
    )
    resp = unauth_client.get("/api/v1/department/requests/")
    assert resp.status_code == 403


def test_allocations_and_announcements_endpoints(stub_iam):
    admin_client = _client(
        stub_iam,
        user_id=901,
        kind="staff",
        roles=("department_admin",),
        active_role="department_admin",
        modules=("department",),
        permissions=(
            "department.allocation.view",
            "department.allocation.manage",
            "department.announcement.view",
            "department.announcement.publish",
        ),
    )

    # 1. Post TA Allocation
    ta_resp = admin_client.post(
        "/api/v1/department/allocations/ta/",
        data={
            "student_id": 101,
            "student_name": "PG Scholar 1",
            "course_code": "CS204",
            "course_name": "Algorithms",
            "faculty_name": "Prof. Algo",
            "hours_per_week": 8,
        },
        format="json",
    )
    assert ta_resp.status_code == 201

    # 2. Post Supervisor Allocation
    sup_resp = admin_client.post(
        "/api/v1/department/allocations/supervisors/",
        data={
            "student_id": 101,
            "student_name": "PG Scholar 1",
            "programme": "Ph.D.",
            "supervisor_id": 401,
            "supervisor_name": "Prof. Research",
            "thesis_topic": "Efficient Transformers",
        },
        format="json",
    )
    assert sup_resp.status_code == 201

    # 3. Post Announcement
    ann_resp = admin_client.post(
        "/api/v1/department/announcements/",
        data={
            "title": "PhD Progress Presentation Schedule",
            "content": "All scholars must present progress slides next Friday.",
            "is_pinned": True,
        },
        format="json",
    )
    assert ann_resp.status_code == 201
    assert ann_resp.json()["is_pinned"] is True
