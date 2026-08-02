"""Write authority is a permission, not read scope.

A student can SEE a published posting and their own application, which is
exactly why the write paths must ask for a code as well.
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.placement.models import (
    Application,
    Company,
    InterviewRound,
    JobPosting,
    Offer,
    PlacementPolicy,
    RecruiterAccount,
    RoundParticipation,
)
from modules.placement.services import recruiters

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-password"

STUDENT_PERMS = (
    "placement_cell.application.view_self",
    "placement_cell.application.create",
    "placement_cell.job_posting.view",
)


@pytest.fixture
def world():
    company = Company.objects.create(name="Acme", slug="acme", status="active",
                                     approval_status="approved",
                                     approved_by_user_id=9)
    PlacementPolicy.objects.create(season="2026-27", is_active=True)
    posting = JobPosting.objects.create(
        company=company, title="SDE-1", placement_year="2026-27",
        status="published", ctc_lpa="12.00", seats=2,
        description="Build things", eligibility_rule={"gte": ["cpi", 7.0]},
        closes_at=timezone.now() + timedelta(days=7),
        published_at=timezone.now(),
        eligibility_rule_locked_at=timezone.now(),
        created_by_user_id=9)
    return company, posting


def _as(stub_iam, uid, perms, kind="student"):
    stub_iam(make_session(user_id=uid, kind=kind, modules=("placement_cell",),
                          permissions=perms))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


@pytest.fixture
def recruiter_client():
    def _make(company, email="hire@acme.test"):
        account, raw = recruiters.invite(company_id=company.pk, email=email,
                                         invited_by_user_id=9)
        recruiters.accept_invite(token=raw, password=PASSWORD)
        session = recruiters.sign_in(email=email, password=PASSWORD)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Recruiter {session.raw_key}")
        return RecruiterAccount.objects.get(pk=account.pk), client
    return _make


def test_student_cannot_edit_a_published_posting(stub_iam, world):
    """Readable to every student, hence the separate check."""
    _, posting = world
    client = _as(stub_iam, 1001, STUDENT_PERMS)

    response = client.patch(f"/api/v1/placement/postings/{posting.pk}",
                            {"title": "Owned", "ctc_lpa": "99.00"},
                            format="json")

    assert response.status_code == 403
    posting.refresh_from_db()
    assert posting.title == "SDE-1"


def test_student_cannot_open_a_dream_slot_on_a_posting(stub_iam, world):
    """Policy rule 7: it decides whether a placed student may apply."""
    _, posting = world
    client = _as(stub_iam, 1001, STUDENT_PERMS)

    client.patch(f"/api/v1/placement/postings/{posting.pk}",
                 {"is_dream_slot": True}, format="json")

    posting.refresh_from_db()
    assert posting.is_dream_slot is False


def test_student_cannot_schedule_an_interview_round(stub_iam, world):
    _, posting = world
    client = _as(stub_iam, 1001, STUDENT_PERMS)

    response = client.post("/api/v1/placement/interviews/rounds", {
        "posting_id": posting.pk, "mode": "online", "kind": "tech",
        "starts_at": "2030-01-01T10:00:00Z",
        "meeting_url": "https://evil.example/join",
    }, format="json")

    assert response.status_code == 403
    assert not InterviewRound.objects.exists()


def test_student_cannot_record_their_own_interview_outcome(stub_iam, world):
    """Self-grading: the row hangs off their own application."""
    _, posting = world
    app = Application.objects.create(posting=posting, user_id=1001,
                                     status="interview_scheduled")
    round_ = InterviewRound.objects.create(
        posting=posting, seq=1, kind="tech", mode="online",
        starts_at="2030-01-01T10:00:00Z", meeting_url="https://x.invalid")
    seat = RoundParticipation.objects.create(round=round_, application=app,
                                             outcome="pending")
    client = _as(stub_iam, 1001, STUDENT_PERMS)

    response = client.post(
        f"/api/v1/placement/interviews/rounds/{round_.pk}/outcome",
        {"application_id": app.pk, "outcome": "passed", "score": "100"},
        format="json")

    assert response.status_code == 403
    seat.refresh_from_db()
    assert seat.outcome == "pending"


def test_student_cannot_add_themselves_to_a_round(stub_iam, world):
    _, posting = world
    app = Application.objects.create(posting=posting, user_id=1001,
                                     status="shortlisted")
    round_ = InterviewRound.objects.create(
        posting=posting, seq=1, kind="tech", mode="online",
        starts_at="2030-01-01T10:00:00Z", meeting_url="https://x.invalid")
    client = _as(stub_iam, 1001, STUDENT_PERMS)

    response = client.post(
        f"/api/v1/placement/interviews/rounds/{round_.pk}/candidates",
        {"application_ids": [app.pk]}, format="json")

    assert response.status_code == 403
    assert not RoundParticipation.objects.exists()


def test_student_issuing_themselves_an_offer_is_refused_cleanly(stub_iam, world):
    """403, not a 500 — the refusal must be a decision, not a crash."""
    _, posting = world
    app = Application.objects.create(posting=posting, user_id=1001,
                                     status="selected")
    client = _as(stub_iam, 1001, STUDENT_PERMS)

    response = client.post("/api/v1/placement/offers/issue",
                           {"application_id": app.pk, "ctc_lpa": "99.00"},
                           format="json")

    assert response.status_code == 403
    assert not Offer.objects.exists()


def test_read_only_reporting_staff_cannot_issue_offers(stub_iam, world):
    """`report.view` makes them staff for scoping, not for issuing."""
    _, posting = world
    app = Application.objects.create(posting=posting, user_id=1001,
                                     status="selected")
    client = _as(stub_iam, 77, ("placement_cell.report.view",), kind="staff")

    response = client.post("/api/v1/placement/offers/issue",
                           {"application_id": app.pk, "ctc_lpa": "99.00"},
                           format="json")

    assert response.status_code == 403
    assert not Offer.objects.exists()


def test_read_only_reporting_staff_cannot_edit_postings(stub_iam, world):
    _, posting = world
    client = _as(stub_iam, 77, ("placement_cell.report.view",), kind="staff")

    response = client.patch(f"/api/v1/placement/postings/{posting.pk}",
                            {"seats": 999}, format="json")

    assert response.status_code == 403
    posting.refresh_from_db()
    assert posting.seats == 2


def test_tpo_can_still_do_all_of_it(stub_iam, world):
    """The checks must not lock out the role they exist for."""
    _, posting = world
    app = Application.objects.create(posting=posting, user_id=1001,
                                     status="selected")
    client = _as(stub_iam, 9, (
        "placement_cell.job_posting.manage",
        "placement_cell.interview.schedule",
        "placement_cell.offer.issue",
        "placement_cell.application.review",
    ), kind="staff")

    assert client.patch(f"/api/v1/placement/postings/{posting.pk}",
                        {"seats": 5}, format="json").status_code == 200
    assert client.post("/api/v1/placement/interviews/rounds", {
        "posting_id": posting.pk, "mode": "online", "kind": "tech",
        "starts_at": "2030-01-01T10:00:00Z",
        "meeting_url": "https://meet.invalid/x",
    }, format="json").status_code == 201
    assert client.post("/api/v1/placement/offers/issue",
                       {"application_id": app.pk, "ctc_lpa": "18.00"},
                       format="json").status_code == 201


def test_recruiter_can_still_run_their_own_process(world, recruiter_client):
    """A recruiter holds no codes, so the check reads the lane instead."""
    company, posting = world
    _, client = recruiter_client(company)
    app = Application.objects.create(posting=posting, user_id=1001,
                                     status="selected")

    assert client.post("/api/v1/placement/interviews/rounds", {
        "posting_id": posting.pk, "mode": "online", "kind": "tech",
        "starts_at": "2030-01-01T10:00:00Z",
        "meeting_url": "https://meet.invalid/x",
    }, format="json").status_code == 201
    assert client.post("/api/v1/placement/offers/issue",
                       {"application_id": app.pk, "ctc_lpa": "18.00"},
                       format="json").status_code == 201


def test_a_bad_id_in_a_filter_is_a_400_not_a_crash(stub_iam, world):
    client = _as(stub_iam, 1001, STUDENT_PERMS)
    response = client.get("/api/v1/placement/applications?posting=not-a-number")
    assert response.status_code == 400


def test_a_recruiter_cannot_issue_an_offer_for_another_company(world,
                                                               recruiter_client):
    """The guard must not live in the view alone."""
    _, acme_posting = world
    borg = Company.objects.create(name="Borg", slug="borg", status="active",
                                  approval_status="approved",
                                  approved_by_user_id=9)
    _, borg_client = recruiter_client(borg, email="hire@borg.test")
    victim = Application.objects.create(posting=acme_posting, user_id=1001,
                                        status="selected")

    response = borg_client.post("/api/v1/placement/offers/issue",
                                {"application_id": victim.pk,
                                 "ctc_lpa": "1.00"}, format="json")

    assert response.status_code == 404
    assert not Offer.objects.exists()
