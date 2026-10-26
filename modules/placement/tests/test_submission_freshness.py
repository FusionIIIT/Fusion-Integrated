from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import ConflictError
from modules.placement.domain import state_machine as sm
from modules.placement.models import (
    Application,
    Company,
    JobPosting,
    PlacementPolicy,
    StudentProfile,
)
from modules.placement.services import applications

pytestmark = pytest.mark.django_db


@pytest.fixture
def draft_application():
    season = "2026-27"
    PlacementPolicy.objects.create(season=season)
    company = Company.objects.create(name="Acme", slug="acme", status="active")
    now = timezone.now()
    posting = JobPosting.objects.create(
        company=company, title="SDE", description="Role details",
        placement_year=season, status="published",
        published_at=now, opens_at=now - timedelta(days=1),
        closes_at=now + timedelta(days=1), eligibility_rule={},
        eligibility_rule_locked_at=now,
    )
    StudentProfile.objects.create(user_id=1001, is_complete=True)
    return Application.objects.create(
        posting=posting, user_id=1001, status=sm.DRAFT,
        eligibility_snapshot={"is_eligible": True},
    )


def _student():
    return make_principal(
        user_id=1001, kind="student", modules=("placement_cell",),
        permissions=("placement_cell.application.create",),
    )


def test_submit_rejects_when_fresh_evaluation_is_ineligible(
        draft_application, monkeypatch):
    monkeypatch.setattr(applications, "evaluate_for", lambda **_: {
        "is_eligible": False, "failed": [{"field": "cpi"}],
    })

    with pytest.raises(ConflictError) as exc:
        applications.transition(
            application_id=draft_application.pk, to_status=sm.SUBMITTED,
            actor=_student())

    assert exc.value.code == "not_eligible"
    draft_application.refresh_from_db()
    assert draft_application.status == sm.DRAFT


def test_submit_freezes_fresh_eligibility_snapshot(
        draft_application, monkeypatch):
    fresh = {
        "is_eligible": True,
        "failed": [],
        "season_decision": {"allowed": True},
        "cpi": "8.25",
        "semester": 6,
        "declared_seq": 4,
    }
    monkeypatch.setattr(applications, "evaluate_for", lambda **_: fresh)

    submitted = applications.transition(
        application_id=draft_application.pk, to_status=sm.SUBMITTED,
        actor=_student())

    submitted.refresh_from_db()
    assert submitted.status == sm.SUBMITTED
    assert submitted.eligibility_snapshot == fresh
    assert submitted.cpi_at_apply == Decimal("8.25")
    assert submitted.semester_at_apply == 6
    assert submitted.standing_declared_seq_at_apply == 4


