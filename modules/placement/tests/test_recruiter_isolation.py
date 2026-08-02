"""The recruiter boundary.

This is the module's externally-reachable surface, so it gets the harshest
tests. The property under examination throughout: **a recruiter at company A
cannot observe anything belonging to company B, and cannot tell whether it
exists.**
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.placement.models import (
    Application,
    Company,
    JobPosting,
    RecruiterAccount,
    RecruiterLoginAttempt,
    RecruiterSession,
    StudentProfile,
)
from modules.placement.services import recruiters

pytestmark = pytest.mark.django_db

PASSWORD = "a-long-enough-password"


def make_company(name, approved=True):
    return Company.objects.create(
        name=name, slug=name.lower(), status="active",
        approval_status="approved" if approved else "pending",
        approved_by_user_id=9 if approved else None)


def make_recruiter(company, email):
    account, raw = recruiters.invite(company_id=company.pk, email=email,
                                     invited_by_user_id=9)
    recruiters.accept_invite(token=raw, password=PASSWORD)
    return RecruiterAccount.objects.get(pk=account.pk)


def recruiter_client(account):
    session = recruiters.sign_in(email=account.email, password=PASSWORD)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Recruiter {session.raw_key}")
    return c


def make_posting(company, title="SDE", status="published"):
    return JobPosting.objects.create(
        company=company, title=title, placement_year="2026-27",
        description="Build things.", status=status,
        closes_at=timezone.now() + timedelta(days=7),
        eligibility_rule={"gte": ["cpi", 7.0]},
        eligibility_rule_locked_at=timezone.now() if status == "published" else None)


@pytest.fixture
def two_companies():
    a, b = make_company("Acme"), make_company("Borg")
    ra, rb = make_recruiter(a, "hire@acme.test"), make_recruiter(b, "hire@borg.test")
    pa, pb = make_posting(a, "Acme SDE"), make_posting(b, "Borg SDE")
    app_a = Application.objects.create(posting=pa, user_id=1001,
                                       status="submitted")
    app_b = Application.objects.create(posting=pb, user_id=1002,
                                       status="submitted")
    return {"a": a, "b": b, "ra": ra, "rb": rb, "pa": pa, "pb": pb,
            "app_a": app_a, "app_b": app_b}


# -- Cross-company isolation ---------------------------------------------------
class TestCrossCompanyIsolation:

    def test_a_recruiter_lists_only_their_own_postings(self, two_companies):
        c = recruiter_client(two_companies["ra"])
        rows = c.get("/api/v1/placement/postings").json()["results"]
        assert [r["title"] for r in rows] == ["Acme SDE"]

    def test_another_companys_posting_is_404_not_403(self, two_companies):
        c = recruiter_client(two_companies["ra"])
        foreign = c.get(f"/api/v1/placement/postings/{two_companies['pb'].pk}")
        missing = c.get("/api/v1/placement/postings/999999")
        assert foreign.status_code == 404
        assert missing.status_code == 404

    def test_a_recruiter_lists_only_their_own_applicants(self, two_companies):
        c = recruiter_client(two_companies["ra"])
        rows = c.get("/api/v1/placement/applications").json()["results"]
        assert [r["id"] for r in rows] == [two_companies["app_a"].pk]

    def test_a_recruiter_cannot_act_on_another_companys_application(
            self, two_companies):
        c = recruiter_client(two_companies["ra"])
        r = c.post(
            f"/api/v1/placement/applications/{two_companies['app_b'].pk}/transition",
            {"to_status": "under_review"}, format="json")
        assert r.status_code == 404

    def test_a_recruiter_cannot_issue_an_offer_to_another_companys_applicant(
            self, two_companies):
        c = recruiter_client(two_companies["ra"])
        r = c.post("/api/v1/placement/offers/issue",
                   {"application_id": two_companies["app_b"].pk}, format="json")
        assert r.status_code == 404

    def test_company_id_in_the_body_cannot_reassign_a_posting(self, two_companies):
        """The credential decides the company, never the payload. Otherwise
        `company_id` is a one-field privilege escalation."""
        c = recruiter_client(two_companies["ra"])
        r = c.post("/api/v1/placement/postings",
                   {"company_id": two_companies["b"].pk, "title": "Injected",
                    "placement_year": "2026-27"}, format="json")
        assert r.status_code == 201
        assert r.json()["company"]["id"] == two_companies["a"].pk

    def test_a_recruiter_sees_only_their_own_company_record(self, two_companies):
        c = recruiter_client(two_companies["ra"])
        rows = c.get("/api/v1/placement/companies").json()["results"]
        assert [r["id"] for r in rows] == [two_companies["a"].pk]

    def test_a_recruiter_cannot_read_a_non_applicants_profile(self, two_companies):
        StudentProfile.objects.create(user_id=5555)
        c = recruiter_client(two_companies["ra"])
        assert c.get("/api/v1/placement/profiles/5555").status_code == 404

    def test_a_recruiter_can_read_their_own_applicants_profile(self, two_companies):
        StudentProfile.objects.create(user_id=1001)
        c = recruiter_client(two_companies["ra"])
        assert c.get("/api/v1/placement/profiles/1001").status_code == 200

    def test_a_recruiter_cannot_read_another_companys_applicants_profile(
            self, two_companies):
        StudentProfile.objects.create(user_id=1002)
        c = recruiter_client(two_companies["ra"])
        assert c.get("/api/v1/placement/profiles/1002").status_code == 404

    def test_a_recruiter_sees_no_internal_announcements(self, two_companies):
        from modules.placement.models import Announcement
        Announcement.objects.create(title="Internal", body="x",
                                    published_at=timezone.now())
        c = recruiter_client(two_companies["ra"])
        assert c.get("/api/v1/placement/announcements").json()["results"] == []

    def test_draft_applications_are_invisible_to_the_recruiter(self, two_companies):
        """A student composing an application has not submitted it."""
        Application.objects.create(posting=two_companies["pa"], user_id=7777,
                                   status="draft")
        c = recruiter_client(two_companies["ra"])
        rows = c.get("/api/v1/placement/applications").json()["results"]
        assert 7777 not in [r["candidate"]["user_id"] for r in rows]


# -- The credential itself -----------------------------------------------------
class TestRecruiterCredential:

    def test_a_recruiter_token_is_rejected_under_the_token_scheme(
            self, two_companies):
        session = recruiters.sign_in(email="hire@acme.test", password=PASSWORD)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Token {session.raw_key}")
        # Falls through to the IAM authenticator, which does not know it.
        assert c.get("/api/v1/placement/postings").status_code in (401, 403)

    def test_an_institute_session_is_rejected_under_the_recruiter_scheme(
            self, stub_iam, two_companies):
        stub_iam(make_session(user_id=9, modules=("placement_cell",)))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Recruiter abc")
        assert c.get("/api/v1/placement/postings").status_code == 401

    def test_a_recruiter_holds_no_permissions_at_all(self, two_companies):
        """Their reach is the scoped queryset, never a permission grant — so a
        misconfigured role cannot widen it."""
        from modules.placement.authentication import RecruiterPrincipal
        p = RecruiterPrincipal(account_id=1, company_id=1, email="x@y.z",
                               display_name="X")
        assert p.has_permission("placement_cell.application.view") is False
        assert p.has_any_permission("anything", "at", "all") is False
        assert p.has_module("placement_cell") is True
        assert p.has_module("hr") is False

    def test_a_recruiter_cannot_reach_the_iam_directory_or_me(self, two_companies):
        c = recruiter_client(two_companies["ra"])
        assert c.get("/api/v1/me").status_code in (401, 403)
        assert c.get("/api/v1/directory/users?q=a").status_code in (401, 403)

    def test_revoking_the_session_takes_effect_immediately(self, two_companies):
        account = two_companies["ra"]
        session = recruiters.sign_in(email=account.email, password=PASSWORD)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Recruiter {session.raw_key}")
        assert c.get("/api/v1/placement/postings").status_code == 200

        recruiters.sign_out(session_key=session.raw_key)
        assert c.get("/api/v1/placement/postings").status_code == 401

    def test_an_expired_session_is_rejected(self, two_companies):
        session = recruiters.sign_in(email="hire@acme.test", password=PASSWORD)
        RecruiterSession.objects.filter(pk=session.key).update(
            expires_at=timezone.now() - timedelta(seconds=1))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Recruiter {session.raw_key}")
        assert c.get("/api/v1/placement/postings").status_code == 401

    def test_deactivating_the_account_cuts_off_a_live_session(self, two_companies):
        account = two_companies["ra"]
        c = recruiter_client(account)
        assert c.get("/api/v1/placement/postings").status_code == 200

        RecruiterAccount.objects.filter(pk=account.pk).update(is_active=False)
        assert c.get("/api/v1/placement/postings").status_code == 401

    def test_un_approving_the_company_cuts_off_a_live_session(self, two_companies):
        """Checked per request, not merely at login — otherwise a blacklisted
        company keeps working until their eight-hour session lapses."""
        c = recruiter_client(two_companies["ra"])
        assert c.get("/api/v1/placement/postings").status_code == 200

        Company.objects.filter(pk=two_companies["a"].pk).update(
            status="blacklisted")
        assert c.get("/api/v1/placement/postings").status_code == 401


# -- Sign-in -------------------------------------------------------------------
class TestRecruiterSignIn:

    def test_every_failure_says_the_same_thing(self, two_companies):
        from core.api.exceptions import PermissionDeniedError
        messages = set()
        for email, password in (("nobody@nowhere.test", PASSWORD),
                                ("hire@acme.test", "wrong-password")):
            with pytest.raises(PermissionDeniedError) as exc:
                recruiters.sign_in(email=email, password=password)
            messages.add(str(exc.value))
        assert len(messages) == 1, "failure messages must not distinguish cases"

    def test_failures_are_recorded_with_their_real_cause(self, two_companies):
        from core.api.exceptions import PermissionDeniedError
        for email, password in (("nobody@nowhere.test", PASSWORD),
                                ("hire@acme.test", "wrong-password")):
            with pytest.raises(PermissionDeniedError):
                recruiters.sign_in(email=email, password=password)
        # Indistinguishable outside, fully distinguishable in the audit log —
        # which is what makes stuffing detectable.
        assert set(RecruiterLoginAttempt.objects.values_list("outcome", flat=True)) \
            == {"unknown_account", "bad_password"}

    def test_lockout_after_repeated_failures(self, two_companies):
        for _ in range(5):
            RecruiterLoginAttempt.objects.create(email="hire@acme.test",
                                                 outcome="bad_password")
        with pytest.raises(recruiters.Locked):
            recruiters.sign_in(email="hire@acme.test", password=PASSWORD)

    def test_a_recruiter_at_an_unapproved_company_cannot_sign_in(self):
        from core.api.exceptions import ConflictError
        pending = make_company("Pending", approved=False)
        with pytest.raises(ConflictError):
            recruiters.invite(company_id=pending.pk, email="x@pending.test",
                              invited_by_user_id=9)


# -- Invitation ----------------------------------------------------------------
class TestInvitation:

    def test_the_raw_token_is_never_stored(self):
        company = make_company("Init")
        account, raw = recruiters.invite(company_id=company.pk,
                                         email="a@init.test",
                                         invited_by_user_id=9)
        account.refresh_from_db()
        assert raw not in account.invite_token_hash
        assert raw not in str(account.__dict__)

    def test_an_invitation_is_single_use(self):
        from core.api.exceptions import PermissionDeniedError
        company = make_company("Once")
        _, raw = recruiters.invite(company_id=company.pk, email="a@once.test",
                                   invited_by_user_id=9)
        recruiters.accept_invite(token=raw, password=PASSWORD)
        with pytest.raises(PermissionDeniedError):
            recruiters.accept_invite(token=raw, password="another-password-1")

    def test_an_expired_invitation_is_refused(self):
        from core.api.exceptions import PermissionDeniedError
        company = make_company("Expired")
        account, raw = recruiters.invite(company_id=company.pk,
                                         email="a@expired.test",
                                         invited_by_user_id=9)
        RecruiterAccount.objects.filter(pk=account.pk).update(
            invite_expires_at=timezone.now() - timedelta(seconds=1))
        with pytest.raises(PermissionDeniedError):
            recruiters.accept_invite(token=raw, password=PASSWORD)

    def test_a_guessed_token_and_an_expired_one_are_indistinguishable(self):
        from core.api.exceptions import PermissionDeniedError
        company = make_company("Same")
        account, raw = recruiters.invite(company_id=company.pk,
                                         email="a@same.test",
                                         invited_by_user_id=9)
        RecruiterAccount.objects.filter(pk=account.pk).update(
            invite_expires_at=timezone.now() - timedelta(seconds=1))
        messages = set()
        for token in (raw, "totally-made-up-token"):
            with pytest.raises(PermissionDeniedError) as exc:
                recruiters.accept_invite(token=token, password=PASSWORD)
            messages.add(str(exc.value))
        assert len(messages) == 1

    def test_a_short_password_is_refused(self):
        from core.api.exceptions import ConflictError
        company = make_company("Short")
        _, raw = recruiters.invite(company_id=company.pk, email="a@short.test",
                                   invited_by_user_id=9)
        with pytest.raises(ConflictError):
            recruiters.accept_invite(token=raw, password="short")

    def test_one_address_cannot_belong_to_two_companies(self):
        from core.api.exceptions import ConflictError
        a, b = make_company("A1"), make_company("B1")
        recruiters.invite(company_id=a.pk, email="shared@x.test",
                          invited_by_user_id=9)
        with pytest.raises(ConflictError):
            recruiters.invite(company_id=b.pk, email="shared@x.test",
                              invited_by_user_id=9)

    def test_the_password_is_argon2(self, settings):
        """Test settings swap in MD5 for speed, so this restores the real
        hashers — otherwise it asserts whatever the runner happens to set."""
        settings.PASSWORD_HASHERS = [
            "django.contrib.auth.hashers.Argon2PasswordHasher",
            "django.contrib.auth.hashers.PBKDF2PasswordHasher",
        ]
        company = make_company("Hash")
        _, raw = recruiters.invite(company_id=company.pk, email="a@hash.test",
                                   invited_by_user_id=9)
        account = recruiters.accept_invite(token=raw, password=PASSWORD)
        assert account.password_hash.startswith("argon2")


# -- The session cookie --------------------------------------------------------
class TestRecruiterCookie:
    """The portal SPA authenticates by cookie, so the token never lives in
    JS-readable storage. Both transports must behave identically."""

    def test_login_sets_an_httponly_cookie_and_does_not_return_the_token(
            self, two_companies):
        c = APIClient()
        r = c.post("/api/v1/placement/recruiters/login",
                   {"email": "hire@acme.test", "password": PASSWORD},
                   format="json")
        assert r.status_code == 200
        # The value must not travel in the body — that is the whole point.
        assert "token" not in r.json()
        cookie = r.cookies["recruiter_session"]
        assert cookie["httponly"]
        assert cookie["samesite"] == "Lax"
        assert cookie["path"] == "/api/v1/placement"

    def test_the_cookie_authenticates_subsequent_requests(self, two_companies):
        c = APIClient()
        c.post("/api/v1/placement/recruiters/login",
               {"email": "hire@acme.test", "password": PASSWORD}, format="json")
        r = c.get("/api/v1/placement/postings")
        assert r.status_code == 200
        assert [x["title"] for x in r.json()["results"]] == ["Acme SDE"]

    def test_the_cookie_is_still_company_scoped(self, two_companies):
        c = APIClient()
        c.post("/api/v1/placement/recruiters/login",
               {"email": "hire@acme.test", "password": PASSWORD}, format="json")
        assert c.get(
            f"/api/v1/placement/postings/{two_companies['pb'].pk}"
        ).status_code == 404

    def test_logout_revokes_the_session_not_only_the_cookie(self, two_companies):
        c = APIClient()
        login = c.post("/api/v1/placement/recruiters/login",
                       {"email": "hire@acme.test", "password": PASSWORD},
                       format="json")
        key = login.cookies["recruiter_session"].value
        c.post("/api/v1/placement/recruiters/logout", {}, format="json",
               HTTP_X_CSRF_TOKEN=login.json()["csrf_token"])

        # Clearing the cookie is cosmetic; the row must be dead too, or a
        # copied value keeps working after "sign out".
        replay = APIClient()
        replay.credentials(HTTP_AUTHORIZATION=f"Recruiter {key}")
        assert replay.get("/api/v1/placement/postings").status_code == 401

    def test_an_institute_header_does_not_fall_back_to_the_recruiter_cookie(
            self, two_companies):
        """A request must not authenticate as two different principals
        depending on which class runs first."""
        c = APIClient()
        c.post("/api/v1/placement/recruiters/login",
               {"email": "hire@acme.test", "password": PASSWORD}, format="json")
        c.credentials(HTTP_AUTHORIZATION="Token some-institute-token")
        assert c.get("/api/v1/placement/postings").status_code in (401, 403)
