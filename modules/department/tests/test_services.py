"""Tests for Department service layer."""
import datetime
import pytest
from core.api.exceptions import BadRequestError, NotFoundError

from modules.department.services import seminar_service, allocation_service
from modules.department.models.seminar import (
    SeminarSchedulingRequest,
    GraduateSeminar,
    SeminarSchedulingHistory,
)
from modules.department.models.allocation import (
    ThesisSupervisorAllocation,
    TAAllocation,
)
from modules.department.models.announcement import DepartmentAnnouncement

pytestmark = pytest.mark.django_db


class DummyActor:
    def __init__(self, user_id=101, display_name="Student User", permissions=()):
        self.user_id = user_id
        self.display_name = display_name
        self.permissions = set(permissions)

    def has_permission(self, perm: str) -> bool:
        return perm in self.permissions


def test_submit_seminar_request_success():
    actor = DummyActor(user_id=101, display_name="PG Student")
    req = seminar_service.submit_seminar_request(
        actor=actor,
        topic="Machine Learning in Signal Processing",
        abstract="Comprehensive study of adaptive filtering using transformers.",
        programme="M.Tech",
        department="CSE",
        preferred_date=datetime.date(2026, 11, 20),
        faculty_advisor_id=202,
        faculty_advisor_name="Dr. Advisor",
    )
    assert req.pk is not None
    assert req.student_id == 101
    assert req.status == "AWAITING_SCHEDULING"
    assert req.topic == "Machine Learning in Signal Processing"


def test_submit_seminar_request_rejects_non_pg():
    actor = DummyActor(user_id=102, display_name="UG Student")
    with pytest.raises(BadRequestError) as exc:
        seminar_service.submit_seminar_request(
            actor=actor,
            topic="Valid Topic Name",
            abstract="Valid abstract",
            programme="B.Tech",
        )
    assert "OA-BR-61" in str(exc.value)


def test_submit_seminar_request_prevents_duplicate_pending():
    actor = DummyActor(user_id=103, display_name="Student Double")
    seminar_service.submit_seminar_request(
        actor=actor,
        topic="First Seminar Topic",
        abstract="First Abstract Description",
        programme="M.Tech",
    )
    with pytest.raises(BadRequestError) as exc:
        seminar_service.submit_seminar_request(
            actor=actor,
            topic="Second Seminar Topic",
            abstract="Second Abstract Description",
            programme="M.Tech",
        )
    assert "already have a pending seminar request" in str(exc.value)


def test_schedule_graduate_seminar_success():
    student = DummyActor(user_id=104, display_name="Candidate Student")
    admin = DummyActor(user_id=301, display_name="Dept Admin")

    req = seminar_service.submit_seminar_request(
        actor=student,
        topic="Quantum Cryptography Basics",
        abstract="Study of BB84 protocol and quantum key distribution.",
        programme="Ph.D.",
    )

    sem_date = datetime.date(2026, 11, 25)
    seminar = seminar_service.schedule_graduate_seminar(
        actor=admin,
        request_id=req.pk,
        scheduled_date=sem_date,
        start_time=datetime.time(15, 0),
        end_time=datetime.time(16, 30),
        venue="Auditorium Hall B",
        session_chair="Prof. Chairman",
        remarks="Approved by committee",
    )

    assert seminar.pk is not None
    assert seminar.request_id == req.pk
    assert seminar.venue == "Auditorium Hall B"
    assert seminar.scheduled_by_id == 301

    # Request state transitioned to SCHEDULED
    req.refresh_from_db()
    assert req.status == "SCHEDULED"

    # History logged (AFR-OAP-048)
    logs = SeminarSchedulingHistory.objects.filter(seminar=seminar)
    assert logs.count() == 1
    assert logs.first().action == "SCHEDULED"
    assert "Auditorium Hall B" in logs.first().details


def test_schedule_graduate_seminar_invalid_state():
    student = DummyActor(user_id=105, display_name="Student 105")
    admin = DummyActor(user_id=301, display_name="Dept Admin")

    req = seminar_service.submit_seminar_request(
        actor=student,
        topic="Topic Once",
        abstract="Abstract Once",
        programme="M.Tech",
    )

    # First schedule works
    seminar_service.schedule_graduate_seminar(
        actor=admin,
        request_id=req.pk,
        scheduled_date=datetime.date(2026, 11, 25),
        start_time=datetime.time(10, 0),
        end_time=datetime.time(11, 0),
        venue="Room 101",
    )

    # Second attempt to schedule fails
    with pytest.raises(BadRequestError) as exc:
        seminar_service.schedule_graduate_seminar(
            actor=admin,
            request_id=req.pk,
            scheduled_date=datetime.date(2026, 11, 26),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0),
            venue="Room 102",
        )
    assert "invalid_state_transition" in exc.value.code


def test_reject_seminar_request():
    student = DummyActor(user_id=106, display_name="Student 106")
    admin = DummyActor(user_id=301, display_name="Dept Admin")

    req = seminar_service.submit_seminar_request(
        actor=student,
        topic="Topic to Reject",
        abstract="Abstract Description",
        programme="M.Tech",
    )

    rejected = seminar_service.reject_seminar_request(
        actor=admin,
        request_id=req.pk,
        reason="Abstract lacks adequate research motivation.",
    )
    assert rejected.status == "REJECTED"
    assert "lacks adequate" in rejected.rejection_reason


def test_cancel_seminar_request_by_student():
    student = DummyActor(user_id=107, display_name="Student 107")
    req = seminar_service.submit_seminar_request(
        actor=student,
        topic="Topic to Cancel",
        abstract="Abstract Description",
        programme="M.Tech",
    )

    cancelled = seminar_service.cancel_seminar_request(actor=student, request_id=req.pk)
    assert cancelled.status == "CANCELLED"


def test_allocations_and_announcements():
    admin = DummyActor(user_id=301, display_name="Dept Admin")

    # Supervisor allocation
    sup = allocation_service.allocate_thesis_supervisor(
        actor=admin,
        student_id=201,
        student_name="PG Scholar",
        programme="Ph.D.",
        supervisor_id=401,
        supervisor_name="Dr. Senior Prof",
        thesis_topic="Graph Neural Networks",
    )
    assert sup.pk is not None
    assert sup.supervisor_name == "Dr. Senior Prof"

    # TA allocation
    ta = allocation_service.allocate_teaching_assistant(
        actor=admin,
        student_id=201,
        student_name="PG Scholar",
        course_code="CS301",
        course_name="Software Engineering",
        faculty_id=401,
        faculty_name="Dr. Senior Prof",
        hours_per_week=8,
    )
    assert ta.pk is not None
    assert ta.course_code == "CS301"

    # Announcement
    ann = allocation_service.create_announcement(
        actor=admin,
        title="Department Townhall Meeting",
        content="All students and faculty are invited to the semester townhall.",
        is_pinned=True,
    )
    assert ann.pk is not None
    assert ann.is_pinned is True
