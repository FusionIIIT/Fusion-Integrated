"""Holes found by the adversarial pass (prompt Step 5.11), each pinned before its fix."""
from datetime import timedelta

import pytest
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from core.api import csrf
from core.api.exceptions import PermissionDeniedError
from modules.placement.models import (
    Announcement,
    Company,
    InterviewRound,
    JobPosting,
    PlacementPolicy,
)

pytestmark = pytest.mark.django_db

OFFICE = ("placement.job_posting.manage", "placement.company.manage", "placement.application.view",
          "placement.interview.create", "placement.record.manage")


@pytest.fixture
def office(stub_iam):
    stub_iam(make_session(user_id=62, kind="staff", modules=("placement",),
                          permissions=OFFICE, roles=("placement officer",),
                          active_role="placement officer"))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


@pytest.fixture
def company():
    return Company.objects.create(name="Acme", slug="acme", status="active",
                                  approval_status="approved", approved_by_user_id=62)


@pytest.fixture
def posting(company):
    return JobPosting.objects.create(
        company=company, title="SDE-1", placement_year="2026-27", status="published",
        description="Build things.", closes_at=timezone.now() + timedelta(days=7),
        eligibility_rule={"gte": ["cpi", 7.0]}, created_by_user_id=62,
        published_at=timezone.now(), eligibility_rule_locked_at=timezone.now())


def _posting_body(company, **extra):
    return {"placement_year": "2026-27", "title": "SDE-1", "company_id": company.pk,
            "description": "Build things.", "eligibility_rule": {"gte": ["cpi", 7.0]},
            "closes_at": (timezone.now() + timedelta(days=7)).isoformat(), **extra}


# -- Amounts and counts cannot go negative ------------------------------------------
@pytest.mark.parametrize("field,value", [
    ("ctc_lpa", "-5"), ("stipend_pm", "-1"), ("bond_months", -1), ("seats", -1)])
def test_a_negative_amount_or_count_on_a_posting_is_400(office, company, field, value):
    # PC-BR-002: a posting carries valid content; before this fix seats=-1 was a 500.
    r = office.post("/api/v1/placement/postings", _posting_body(company, **{field: value}),
                    format="json")
    assert r.status_code == 400, r.content
    assert not JobPosting.objects.exists()


def test_a_negative_round_capacity_is_400_not_500(office, posting):
    r = office.post("/api/v1/placement/interviews/rounds", {
        "posting_id": posting.pk, "mode": "online", "meeting_url": "https://m.example/r",
        "starts_at": (timezone.now() + timedelta(days=2)).isoformat(), "capacity": -3},
        format="json")
    assert r.status_code == 400, r.content
    assert not InterviewRound.objects.exists()


def test_a_negative_off_campus_package_is_400(office, company):
    PlacementPolicy.objects.create(season="2026-27", is_active=True)
    r = office.post("/api/v1/placement/records/off-campus", {
        "season": "2026-27", "user_id": 4093, "company_id": company.pk, "ctc_lpa": "-3"},
        format="json")
    assert r.status_code == 400, r.content


# -- Nothing is scheduled in the past ------------------------------------------------
def test_a_round_that_starts_in_the_past_is_refused(office, posting):
    # PC-UC-009: a round is scheduled ahead, so candidates can attend it.
    r = office.post("/api/v1/placement/interviews/rounds", {
        "posting_id": posting.pk, "mode": "online", "meeting_url": "https://m.example/r",
        "starts_at": (timezone.now() - timedelta(days=2)).isoformat()}, format="json")
    assert r.status_code == 409, r.content
    assert r.json()["error"]["code"] == "starts_in_past"
    assert not InterviewRound.objects.exists()


def test_a_round_that_ends_before_it_starts_is_refused(office, posting):
    start = timezone.now() + timedelta(days=2)
    r = office.post("/api/v1/placement/interviews/rounds", {
        "posting_id": posting.pk, "mode": "online", "meeting_url": "https://m.example/r",
        "starts_at": start.isoformat(), "ends_at": (start - timedelta(hours=1)).isoformat()},
        format="json")
    assert r.status_code == 409, r.content
    assert r.json()["error"]["code"] == "ends_before_start"


# -- One company, one record ---------------------------------------------------------
def test_registering_a_company_twice_is_409(office, company):
    # PC-UC-014: a second record for the same company would split its history.
    r = office.post("/api/v1/placement/companies", {"name": "  acme  ", "contacts": []},
                    format="json")
    assert r.status_code == 409, r.content
    assert r.json()["error"]["code"] == "company_exists"
    assert Company.objects.count() == 1


def test_a_self_registration_under_an_existing_name_is_409(company):
    r = APIClient().post("/api/v1/placement/companies/register", {
        "name": "ACME", "contact_name": "R. Mehta", "contact_email": "hr@acme.example"},
        format="json")
    assert r.status_code == 409, r.content
    assert Company.objects.count() == 1


def test_the_database_refuses_a_duplicate_name_if_the_service_is_bypassed(company):
    with pytest.raises(IntegrityError), transaction.atomic():
        Company.objects.create(name="ACME", slug="acme-2")


