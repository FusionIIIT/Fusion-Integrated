"""Documents as Google Drive links.

Validation is now about the URL: a link a TPO will click is a phishing vector
unless it is parsed to a file id and rebuilt. Authorisation is unchanged and
matters more — someone else's resume is absent, not forbidden.
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from core.api.exceptions import ConflictError, NotFoundError
from core.files import drive
from modules.placement.models import (
    Application,
    Company,
    JobPosting,
    ProfileDocument,
    RecruiterAccount,
    StudentProfile,
)
from modules.placement.services import documents, recruiters

pytestmark = pytest.mark.django_db

FILE_ID = "1A2b3C4d5E6f7G8h9I0jKlMnOpQrStUv"
LINK = f"https://drive.google.com/file/d/{FILE_ID}/view?usp=sharing"
OTHER_LINK = "https://drive.google.com/file/d/9Z8y7X6w5V4u3T2s1R0qPoNmLkJiHgFe/view"
STUDENT = 1001
PASSWORD = "a-long-enough-password"


def attach(kind="resume", url=LINK, user_id=STUDENT, title="CV"):
    return documents.attach_link(user_id=user_id, kind=kind, url=url,
                                 title=title)


def student_client(stub_iam, user_id=STUDENT):
    stub_iam(make_session(user_id=user_id, modules=("placement_cell",),
                          permissions=("placement_cell.application.view_self",)))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


# -- Link validation -----------------------------------------------------------
class TestLinkValidation:

    @pytest.mark.parametrize("url", [
        f"https://drive.google.com/file/d/{FILE_ID}/view?usp=sharing",
        f"https://drive.google.com/file/d/{FILE_ID}/view",
        f"https://drive.google.com/open?id={FILE_ID}",
        f"https://drive.google.com/uc?id={FILE_ID}&export=download",
        f"https://docs.google.com/document/d/{FILE_ID}/edit",
        f"https://docs.google.com/spreadsheets/d/{FILE_ID}/edit#gid=0",
    ])
    def test_the_shapes_google_actually_hands_out(self, url):
        assert drive.parse(url).file_id == FILE_ID

    def test_the_stored_url_is_rebuilt_not_echoed(self):
        """Tracking and redirect parameters are dropped, not stored."""
        ref = drive.parse(
            f"https://drive.google.com/file/d/{FILE_ID}/view"
            "?usp=sharing&rm=minimal#heading=evil")
        assert ref.url == f"https://drive.google.com/file/d/{FILE_ID}/view"

    @pytest.mark.parametrize(("url", "code"), [
        ("https://evil.example/resume.pdf", "url_not_drive"),
        ("https://drive.google.com.evil.example/file/d/x/view", "url_not_drive"),
        ("http://drive.google.com/file/d/abc/view", "url_not_https"),
        ("javascript:alert(1)", "url_not_https"),
        ("data:text/html,<script>alert(1)</script>", "url_not_https"),
        ("", "url_required"),
    ])
    def test_anything_that_is_not_a_drive_link_is_refused(self, url, code):
        with pytest.raises(drive.InvalidDriveLink) as exc:
            drive.parse(url)
        assert exc.value.code == code

    def test_credentials_in_the_url_cannot_disguise_the_host(self):
        """Reads as Drive to a human, resolves to evil.example in a browser."""
        with pytest.raises(drive.InvalidDriveLink) as exc:
            drive.parse(
                f"https://drive.google.com@evil.example/file/d/{FILE_ID}/view")
        assert exc.value.code == "url_not_drive"

    def test_a_folder_link_is_refused(self):
        """A folder exposes everything in it, not the one document."""
        with pytest.raises(drive.InvalidDriveLink) as exc:
            drive.parse("https://drive.google.com/drive/folders/" + FILE_ID)
        assert exc.value.code == "url_is_folder"

    def test_a_drive_url_with_no_file_id_is_refused(self):
        with pytest.raises(drive.InvalidDriveLink) as exc:
            drive.parse("https://drive.google.com/drive/my-drive")
        assert exc.value.code == "url_no_file_id"

    def test_an_absurdly_long_url_never_reaches_the_database(self):
        with pytest.raises(drive.InvalidDriveLink) as exc:
            drive.parse("https://drive.google.com/file/d/" + "a" * 600 + "/view")
        assert exc.value.code == "url_too_long"


# -- Profile effects -------------------------------------------------------------
class TestProfileEffects:

    def test_attaching_a_resume_moves_completeness(self):
        profile, _ = StudentProfile.objects.get_or_create(user_id=STUDENT)
        before = profile.completeness_percent
        attach()
        profile.refresh_from_db()
        assert profile.completeness_percent > before

    def test_a_new_resume_supersedes_the_old_one(self):
        first = attach()
        second = attach(url=OTHER_LINK)
        first.refresh_from_db()
        assert first.is_active is False
        assert second.is_active is True

    def test_the_same_link_twice_is_not_duplicated(self):
        """A double-clicked button, not a second document."""
        assert attach().pk == attach().pk

    def test_removing_deactivates_but_keeps_the_row(self):
        doc = attach()
        documents.remove(document_id=doc.pk, user_id=STUDENT)
        doc.refresh_from_db()
        assert doc.is_active is False
        assert ProfileDocument.objects.filter(pk=doc.pk).exists()

    def test_removing_someone_elses_document_is_a_404(self):
        doc = attach()
        with pytest.raises(NotFoundError):
            documents.remove(document_id=doc.pk, user_id=2002)

    def test_the_document_count_is_capped(self, monkeypatch):
        monkeypatch.setattr(documents, "MAX_DOCUMENTS_PER_PROFILE", 2)
        attach(kind="other", url=LINK)
        attach(kind="other", url=OTHER_LINK)
        with pytest.raises(ConflictError):
            attach(kind="other",
                   url="https://drive.google.com/file/d/thirdthirdthird123/view")

    def test_an_unknown_kind_is_refused(self):
        with pytest.raises(ConflictError):
            attach(kind="passport")


# -- Reaching a document -----------------------------------------------------------
class TestDownloadAuthorisation:

    def test_the_owner_is_redirected_to_their_document(self, stub_iam):
        doc = attach()
        r = student_client(stub_iam).get(
            f"/api/v1/placement/documents/{doc.pk}/download")
        assert r.status_code == 302
        assert r["Location"] == f"https://drive.google.com/file/d/{FILE_ID}/view"

    def test_the_redirect_tells_google_nothing(self, stub_iam):
        """Drive is not handed the portal page that sent them."""
        doc = attach()
        r = student_client(stub_iam).get(
            f"/api/v1/placement/documents/{doc.pk}/download")
        assert r["Referrer-Policy"] == "no-referrer"
        assert r["Cache-Control"] == "private, no-store"

    def test_another_students_document_is_404_not_403(self, stub_iam):
        """403 would confirm the row exists, which is itself a disclosure."""
        doc = attach()
        other = student_client(stub_iam, user_id=2002)
        assert other.get(
            f"/api/v1/placement/documents/{doc.pk}/download").status_code == 404

    def test_an_unauthenticated_download_is_refused(self):
        doc = attach()
        assert APIClient().get(
            f"/api/v1/placement/documents/{doc.pk}/download").status_code == 401

    def test_a_deactivated_document_is_no_longer_reachable(self, stub_iam):
        doc = attach()
        documents.remove(document_id=doc.pk, user_id=STUDENT)
        assert student_client(stub_iam).get(
            f"/api/v1/placement/documents/{doc.pk}/download").status_code == 404


class TestTheLinkIsNotHandedOut:
    """The URL is a capability with no revocation, so it must not travel in a
    payload that is not re-authorised on every use."""

    def test_the_list_payload_carries_no_drive_url(self, stub_iam):
        attach()
        body = str(student_client(stub_iam).get(
            "/api/v1/placement/documents").json())
        assert FILE_ID not in body
        assert "drive.google.com" not in body

    def test_the_list_points_at_the_authorising_endpoint_instead(self, stub_iam):
        doc = attach()
        row = student_client(stub_iam).get(
            "/api/v1/placement/documents").json()["results"][0]
        assert row["download_url"] == (
            f"/api/v1/placement/documents/{doc.pk}/download")
        assert row["is_link"] is True


class TestRecruiterDownloadScope:

    @pytest.fixture
    def world(self):
        company = Company.objects.create(
            name="Acme", slug="acme", status="active",
            approval_status="approved", approved_by_user_id=9)
        other = Company.objects.create(
            name="Borg", slug="borg", status="active",
            approval_status="approved", approved_by_user_id=9)
        posting = JobPosting.objects.create(
            company=company, title="SDE", placement_year="2026-27",
            description="d", status="published",
            closes_at=timezone.now() + timedelta(days=5),
            eligibility_rule={}, eligibility_rule_locked_at=timezone.now())
        account, raw = recruiters.invite(company_id=company.pk,
                                         email="a@acme.test",
                                         invited_by_user_id=9)
        recruiters.accept_invite(token=raw, password=PASSWORD)
        _, raw2 = recruiters.invite(company_id=other.pk, email="b@borg.test",
                                    invited_by_user_id=9)
        recruiters.accept_invite(token=raw2, password=PASSWORD)
        return {"posting": posting,
                "acme": RecruiterAccount.objects.get(pk=account.pk),
                "borg": RecruiterAccount.objects.get(email="b@borg.test")}

    def client_for(self, account):
        session = recruiters.sign_in(email=account.email, password=PASSWORD)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Recruiter {session.raw_key}")
        return c

    def test_a_recruiter_can_read_their_applicants_resume(self, world):
        doc = attach()
        Application.objects.create(posting=world["posting"], user_id=STUDENT,
                                   status="submitted")
        r = self.client_for(world["acme"]).get(
            f"/api/v1/placement/documents/{doc.pk}/download")
        assert r.status_code == 302

    def test_a_recruiter_cannot_read_a_non_applicants_resume(self, world):
        doc = attach()
        assert self.client_for(world["acme"]).get(
            f"/api/v1/placement/documents/{doc.pk}/download").status_code == 404

    def test_another_companys_recruiter_cannot_read_it(self, world):
        doc = attach()
        Application.objects.create(posting=world["posting"], user_id=STUDENT,
                                   status="submitted")
        assert self.client_for(world["borg"]).get(
            f"/api/v1/placement/documents/{doc.pk}/download").status_code == 404

    def test_a_recruiter_cannot_read_an_arbitrary_document_kind(self, world):
        """Applying exposes a resume, not the student's whole file drawer."""
        doc = attach(kind="other", url=OTHER_LINK)
        Application.objects.create(posting=world["posting"], user_id=STUDENT,
                                   status="submitted")
        assert self.client_for(world["acme"]).get(
            f"/api/v1/placement/documents/{doc.pk}/download").status_code == 404


class TestAttachEndpoint:

    def test_attaching_over_http(self, stub_iam):
        r = student_client(stub_iam).post(
            "/api/v1/placement/documents",
            {"kind": "resume", "url": LINK, "title": "My CV"}, format="json")
        assert r.status_code == 201
        assert r.json()["is_link"] is True
        assert ProfileDocument.objects.filter(user_id=STUDENT).count() == 1

    def test_a_missing_url_is_refused(self, stub_iam):
        r = student_client(stub_iam).post(
            "/api/v1/placement/documents", {"kind": "resume"}, format="json")
        assert r.status_code == 400

    def test_a_hostile_link_is_refused_over_http(self, stub_iam):
        """The endpoint, not only the parser, has to say no."""
        r = student_client(stub_iam).post(
            "/api/v1/placement/documents",
            {"kind": "resume", "url": "https://evil.example/phish"},
            format="json")
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "url_not_drive"
        assert not ProfileDocument.objects.exists()
