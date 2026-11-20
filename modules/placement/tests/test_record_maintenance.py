"""TPO maintenance of placement records, through the HTTP API."""
from decimal import Decimal as D

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.placement.models import (
    Company,
    PlacementPolicy,
    PlacementRecord,
    PlacementRecordRevision,
)

pytestmark = pytest.mark.django_db

URL = "/api/v1/placement/records"
TPO = ("placement.record.manage", "placement.report.view")


def _client(stub_iam, **kw):
    kw.setdefault("modules", ("placement",))
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _tpo(stub_iam):
    return _client(stub_iam, user_id=62, kind="staff", roles=("placement officer",),
                   active_role="placement officer", permissions=TPO)


@pytest.fixture
def policy():
    return PlacementPolicy.objects.create(season="2026-27")


@pytest.fixture
def company():
    return Company.objects.create(name="Acme", slug="acme", status="active",
                                  approval_status="approved", approved_by_user_id=9)


@pytest.fixture
def record(policy, company):
    return PlacementRecord.objects.create(
        policy=policy, user_id=4021, company=company, source="off_campus",
        ctc_lpa=D("12.00"), kind="fte", recorded_by_user_id=62)


class TestOrdinaryCase:

    def test_tpo_corrects_a_student_record_and_the_old_value_is_kept(self, stub_iam, record):
        # PC-UC-010, PC-BR-029, PC-AFR-031, PC-CFR-010
        r = _tpo(stub_iam).patch(f"{URL}/{record.pk}", {
            "reason": "The company revised the offer letter.", "ctc_lpa": "14.50"},
            format="json")
        assert r.status_code == 200
        assert r.json()["ctc_lpa"] == "14.50"
        record.refresh_from_db()
        assert record.ctc_lpa == D("14.50")
        revision = PlacementRecordRevision.objects.get(record=record)
        assert revision.before["ctc_lpa"] == "12.00"
        assert revision.after["ctc_lpa"] == "14.50"
        assert revision.by_user_id == 62

    def test_tpo_lists_records_and_reads_a_records_history(self, stub_iam, record):
        # PC-AFR-030
        c = _tpo(stub_iam)
        c.patch(f"{URL}/{record.pk}", {"reason": "Wrong kind.", "kind": "ppo"},
                format="json")
        rows = c.get(f"{URL}/office?season=2026-27&user_id=4021").json()["results"]
        assert [(x["id"], x["kind"]) for x in rows] == [(record.pk, "ppo")]
        history = c.get(f"{URL}/{record.pk}/revisions").json()["results"]
        assert history[0]["reason"] == "Wrong kind."


class TestAlumniRecords:

    def test_tpo_records_and_updates_a_placement_for_an_alumnus(self, stub_iam, policy, company):
        # PC-AFR-032, PC-UC-010 A1
        c = _tpo(stub_iam)
        made = c.post(f"{URL}/off-campus", {
            "season": "2026-27", "user_id": 880, "company_id": company.pk,
            "ctc_lpa": "9.00"}, format="json")
        assert made.status_code == 201
        r = c.patch(f"{URL}/{made.json()['id']}", {
            "reason": "Alumnus moved to a new package.", "ctc_lpa": "11.00"},
            format="json")
        assert r.status_code == 200
        assert PlacementRecord.objects.get(user_id=880).ctc_lpa == D("11.00")

    def test_an_alumnus_cannot_change_a_record(self, stub_iam, record):
        # PC-BR-029 exception, PC-AFR-059
        c = _client(stub_iam, user_id=880, roles=("alumini",), active_role="alumini",
                    permissions=("placement.statistic.view",))
        r = c.patch(f"{URL}/{record.pk}", {"reason": "x", "ctc_lpa": "99"},
                    format="json")
        assert r.status_code == 403
        record.refresh_from_db()
        assert record.ctc_lpa == D("12.00")


class TestRefusals:

    @pytest.mark.parametrize("perms", [
        ("placement.own_application.view",),
        ("placement.report.view",),
        ("placement.application.review", "placement.job_posting.manage"),
    ])
    def test_without_record_manage_a_correction_is_403_and_nothing_changes(
            self, stub_iam, record, perms):
        # PC-BR-024, PC-AFR-063, PC-UC-010 E1
        c = _client(stub_iam, user_id=5, permissions=perms)
        r = c.patch(f"{URL}/{record.pk}", {"reason": "x", "ctc_lpa": "1"},
                    format="json")
        assert r.status_code == 403
        assert not PlacementRecordRevision.objects.exists()

    def test_a_student_cannot_list_office_records(self, stub_iam, record):
        # PC-BR-023, PC-AFR-062
        c = _client(stub_iam, user_id=4021,
                    permissions=("placement.own_application.view",))
        assert c.get(f"{URL}/office").status_code == 403
        assert c.get(f"{URL}/{record.pk}/revisions").status_code == 403

    def test_a_blank_reason_is_refused(self, stub_iam, record):
        r = _tpo(stub_iam).patch(f"{URL}/{record.pk}", {"reason": "  ", "kind": "ppo"},
                                 format="json")
        assert r.status_code == 400

    def test_a_correction_that_changes_nothing_is_409(self, stub_iam, record):
        r = _tpo(stub_iam).patch(f"{URL}/{record.pk}", {
            "reason": "Same.", "ctc_lpa": "12.00"}, format="json")
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "nothing_changed"

    def test_an_unknown_record_is_404(self, stub_iam):
        c = _tpo(stub_iam)
        r = c.patch(f"{URL}/999", {"reason": "x", "kind": "ppo"}, format="json")
        assert r.status_code == 404
        assert c.get(f"{URL}/999/revisions").status_code == 404

    def test_a_bad_user_filter_is_400_not_500(self, stub_iam, record):
        assert _tpo(stub_iam).get(f"{URL}/office?user_id=abc").status_code == 400

    def test_a_negative_package_is_400(self, stub_iam, record):
        r = _tpo(stub_iam).patch(f"{URL}/{record.pk}", {
            "reason": "Typo.", "ctc_lpa": "-1"}, format="json")
        assert r.status_code == 400


class TestActiveFlag:

    def test_deactivating_then_reactivating_is_recorded_twice(self, stub_iam, record):
        c = _tpo(stub_iam)
        assert c.patch(f"{URL}/{record.pk}", {"reason": "Did not join.",
                                              "is_active": False},
                       format="json").status_code == 200
        assert c.patch(f"{URL}/{record.pk}", {"reason": "Joined after all.",
                                              "is_active": True},
                       format="json").status_code == 200
        assert PlacementRecordRevision.objects.filter(record=record).count() == 2

    def test_reactivating_beside_another_active_record_is_409(
            self, stub_iam, record, policy, company):
        PlacementRecord.objects.filter(pk=record.pk).update(is_active=False)
        PlacementRecord.objects.create(
            policy=policy, user_id=4021, company=company, source="off_campus",
            kind="fte")
        r = _tpo(stub_iam).patch(f"{URL}/{record.pk}", {
            "reason": "Restore.", "is_active": True}, format="json")
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "already_placed"
