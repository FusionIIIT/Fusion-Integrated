"""The four TPO reports and the chairman's oversight view."""
from decimal import Decimal as D

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.placement.domain import reports
from modules.placement.models import (
    Company,
    PlacementPolicy,
    PlacementRecord,
    PlacementRegistration,
)

pytestmark = pytest.mark.django_db

REPORTS = ("placement.report.view",)


def _client(stub_iam, **kw):
    kw.setdefault("modules", ("placement",))
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _season(season, registered, placements):
    """`placements` is a list of (company name, ctc)."""
    policy = PlacementPolicy.objects.create(season=season)
    for i in range(registered):
        PlacementRegistration.objects.create(
            policy=policy, user_id=7000 + i, status="registered",
            registered_at=timezone.now())
    for i, (name, ctc) in enumerate(placements):
        company, _ = Company.objects.get_or_create(
            slug=name.lower(), defaults={"name": name, "status": "active",
                                         "approval_status": "approved",
                                         "approved_by_user_id": 9})
        PlacementRecord.objects.create(policy=policy, user_id=7000 + i, company=company,
                                       ctc_lpa=D(ctc), source="off_campus")
    return policy


class TestDomain:

    def test_a_package_on_a_band_edge_falls_in_the_higher_band(self):
        # PC-AFR-035, PC-CFR-011
        bands = reports.salary_distribution([D("4.99"), D("5"), D("29.99"), D("30"), D("75")])
        assert [b["placed"] for b in bands] == [1, 1, 0, 0, 1, 2]
        assert bands[0]["band"] == "0-5 LPA"
        assert bands[-1]["band"] == "30+ LPA"

    def test_no_packages_gives_every_band_at_zero(self):
        assert [b["placed"] for b in reports.salary_distribution([])] == [0] * 6

    def test_a_season_with_nobody_registered_has_no_rate(self):
        assert reports.placement_rate(0, 0) is None
        assert reports.placement_rate(1, 3) == 33.3

    def test_trends_are_oldest_first_and_fill_missing_seasons_with_zero(self):
        rows = reports.season_trends(["2026-27", "2025-26"], {"2025-26": 4},
                                     {"2025-26": 2}, {"2025-26": 1})
        assert [r.season for r in rows] == ["2025-26", "2026-27"]
        assert (rows[0].placement_rate, rows[0].companies_participated) == (50.0, 1)
        assert (rows[1].registered, rows[1].placed, rows[1].placement_rate) == (0, 0, None)


class TestTpoReports:

    def test_tpo_gets_the_success_rate_and_the_salary_distribution(self, stub_iam):
        # PC-UC-011, PC-AFR-033, PC-AFR-035
        _season("2026-27", 4, [("Acme", "6.00"), ("Acme", "12.00"), ("Bolt", "31.00")])
        body = _client(stub_iam, user_id=62, kind="staff", permissions=REPORTS).get(
            "/api/v1/placement/stats?season=2026-27").json()
        assert body["placement_rate"] == 75.0
        assert {b["band"]: b["placed"] for b in body["salary_distribution"]} == {
            "0-5 LPA": 0, "5-10 LPA": 1, "10-15 LPA": 1, "15-20 LPA": 0,
            "20-30 LPA": 0, "30+ LPA": 1}

    def test_tpo_gets_company_participation_and_employment_trends(self, stub_iam):
        # PC-AFR-034, PC-AFR-036
        _season("2025-26", 4, [("Acme", "6.00"), ("Bolt", "7.00")])
        _season("2026-27", 5, [("Acme", "8.00")])
        rows = _client(stub_iam, user_id=62, kind="staff", permissions=REPORTS).get(
            "/api/v1/placement/stats/trends").json()["results"]
        assert rows == [
            {"season": "2025-26", "registered": 4, "placed": 2,
             "placement_rate": 50.0, "companies_participated": 2},
            {"season": "2026-27", "registered": 5, "placed": 1,
             "placement_rate": 20.0, "companies_participated": 1},
        ]

    def test_an_unregistered_persons_record_is_not_counted_in_a_trend(self, stub_iam):
        policy = _season("2026-27", 2, [("Acme", "6.00")])
        acme = Company.objects.get(slug="acme")
        PlacementRecord.objects.create(policy=policy, user_id=9999, company=acme,
                                       ctc_lpa=D("50"), source="off_campus")
        rows = _client(stub_iam, user_id=62, kind="staff", permissions=REPORTS).get(
            "/api/v1/placement/stats/trends").json()["results"]
        assert rows[0]["placed"] == 1


class TestChairmanOversight:

    def test_chairman_sees_statistics_reports_and_company_engagement(self, stub_iam):
        # PC-UC-012, PC-AFR-037, PC-AFR-038, PC-AFR-039, PC-CFR-012
        _season("2026-27", 3, [("Acme", "6.00"), ("Acme", "9.00")])
        c = _client(stub_iam, user_id=70, kind="faculty", roles=("placement chairman",),
                    active_role="placement chairman", permissions=REPORTS)
        body = c.get("/api/v1/placement/stats?season=2026-27").json()
        assert body["placed"] == 2
        assert body["by_company"] == [{"company__name": "Acme", "placed": 2,
                                       "top": 9.0}]
        assert c.get("/api/v1/placement/stats/trends").json()["results"][0][
            "companies_participated"] == 1


class TestRefusals:

    def test_a_student_cannot_read_the_trend_report(self, stub_iam):
        # PC-UC-011 E1, PC-BR-023
        c = _client(stub_iam, user_id=1001,
                    permissions=("placement.own_application.view",))
        assert c.get("/api/v1/placement/stats/trends").status_code == 403

    def test_a_student_asking_for_stats_gets_no_salary_distribution(self, stub_iam):
        # PC-BR-016, PC-UC-024 E1
        _season("2026-27", 4, [("Acme", "6.00")])
        body = _client(stub_iam, user_id=1001,
                       permissions=("placement.own_application.view",)).get(
            "/api/v1/placement/stats?season=2026-27").json()
        assert "salary_distribution" not in body
        assert "by_company" not in body
