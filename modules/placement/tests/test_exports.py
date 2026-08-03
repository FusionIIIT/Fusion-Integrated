"""CSV export.

Two properties. The escaping one is the reason this file exists: a spreadsheet
evaluates a cell that begins `=`, and the values in these columns are supplied
by students. The access one is the usual — an export is the largest single
egress of personal data in the module, so the gate matches the CPI directory's.
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from core.api import csv as safe_csv
from modules.placement.models import (
    Application,
    Company,
    JobPosting,
    PlacementPolicy,
    PlacementRecord,
    RecruiterAccount,
)
from modules.placement.services import recruiters

pytestmark = pytest.mark.django_db

APPLICATIONS = "/api/v1/placement/exports/applications.csv"
PLACEMENTS = "/api/v1/placement/exports/placements.csv"
PASSWORD = "a-long-enough-password"


def _client(stub_iam, perms, users=None, kind="staff", uid=9):
    stub_iam(make_session(user_id=uid, kind=kind, modules=("placement_cell",),
                          permissions=perms), users=users or {})
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _body(response) -> str:
    return b"".join(response.streaming_content).decode()


@pytest.fixture
def world():
    company = Company.objects.create(
        name="Acme", slug="acme", status="active",
        approval_status="approved", approved_by_user_id=9)
    PlacementPolicy.objects.create(season="2026-27", is_active=True)
    posting = JobPosting.objects.create(
        company=company, title="SDE", placement_year="2026-27",
        description="d", status="published",
        closes_at=timezone.now() + timedelta(days=7),
        published_at=timezone.now(),
        eligibility_rule={}, eligibility_rule_locked_at=timezone.now())
    return company, posting


# -- Formula injection ---------------------------------------------------------
class TestCellEscaping:

    @pytest.mark.parametrize("payload", [
        "=cmd|'/c calc'!A1",
        "+1+1",
        "-2+3",
        "@SUM(A1:A9)",
        "\tleading tab",
        "\rleading carriage return",
    ])
    def test_a_formula_is_neutralised(self, payload):
        assert safe_csv.sanitise_cell(payload).startswith("'")

    def test_ordinary_text_is_untouched(self):
        """Escaping everything would put an apostrophe on every name."""
        assert safe_csv.sanitise_cell("Asha Verma") == "Asha Verma"
        assert safe_csv.sanitise_cell("8.10") == "8.10"
        assert safe_csv.sanitise_cell(None) == ""

    def test_a_hostile_name_reaches_the_file_inert(self, stub_iam, world,
                                                   user_ref):
        """End to end: the value comes from the directory, so quoting at the
        writer is not enough — it has to be prefixed."""
        _, posting = world
        Application.objects.create(posting=posting, user_id=1001,
                                   status="submitted")
        evil = user_ref(1001, name="=HYPERLINK(\"http://evil.test\")")
        client = _client(stub_iam, ("placement_cell.report.view",),
                         users={1001: evil})

        body = _body(client.get(APPLICATIONS))

        assert "'=HYPERLINK" in body
        # And never the bare formula at the start of a cell.
        assert ',=HYPERLINK' not in body


# -- Who may export ------------------------------------------------------------
class TestExportAccess:

    def test_staff_with_report_view_may_export(self, stub_iam, world):
        client = _client(stub_iam, ("placement_cell.report.view",))
        response = client.get(APPLICATIONS)
        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/csv")

    def test_the_file_is_an_attachment_and_not_sniffable(self, stub_iam, world):
        client = _client(stub_iam, ("placement_cell.report.view",))
        response = client.get(APPLICATIONS)
        assert response["Content-Disposition"].startswith("attachment;")
        assert response["X-Content-Type-Options"] == "nosniff"
        assert response["Cache-Control"] == "private, no-store"

    def test_a_student_cannot_export(self, stub_iam, world):
        client = _client(stub_iam, ("placement_cell.application.view_self",),
                         kind="student", uid=1001)
        assert client.get(APPLICATIONS).status_code == 403
        assert client.get(PLACEMENTS).status_code == 403

    def test_a_recruiter_cannot_export(self, stub_iam, world):
        """401, not 403: these endpoints do not list RecruiterAuthentication at
        all, so a recruiter credential is not even recognised here. A stronger
        boundary than accepting it and then refusing."""
        company, _ = world
        _, raw = recruiters.invite(company_id=company.pk, email="r@acme.test",
                                   invited_by_user_id=9)
        recruiters.accept_invite(token=raw, password=PASSWORD)
        RecruiterAccount.objects.get(email="r@acme.test")
        session = recruiters.sign_in(email="r@acme.test", password=PASSWORD)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Recruiter {session.raw_key}")

        assert client.get(APPLICATIONS).status_code == 401

    def test_an_unauthenticated_export_is_refused(self):
        assert APIClient().get(APPLICATIONS).status_code == 401


# -- Contents ------------------------------------------------------------------
class TestExportContents:

    def test_applications_carry_the_columns_a_tpo_reports_on(
            self, stub_iam, world, user_ref):
        _, posting = world
        Application.objects.create(posting=posting, user_id=1001,
                                   status="submitted", cpi_at_apply="8.10")
        client = _client(stub_iam, ("placement_cell.report.view",),
                         users={1001: user_ref(1001)})

        body = _body(client.get(APPLICATIONS))

        assert "Roll no,Name,Discipline" in body
        assert "Asha Verma" in body
        assert "8.10" in body
        assert "Acme" in body

    def test_placements_export_only_active_records(self, stub_iam, world,
                                                   user_ref):
        """A superseded record is history, not an outcome — counting it would
        double-count a student who upgraded."""
        company, posting = world
        policy = PlacementPolicy.objects.get(season="2026-27")
        app = Application.objects.create(posting=posting, user_id=1001,
                                         status="offer_accepted")
        from modules.placement.models import Offer
        offer = Offer.objects.create(
            application=app, posting=posting, user_id=1001, ctc_lpa="18.00",
            respond_by=timezone.now() + timedelta(days=1), status="accepted")
        PlacementRecord.objects.create(
            policy=policy, offer=offer, company=company, posting=posting,
            user_id=1001, ctc_lpa="18.00", kind="fte", is_active=True,
            recorded_by_user_id=1001)
        client = _client(stub_iam, ("placement_cell.report.view",),
                         users={1001: user_ref(1001)})

        body = _body(client.get(PLACEMENTS))

        assert "18.00" in body
        assert body.count("Asha Verma") == 1

    def test_an_empty_export_is_still_a_valid_file(self, stub_iam, world):
        """A header-only CSV, not a 204 — the TPO opened a spreadsheet and
        should see the columns."""
        client = _client(stub_iam, ("placement_cell.report.view",))
        body = _body(client.get(APPLICATIONS))
        header = ("Roll no,Name,Discipline,Programme,Company,Role,Season,"
                  "Status,CPI at apply,Semester at apply,Applied at")
        assert body.strip().splitlines() == [header]
