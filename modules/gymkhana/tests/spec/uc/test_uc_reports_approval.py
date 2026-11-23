# ruff: noqa: N802
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.club import Club, ClubLeadership
from modules.gymkhana.models.report import ClubEventReport

pytestmark = pytest.mark.django_db


@pytest.fixture
def gymkhana_users():
    for user_id, kind in ((101, "student"), (102, "student"), (103, "student"), (201, "faculty")):
        UserRef.objects.create(
            user_id=user_id,
            username=f"u{user_id}",
            display_name=f"User {user_id}",
            kind=kind,
            discipline="CSE" if kind == "student" else "",
            batch_year=2023 if kind == "student" else None,
        )
    return 101, 102, 103, 201


@pytest.fixture
def confirmed_club(gymkhana_users):
    club = Club.objects.create(
        name="Literature Club",
        category="Cultural",
        description="Books",
        faculty_councillor_id=201,
        status="confirmed",
    )
    ClubLeadership.objects.create(club=club, student_id=101, role="coordinator", is_current=True)
    ClubLeadership.objects.create(club=club, student_id=102, role="co_coordinator", is_current=True)
    return club


def client_for(stub_iam, user_id, permissions=(), kind="student"):
    stub_iam(make_session(user_id=user_id, kind=kind, modules=("gymkhana",), permissions=tuple(permissions)))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock_token")
    return client


def test_TC_GYM_039_UC_GYM_010_Main_Success_Flow(stub_iam, confirmed_club):
    """TC-GYM-039; source_id: UC-GYM-010 Main Success Flow"""
    report_file = SimpleUploadedFile("report.pdf", b"%PDF-1.4 report", content_type="application/pdf")
    leader = client_for(stub_iam, 101, ("gymkhana.report.submit",))
    response = leader.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/reports/submit/",
        {
            "title": "Annual event",
            "description": "Event outcomes",
            "student_incharge_id": 103,
            "event_name": "Annual event",
            "event_datetime": "2026-12-01T10:00:00Z",
            "report_file": report_file,
        },
        format="multipart",
    )
    assert response.status_code == 201
    report = ClubEventReport.objects.get(club=confirmed_club)
    assert report.student_incharge_id == 103
    assert bool(report.report_file)


def test_TC_GYM_040_UC_GYM_010_Exception_E1_Missing_Report_File(stub_iam, confirmed_club):
    """TC-GYM-040; source_id: UC-GYM-010 Exception E1 Missing Report File"""
    leader = client_for(stub_iam, 101, ("gymkhana.report.submit",))
    before = ClubEventReport.objects.count()
    response = leader.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/reports/submit/",
        {
            "title": "Missing file",
            "description": "No file",
            "student_incharge_id": 103,
            "event_name": "Annual event",
            "event_datetime": "2026-12-01T10:00:00Z",
        },
        format="multipart",
    )
    assert response.status_code in (400, 422)
    assert ClubEventReport.objects.count() == before


def test_TC_GYM_041_UC_GYM_010_Exception_E1_Invalid_Required_References(stub_iam, confirmed_club):
    """TC-GYM-041; source_id: UC-GYM-010 Exception E1 Invalid Required References"""
    report_file = SimpleUploadedFile("report.pdf", b"%PDF-1.4 report", content_type="application/pdf")
    leader = client_for(stub_iam, 101, ("gymkhana.report.submit",))
    before = ClubEventReport.objects.count()
    response = leader.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/reports/submit/",
        {
            "title": "Invalid reference",
            "description": "Invalid student incharge",
            "student_incharge_id": 999,
            "event_name": "Annual event",
            "event_datetime": "2026-12-01T10:00:00Z",
            "report_file": report_file,
        },
        format="multipart",
    )
    assert response.status_code in (400, 422)
    assert ClubEventReport.objects.count() == before


def test_TC_GYM_042_UC_GYM_011_Main_Success_Flow(stub_iam, gymkhana_users):
    """TC-GYM-042; source_id: UC-GYM-011 Main Success Flow"""
    club = Club.objects.create(
        name="Open Club",
        category="Sports",
        description="Pending",
        faculty_councillor_id=201,
        status="open",
    )
    ClubLeadership.objects.create(club=club, student_id=101, role="coordinator", is_current=True)
    ClubLeadership.objects.create(club=club, student_id=102, role="co_coordinator", is_current=True)
    admin = client_for(stub_iam, 201, ("gymkhana.club.approve",), "faculty")
    response = admin.post(f"/api/v1/gymkhana/clubs/{club.id}/confirm/")
    assert response.status_code == 200
    club.refresh_from_db()
    assert club.status == "confirmed"


def test_TC_GYM_043_UC_GYM_011_Exception_E1_Club_Not_Open(stub_iam, confirmed_club):
    """TC-GYM-043; source_id: UC-GYM-011 Exception E1 Club Not Open"""
    admin = client_for(stub_iam, 201, ("gymkhana.club.approve",), "faculty")
    response = admin.post(f"/api/v1/gymkhana/clubs/{confirmed_club.id}/confirm/")
    assert response.status_code == 409
    confirmed_club.refresh_from_db()
    assert confirmed_club.status == "confirmed"


def test_TC_GYM_044_UC_GYM_011_Exception_E1_Update_Failure(stub_iam, gymkhana_users):
    """TC-GYM-044; source_id: UC-GYM-011 Exception E1 Update Failure"""
    pytest.skip("NOT_AUTOMATED: club status update storage failure has no injectable interface")


def test_TC_GYM_045_UC_GYM_012_Main_Success_Flow(stub_iam, confirmed_club):
    """TC-GYM-045; source_id: UC-GYM-012 Main Success Flow"""
    ClubEventReport.objects.create(
        club=confirmed_club,
        title="Annual report",
        description="Outcomes",
        student_incharge_id=103,
        event_name="Annual event",
        event_datetime=timezone.now(),
        report_file=SimpleUploadedFile("report.pdf", b"%PDF-1.4", content_type="application/pdf"),
        submitted_by_id=101,
    )
    councillor = client_for(stub_iam, 201, ("gymkhana.report.review",), "faculty")
    response = councillor.get(f"/api/v1/gymkhana/clubs/{confirmed_club.id}/reports/")
    assert response.status_code == 200
    assert len(response.json()) == 1
    report_download = councillor.get(
        f"/api/v1/gymkhana/reports/{ClubEventReport.objects.get(club=confirmed_club).id}/file/"
    )
    assert report_download.status_code == 200


def test_TC_GYM_046_UC_GYM_012_Exception_E1_Unauthorized_Faculty(stub_iam, confirmed_club):
    """TC-GYM-046; source_id: UC-GYM-012 Exception E1 Unauthorized Faculty"""
    report = ClubEventReport.objects.create(
        club=confirmed_club,
        title="Private report",
        description="Outcomes",
        student_incharge_id=103,
        event_name="Annual event",
        event_datetime=timezone.now(),
        report_file=SimpleUploadedFile("report.pdf", b"%PDF-1.4", content_type="application/pdf"),
        submitted_by_id=101,
    )
    outsider = client_for(stub_iam, 202, ("gymkhana.report.review",), "faculty")
    response = outsider.get(f"/api/v1/gymkhana/clubs/{confirmed_club.id}/reports/")
    assert response.status_code == 200
    assert response.json() == []
    download = outsider.get(f"/api/v1/gymkhana/reports/{report.id}/file/")
    assert download.status_code == 404