# -- A cookie alone cannot write ----------------------------------------------------
def test_a_cookie_write_to_the_module_without_the_csrf_token_is_403_and_changes_nothing(stub_iam):
    stub_iam(make_session(user_id=62, kind="staff", modules=("placement",),
                          permissions=("placement.announcement.publish",)))
    client = APIClient()
    client.cookies[settings.IAM_AUTH_COOKIE_NAME] = "tok-123"
    body = {"title": "Drive", "body": "Hall 2.", "topic": "drive"}
    refused = client.post("/api/v1/placement/announcements", body, format="json")
    assert refused.status_code == 403
    assert not Announcement.objects.exists()
    allowed = client.post("/api/v1/placement/announcements", body, format="json",
                          HTTP_X_CSRF_TOKEN=csrf.token_for("tok-123"))
    assert allowed.status_code == 201


# -- Holes the security audit of the upstream module found ----------------------------
def _recruiter_world():
    from modules.placement.models import Application, Offer
    from modules.placement.services import recruiters

    company = Company.objects.create(name="Acme", slug="acme", status="active",
                                     approval_status="approved", approved_by_user_id=62)
    _, raw = recruiters.invite(company_id=company.pk, email="hire@acme.test",
                               invited_by_user_id=62)
    recruiters.accept_invite(token=raw, password=RECRUITER_PASSWORD)
    posting = JobPosting.objects.create(
        company=company, title="SDE-1", placement_year="2026-27", status="published",
        description="Build things.", closes_at=timezone.now() + timedelta(days=7),
        eligibility_rule={"gte": ["cpi", 7.0]}, created_by_user_id=62,
        published_at=timezone.now(), eligibility_rule_locked_at=timezone.now())
    app = Application.objects.create(posting=posting, user_id=4093, status="offer_issued")
    Offer.objects.create(application=app, posting=posting, user_id=4093, ctc_lpa="12.00",
                         respond_by=timezone.now() + timedelta(days=3),
                         policy_decision={"allowed": True, "facts": {"held_ctc": "30.00"}})
    session = recruiters.sign_in(email="hire@acme.test", password=RECRUITER_PASSWORD)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Recruiter {session.raw_key}")
    return company, client


RECRUITER_PASSWORD = "a-long-enough-password"


def test_a_recruiter_never_sees_the_policy_decision_on_an_offer():
    # PC-BR-009: the decision records the student's other offers, which are not the company's.
    _, recruiter = _recruiter_world()
    rows = recruiter.get("/api/v1/placement/offers").json()["results"]
    assert rows and all("policy_decision" not in r for r in rows)


def test_the_office_still_sees_the_policy_decision(office):
    _recruiter_world()
    rows = office.get("/api/v1/placement/offers").json()["results"]
    assert rows[0]["policy_decision"]["facts"] == {"held_ctc": "30.00"}


@pytest.mark.parametrize("flag", [{"is_dream_slot": True}, {"dream_slot_note": "Top tier"}])
def test_a_recruiter_cannot_declare_a_dream_slot(flag):
    # Policy rule 7: the Placement Cell declares a Dream Slot, never the company.
    company, recruiter = _recruiter_world()
    body = {"placement_year": "2026-27", "title": "SDE-2", "description": "Build.",
            "eligibility_rule": {"gte": ["cpi", 7.0]}, **flag}
    created = recruiter.post("/api/v1/placement/postings", body, format="json")
    assert created.status_code == 403, created.content
    draft = JobPosting.objects.create(company=company, title="SDE-3", placement_year="2026-27",
                                      status="draft", created_by_user_id=62)
    edited = recruiter.patch(f"/api/v1/placement/postings/{draft.pk}", flag, format="json")
    assert edited.status_code == 403, edited.content
    draft.refresh_from_db()
    assert (draft.is_dream_slot, draft.dream_slot_note) == (False, "")


def test_failures_from_another_address_do_not_lock_the_recruiter_out():
    # A stranger who knows the email must not be able to keep the account locked.
    from modules.placement.models import RecruiterLoginAttempt
    from modules.placement.services import recruiters

    _recruiter_world()
    RecruiterLoginAttempt.objects.bulk_create(
        RecruiterLoginAttempt(email="hire@acme.test", ip="203.0.113.9", outcome="bad_password")
        for _ in range(15))
    with pytest.raises(recruiters.Locked):
        recruiters.sign_in(email="hire@acme.test", password=RECRUITER_PASSWORD,
                           ip="203.0.113.9")
    assert recruiters.sign_in(email="hire@acme.test", password=RECRUITER_PASSWORD,
                              ip="198.51.100.4").raw_key


@pytest.mark.django_db(transaction=True)
def test_a_parallel_burst_of_guesses_cannot_outrun_the_lockout(monkeypatch):
    # Four failures are on record; the fifth locks, so only one more guess may be checked.
    import contextlib
    import threading

    from django.db import connection

    from modules.placement.models import RecruiterLoginAttempt
    from modules.placement.services import recruiters

    _recruiter_world()
    RecruiterLoginAttempt.objects.bulk_create(
        RecruiterLoginAttempt(email="hire@acme.test", ip="203.0.113.9", outcome="bad_password")
        for _ in range(4))
    gate = threading.Barrier(6)
    real_check = recruiters.check_lockout

    def check_together(*args, **kwargs):
        with contextlib.suppress(threading.BrokenBarrierError):
            gate.wait(timeout=5)
        return real_check(*args, **kwargs)

    def guess():
        try:
            recruiters.sign_in(email="hire@acme.test", password="wrong-guess",
                               ip="203.0.113.9")
        except (recruiters.Locked, PermissionDeniedError):
            pass
        finally:
            connection.close()

    monkeypatch.setattr(recruiters, "check_lockout", check_together)
    threads = [threading.Thread(target=guess) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert RecruiterLoginAttempt.objects.filter(outcome="bad_password").count() == 5
