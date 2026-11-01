from types import SimpleNamespace

import pytest
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from modules.gymkhana.models import (
    Club,
    ClubCoordinatorAssignment,
    MembershipApplication,
)
from modules.gymkhana.services.membership import apply, my_applications, review


pytestmark = pytest.mark.django_db


@pytest.fixture
def club():
    return Club.objects.create(
        code="coding-club",
        name="Coding Club",
        description="Competitive programming and development",
    )


@pytest.fixture
def student():
    return SimpleNamespace(user_id=101, kind="student")


@pytest.fixture
def coordinator(club):
    ClubCoordinatorAssignment.objects.create(
        club=club,
        user_id=201,
        role=ClubCoordinatorAssignment.Role.HEAD,
        is_active=True,
    )
    return SimpleNamespace(user_id=201, kind="student")


def test_student_can_apply(club, student):
    application = apply(
        actor=student,
        club_id=club.id,
        achievements="Solved 100 coding problems",
        statement="I want to contribute to the club",
    )

    assert application.student_id == student.user_id
    assert application.status == MembershipApplication.Status.OPEN
    assert application.achievements == "Solved 100 coding problems"


def test_student_cannot_apply_twice(club, student):
    apply(actor=student, club_id=club.id)

    with pytest.raises(ValidationError):
        apply(actor=student, club_id=club.id)


def test_student_can_view_only_own_applications(club, student):
    apply(actor=student, club_id=club.id)

    applications = list(my_applications(actor=student))

    assert len(applications) == 1
    assert applications[0].student_id == student.user_id


def test_application_can_be_approved(club, student, coordinator):
    application = apply(actor=student, club_id=club.id)

    reviewed = review(
        actor=coordinator,
        application_id=application.id,
        decision=MembershipApplication.Status.APPROVED,
        remarks="Welcome to the club",
    )

    assert reviewed.status == MembershipApplication.Status.APPROVED
    assert reviewed.reviewed_by == coordinator.user_id
    assert reviewed.review_remarks == "Welcome to the club"
    assert reviewed.reviewed_at is not None


def test_unassigned_user_cannot_review(club, student):
    application = apply(actor=student, club_id=club.id)
    stranger = SimpleNamespace(user_id=999, kind="student")

    with pytest.raises(PermissionDenied):
        review(
            actor=stranger,
            application_id=application.id,
            decision=MembershipApplication.Status.REJECTED,
        )


def test_application_cannot_be_reviewed_twice(club, student, coordinator):
    application = apply(actor=student, club_id=club.id)

    review(
        actor=coordinator,
        application_id=application.id,
        decision=MembershipApplication.Status.REJECTED,
    )

    with pytest.raises(ValidationError):
        review(
            actor=coordinator,
            application_id=application.id,
            decision=MembershipApplication.Status.APPROVED,
        )


def test_inactive_club_rejects_application(student, club):
    club.is_active = False
    club.save(update_fields=["is_active"])

    with pytest.raises(NotFound):
        apply(actor=student, club_id=club.id)
