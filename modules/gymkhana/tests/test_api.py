import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.gymkhana.models import (
    Club,
    ClubCoordinatorAssignment,
    MembershipApplication,
)

pytestmark = pytest.mark.django_db

BASE = "/api/v1/gymkhana"


def api_client(stub_iam, **session_kwargs):
    stub_iam(make_session(**session_kwargs))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


@pytest.fixture
def club():
    return Club.objects.create(
        code="coding-club",
        name="Coding Club",
        description="Coding and development",
        is_active=True,
    )


@pytest.fixture
def second_club():
    return Club.objects.create(
        code="robotics-club",
        name="Robotics Club",
        description="Robotics and embedded systems",
        is_active=True,
    )


def student_client(stub_iam, user_id=1001):
    return api_client(
        stub_iam,
        user_id=user_id,
        kind="student",
        modules=("gymkhana",),
        permissions=(
            "gymkhana.club.view",
            "gymkhana.application.self",
            "gymkhana.application.create",
        ),
    )


def test_unauthenticated_request_is_rejected():
    response = APIClient().get(f"{BASE}/clubs")
    assert response.status_code == 401


def test_student_can_list_active_clubs(stub_iam, club):
    inactive = Club.objects.create(
        code="inactive-club",
        name="Inactive Club",
        is_active=False,
    )
    client = student_client(stub_iam)

    response = client.get(f"{BASE}/clubs")

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["results"]]
    assert club.id in ids
    assert inactive.id not in ids


def test_student_can_apply_and_view_own_application(stub_iam, club):
    client = student_client(stub_iam)

    response = client.post(
        f"{BASE}/applications/mine",
        {
            "club_id": club.id,
            "achievements": "Solved coding problems",
            "statement": "I want to contribute to the club.",
        },
        format="json",
    )
    assert response.status_code == 201, response.content

    application_id = response.json()["id"]
    rows = client.get(f"{BASE}/applications/mine")
    assert rows.status_code == 200
    assert [row["id"] for row in rows.json()["results"]] == [application_id]


def test_student_cannot_view_another_students_applications(
    stub_iam, club
):
    MembershipApplication.objects.create(
        club=club,
        student_id=2002,
        achievements="",
        statement="",
    )
    client = student_client(stub_iam, user_id=1001)

    response = client.get(f"{BASE}/applications/mine")

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_assigned_coordinator_can_review_application(
    stub_iam, club
):
    application = MembershipApplication.objects.create(
        club=club,
        student_id=1001,
        achievements="",
        statement="",
    )
    ClubCoordinatorAssignment.objects.create(
        club=club,
        user_id=201,
        role=ClubCoordinatorAssignment.Role.HEAD,
        is_active=True,
    )
    client = api_client(
        stub_iam,
        user_id=201,
        kind="student",
        modules=("gymkhana",),
        permissions=("gymkhana.application.review",),
    )

    response = client.post(
        f"{BASE}/applications/{application.id}/review",
        {"decision": "approved", "remarks": "Welcome!"},
        format="json",
    )

    assert response.status_code == 200, response.content
    application.refresh_from_db()
    assert application.status == MembershipApplication.Status.APPROVED
    assert application.reviewed_by == 201


def test_unassigned_coordinator_cannot_review_application(
    stub_iam, club
):
    application = MembershipApplication.objects.create(
        club=club,
        student_id=1001,
        achievements="",
        statement="",
    )
    client = api_client(
        stub_iam,
        user_id=999,
        kind="student",
        modules=("gymkhana",),
    )

    response = client.post(
        f"{BASE}/applications/{application.id}/review",
        {"decision": "rejected"},
        format="json",
    )

    assert response.status_code == 403
    application.refresh_from_db()
    assert application.status == MembershipApplication.Status.OPEN


def test_bulk_review_returns_independent_results(
    stub_iam, club, second_club
):
    allowed_application = MembershipApplication.objects.create(
        club=club,
        student_id=1001,
        achievements="",
        statement="",
    )
    other_application = MembershipApplication.objects.create(
        club=second_club,
        student_id=1002,
        achievements="",
        statement="",
    )
    ClubCoordinatorAssignment.objects.create(
        club=club,
        user_id=201,
        role=ClubCoordinatorAssignment.Role.HEAD,
        is_active=True,
    )
    client = api_client(
        stub_iam,
        user_id=201,
        kind="student",
        modules=("gymkhana",),
        permissions=("gymkhana.application.review",),
    )

    response = client.post(
        f"{BASE}/applications/bulk-review",
        {
            "items": [
                {
                    "application_id": allowed_application.id,
                    "decision": "approved",
                    "remarks": "Approved",
                },
                {
                    "application_id": other_application.id,
                    "decision": "rejected",
                },
            ]
        },
        format="json",
    )

    assert response.status_code == 200, response.content
    results = response.json()["results"]
    assert len(results) == 2
    assert results[0]["ok"] is True
    assert results[1]["ok"] is False

    allowed_application.refresh_from_db()
    other_application.refresh_from_db()
    assert allowed_application.status == MembershipApplication.Status.APPROVED
    assert other_application.status == MembershipApplication.Status.OPEN
