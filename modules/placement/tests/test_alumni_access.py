"""PC-UC-017: alumni read anonymised statistics and nothing else."""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.placement import registry
from modules.placement.models import Application, Company, JobPosting

pytestmark = pytest.mark.django_db

ALUMNUS = {"user_id": 880, "kind": "student", "roles": ("alumini",),
           "active_role": "alumini", "modules": ("placement",),
           "permissions": tuple(registry.ROLE_GRANTS["alumini"])}


@pytest.fixture
def alumnus(stub_iam):
    stub_iam(make_session(**ALUMNUS))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


@pytest.fixture
def posting():
    company = Company.objects.create(name="Acme", slug="acme", status="active",
                                     approval_status="approved", approved_by_user_id=9)
    return JobPosting.objects.create(
        company=company, title="SDE", placement_year="2026-27", status="published",
        description="Work.", closes_at=timezone.now(), eligibility_rule={},
        eligibility_rule_locked_at=timezone.now())


def test_pc_uc_017_alumni_grant_is_read_only_statistics():
    # PC-BR-019, PC-AFR-058, PC-AFR-059: one permission, a view., PC-UC-017, PC-CFR-018
    assert registry.ROLE_GRANTS["alumini"] == ["placement.statistic.view"]
    nav = [i["to"] for i in registry.NAV_ITEMS
           if i["required_permission"] in registry.ROLE_GRANTS["alumini"]]
    assert nav == ["/placement/reports"]


def test_pc_uc_017_alumnus_reads_anonymised_statistics(alumnus):
    # PC-UC-017
    r = alumnus.get("/api/v1/placement/stats?season=2026-27")
    assert r.status_code == 200
    assert "by_company" not in r.json()


@pytest.mark.parametrize(("method", "url", "body"), [
    ("post", "/api/v1/placement/applications/apply", {"posting_id": 1}),
    ("post", "/api/v1/placement/offers/1/respond", {"accept": True}),
    ("post", "/api/v1/placement/offers/issue", {"application_id": 1}),
    ("post", "/api/v1/placement/applications/1/transition", {"to_status": "shortlisted"}),
    ("post", "/api/v1/placement/interviews/rounds", {
        "posting_id": 1, "mode": "online", "starts_at": "2026-12-01T10:00:00Z",
        "meeting_url": "https://meet.example/x"}),
    ("post", "/api/v1/placement/announcements", {"title": "x", "body": "y"}),
    ("patch", "/api/v1/placement/records/1", {"reason": "x", "kind": "ppo"}),
])
def test_pc_br_020_alumnus_is_refused_every_active_workflow_action(alumnus, method, url, body):
    # PC-AFR-060, PC-UC-017 E2, PC-BR-020
    r = getattr(alumnus, method)(url, body, format="json")
    assert r.status_code in (403, 404)
    assert not Application.objects.exists()


def test_pc_uc_017_e1_alumnus_sees_no_application(alumnus, posting):
    # PC-UC-017
    Application.objects.create(posting=posting, user_id=1001, status="submitted")
    r = alumnus.get("/api/v1/placement/applications")
    assert r.status_code == 403
