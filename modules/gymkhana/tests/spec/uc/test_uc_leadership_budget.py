# ruff: noqa: N802
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models.budget import ClubBudgetRequest
from modules.gymkhana.models.club import Club, ClubLeadership

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


def test_TC_GYM_033_UC_GYM_008_Main_Success_Flow(stub_iam, confirmed_club):
    """TC-GYM-033; source_id: UC-GYM-008 Main Success Flow"""
    leader = client_for(stub_iam, 101, ("gymkhana.leadership.update",))
    response = leader.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/leadership/",
        {"new_coordinator_id": 102, "new_co_coordinator_id": 103},
        format="json",
    )
    assert response.status_code == 200
    current = set(
        ClubLeadership.objects.filter(club=confirmed_club, is_current=True).values_list("student_id", flat=True)
    )
    assert current == {102, 103}


def test_TC_GYM_034_UC_GYM_008_Exception_E1_Invalid_Proposed_Leader(stub_iam, confirmed_club):
    """TC-GYM-034; source_id: UC-GYM-008 Exception E1 Invalid Proposed Leader"""
    before = set(
        ClubLeadership.objects.filter(club=confirmed_club, is_current=True).values_list("student_id", flat=True)
    )
    leader = client_for(stub_iam, 101, ("gymkhana.leadership.update",))
    response = leader.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/leadership/",
        {"new_coordinator_id": 999, "new_co_coordinator_id": 103},
        format="json",
    )
    assert response.status_code in (400, 422)
    after = set(
        ClubLeadership.objects.filter(club=confirmed_club, is_current=True).values_list("student_id", flat=True)
    )
    assert after == before


def test_TC_GYM_035_UC_GYM_008_Exception_E1_Unauthorized_Actor(stub_iam, confirmed_club):
    """TC-GYM-035; source_id: UC-GYM-008 Exception E1 Unauthorized Actor"""
    before = set(
        ClubLeadership.objects.filter(club=confirmed_club, is_current=True).values_list("student_id", flat=True)
    )
    outsider = client_for(stub_iam, 103, ("gymkhana.leadership.update",))
    response = outsider.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/leadership/",
        {"new_coordinator_id": 102, "new_co_coordinator_id": 103},
        format="json",
    )
    assert response.status_code == 403
    after = set(
        ClubLeadership.objects.filter(club=confirmed_club, is_current=True).values_list("student_id", flat=True)
    )
    assert after == before


def test_TC_GYM_036_UC_GYM_009_Main_Success_Flow(stub_iam, confirmed_club):
    """TC-GYM-036; source_id: UC-GYM-009 Main Success Flow"""
    supporting = SimpleUploadedFile("budget.pdf", b"%PDF-1.4", content_type="application/pdf")
    leader = client_for(stub_iam, 101, ("gymkhana.budget.request",))
    response = leader.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/budgets/",
        {"amount": "1250.50", "purpose": "Equipment", "description": "Replacement", "supporting_file": supporting},
        format="multipart",
    )
    assert response.status_code == 201
    budget = ClubBudgetRequest.objects.get(club=confirmed_club)
    assert budget.amount == Decimal("1250.50")
    assert budget.status == "open"


def test_TC_GYM_037_UC_GYM_009_Exception_E1_Negative_Amount(stub_iam, confirmed_club):
    """TC-GYM-037; source_id: UC-GYM-009 Exception E1 Negative Amount"""
    supporting = SimpleUploadedFile("budget.pdf", b"%PDF-1.4", content_type="application/pdf")
    leader = client_for(stub_iam, 101, ("gymkhana.budget.request",))
    before = ClubBudgetRequest.objects.count()
    response = leader.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/budgets/",
        {"amount": "-1.00", "purpose": "Equipment", "description": "Invalid", "supporting_file": supporting},
        format="multipart",
    )
    assert response.status_code in (400, 422)
    assert ClubBudgetRequest.objects.count() == before


def test_TC_GYM_038_UC_GYM_009_Exception_E1_Missing_Supporting_File(stub_iam, confirmed_club):
    """TC-GYM-038; source_id: UC-GYM-009 Exception E1 Missing Supporting File"""
    leader = client_for(stub_iam, 101, ("gymkhana.budget.request",))
    before = ClubBudgetRequest.objects.count()
    response = leader.post(
        f"/api/v1/gymkhana/clubs/{confirmed_club.id}/budgets/",
        {"amount": "100.00", "purpose": "Equipment", "description": "Missing file"},
        format="multipart",
    )
    assert response.status_code in (400, 422)
    assert ClubBudgetRequest.objects.count() == before
