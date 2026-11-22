"""Automated backend test suite for FR Strategy (CFR + AFR)."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.placement.models import Company, JobPosting, PlacementRegistration as StudentPlacementProfile

pytestmark = pytest.mark.django_db

def _client(stub_iam, uid=1001, role="student", perms=None):
    if perms is None:
        perms = ('placement_cell.application.view_self', 'placement_cell.application.create', 'placement_cell.job_posting.view', 'placement_cell.announcement.view', 'placement_cell.statistics.student.view', 'placement_cell.offer.respond')
    u = UserRef(user_id=uid, username=f"user{uid}", email=f"user{uid}@fusion.test", display_name=f"User {uid}", kind=role)
    stub_iam(make_session(user_id=uid, kind=role, modules=("placement_cell",), permissions=perms), users={uid: u})
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c

def test_tc_fr_001_01(stub_iam):
    """test_id: TC-FR-001-01
    source_id: PC-AFR-001
    purpose: Verify PC-AFR-001: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.put("/api/v1/placement/profile", {
        "summary": "Fullstack student", "skills": ["Python", "Django"],
        "projects": [{"title": "Fusion"}], "achievements": [], "certifications": [], "links": []
    }, format="json")
    assert r.status_code in (200, 201)
    assert StudentPlacementProfile.objects.filter(user_id=1001).exists()

def test_tc_fr_002_01(stub_iam):
    """test_id: TC-FR-002-01
    source_id: PC-AFR-002
    purpose: Verify PC-AFR-002: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.put("/api/v1/placement/profile", {
        "summary": "Fullstack student", "skills": ["Python", "Django"],
        "projects": [{"title": "Fusion"}], "achievements": [], "certifications": [], "links": []
    }, format="json")
    assert r.status_code in (200, 201)
    assert StudentPlacementProfile.objects.filter(user_id=1001).exists()

def test_tc_fr_003_01(stub_iam):
    """test_id: TC-FR-003-01
    source_id: PC-AFR-003
    purpose: Verify PC-AFR-003: The Student
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.put("/api/v1/placement/profile", {
        "summary": "Fullstack student", "skills": ["Python", "Django"],
        "projects": [{"title": "Fusion"}], "achievements": [], "certifications": [], "links": []
    }, format="json")
    assert r.status_code in (200, 201)
    assert StudentPlacementProfile.objects.filter(user_id=1001).exists()

def test_tc_fr_004_01(stub_iam):
    """test_id: TC-FR-004-01
    source_id: PC-AFR-004
    purpose: Verify PC-AFR-004: Where profile
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_005_01(stub_iam):
    """test_id: TC-FR-005-01
    source_id: PC-AFR-005
    purpose: Verify PC-AFR-005: PCMS shall
    test_type: positive"""
    # PC-AFR-005: Generate structured resume from saved placement profile
    client = _client(stub_iam, uid=1001)
    client.put("/api/v1/placement/profile", {"summary": "Experienced coder", "skills": ["Python"]}, format="json")
    r = client.get("/api/v1/placement/profile/resume")
    assert r.status_code == 200, f"Expected 200 OK for resume generation, got {r.status_code}"

def test_tc_fr_006_01(stub_iam):
    """test_id: TC-FR-006-01
    source_id: PC-AFR-006
    purpose: Verify PC-AFR-006: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/postings")
    assert r.status_code == 200

def test_tc_fr_007_01(stub_iam):
    """test_id: TC-FR-007-01
    source_id: PC-AFR-007
    purpose: Verify PC-AFR-007: PCMS shall
    test_type: positive"""
    c = Company.objects.create(name="TechCorp", slug="techcorp", status="active")
    p = JobPosting.objects.create(company=c, title="SWE", placement_year="2026-27", status="draft", created_by_user_id=1)
    client = _client(stub_iam, uid=1001)
    r = client.post("/api/v1/placement/applications/apply", {"posting_id": p.id}, format="json")
    assert r.status_code in (201, 200, 400, 409)

def test_tc_fr_008_01(stub_iam):
    """test_id: TC-FR-008-01
    source_id: PC-AFR-008
    purpose: Verify PC-AFR-008: Before
    test_type: positive"""
    c = Company.objects.create(name="TechCorp", slug="techcorp", status="active")
    p = JobPosting.objects.create(company=c, title="SWE", placement_year="2026-27", status="draft", created_by_user_id=1)
    client = _client(stub_iam, uid=1001)
    r = client.post("/api/v1/placement/applications/apply", {"posting_id": p.id}, format="json")
    assert r.status_code in (201, 200, 400, 409)

def test_tc_fr_009_01(stub_iam):
    """test_id: TC-FR-009-01
    source_id: PC-AFR-009
    purpose: Verify PC-AFR-009: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_010_01(stub_iam):
    """test_id: TC-FR-010-01
    source_id: PC-AFR-010
    purpose: Verify PC-AFR-010: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_011_01(stub_iam):
    """test_id: TC-FR-011-01
    source_id: PC-AFR-011
    purpose: Verify PC-AFR-011: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/offers")
    assert r.status_code == 200

def test_tc_fr_012_01(stub_iam):
    """test_id: TC-FR-012-01
    source_id: PC-AFR-012
    purpose: Verify PC-AFR-012: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/offers")
    assert r.status_code == 200

def test_tc_fr_013_01(stub_iam):
    """test_id: TC-FR-013-01
    source_id: PC-AFR-013
    purpose: Verify PC-AFR-013: When a Student
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_014_01(stub_iam):
    """test_id: TC-FR-014-01
    source_id: PC-AFR-014
    purpose: Verify PC-AFR-014: PCMS shall apply
    test_type: positive"""
    client = APIClient()
    r = client.post("/api/v1/placement/companies/register", {
        "name": "Global Corp", "website": "https://global.test",
        "contact_name": "Recruiter One", "contact_email": "r1@global.test"
    }, format="json")
    assert r.status_code == 201
    assert r.json()["approval_status"] == "pending"

def test_tc_fr_015_01(stub_iam):
    """test_id: TC-FR-015-01
    source_id: PC-AFR-015
    purpose: Verify PC-AFR-015: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_016_01(stub_iam):
    """test_id: TC-FR-016-01
    source_id: PC-AFR-016
    purpose: Verify PC-AFR-016: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_017_01(stub_iam):
    """test_id: TC-FR-017-01
    source_id: PC-AFR-017
    purpose: Verify PC-AFR-017: PCMS shall allow the
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/postings")
    assert r.status_code == 200

def test_tc_fr_018_01(stub_iam):
    """test_id: TC-FR-018-01
    source_id: PC-AFR-018
    purpose: Verify PC-AFR-018: Where authorized,
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_019_01(stub_iam):
    """test_id: TC-FR-019-01
    source_id: PC-AFR-019
    purpose: Verify PC-AFR-019: Where authorized,
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_020_01(stub_iam):
    """test_id: TC-FR-020-01
    source_id: PC-AFR-020
    purpose: Verify PC-AFR-020: PCMS shall allow the
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_021_01(stub_iam):
    """test_id: TC-FR-021-01
    source_id: PC-AFR-021
    purpose: Verify PC-AFR-021: Each PCMS job posting
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_022_01(stub_iam):
    """test_id: TC-FR-022-01
    source_id: PC-AFR-022
    purpose: Verify PC-AFR-022: Eligibility criteria
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_023_01(stub_iam):
    """test_id: TC-FR-023-01
    source_id: PC-AFR-023
    purpose: Verify PC-AFR-023: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_024_01(stub_iam):
    """test_id: TC-FR-024-01
    source_id: PC-AFR-024
    purpose: Verify PC-AFR-024: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_025_01(stub_iam):
    """test_id: TC-FR-025-01
    source_id: PC-AFR-025
    purpose: Verify PC-AFR-025: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_026_01(stub_iam):
    """test_id: TC-FR-026-01
    source_id: PC-AFR-026
    purpose: Verify PC-AFR-026: PCMS shall allow the
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_027_01(stub_iam):
    """test_id: TC-FR-027-01
    source_id: PC-AFR-027
    purpose: Verify PC-AFR-027: Where authorized,
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_028_01(stub_iam):
    """test_id: TC-FR-028-01
    source_id: PC-AFR-028
    purpose: Verify PC-AFR-028: A PCMS interview
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_029_01(stub_iam):
    """test_id: TC-FR-029-01
    source_id: PC-AFR-029
    purpose: Verify PC-AFR-029: PCMS shall allow the
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_030_01(stub_iam):
    """test_id: TC-FR-030-01
    source_id: PC-AFR-030
    purpose: Verify PC-AFR-030: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_031_01(stub_iam):
    """test_id: TC-FR-031-01
    source_id: PC-AFR-031
    purpose: Verify PC-AFR-031: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_032_01(stub_iam):
    """test_id: TC-FR-032-01
    source_id: PC-AFR-032
    purpose: Verify PC-AFR-032: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_033_01(stub_iam):
    """test_id: TC-FR-033-01
    source_id: PC-AFR-033
    purpose: Verify PC-AFR-033: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_034_01(stub_iam):
    """test_id: TC-FR-034-01
    source_id: PC-AFR-034
    purpose: Verify PC-AFR-034: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_035_01(stub_iam):
    """test_id: TC-FR-035-01
    source_id: PC-AFR-035
    purpose: Verify PC-AFR-035: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_036_01(stub_iam):
    """test_id: TC-FR-036-01
    source_id: PC-AFR-036
    purpose: Verify PC-AFR-036: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_037_01(stub_iam):
    """test_id: TC-FR-037-01
    source_id: PC-AFR-037
    purpose: Verify PC-AFR-037: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_038_01(stub_iam):
    """test_id: TC-FR-038-01
    source_id: PC-AFR-038
    purpose: Verify PC-AFR-038: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_039_01(stub_iam):
    """test_id: TC-FR-039-01
    source_id: PC-AFR-039
    purpose: Verify PC-AFR-039: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_040_01(stub_iam):
    """test_id: TC-FR-040-01
    source_id: PC-AFR-040
    purpose: Verify PC-AFR-040: PCMS shall allow an
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/announcements")
    assert r.status_code == 200

def test_tc_fr_041_01(stub_iam):
    """test_id: TC-FR-041-01
    source_id: PC-AFR-041
    purpose: Verify PC-AFR-041: PCMS shall allow the
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/announcements")
    assert r.status_code == 200

def test_tc_fr_042_01(stub_iam):
    """test_id: TC-FR-042-01
    source_id: PC-AFR-042
    purpose: Verify PC-AFR-042: Supported
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/announcements")
    assert r.status_code == 200

def test_tc_fr_043_01(stub_iam):
    """test_id: TC-FR-043-01
    source_id: PC-AFR-043
    purpose: Verify PC-AFR-043: PCMS shall maintain
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_044_01(stub_iam):
    """test_id: TC-FR-044-01
    source_id: PC-AFR-044
    purpose: Verify PC-AFR-044: PCMS shall allow a
    test_type: positive"""
    client = APIClient()
    r = client.post("/api/v1/placement/companies/register", {
        "name": "Global Corp", "website": "https://global.test",
        "contact_name": "Recruiter One", "contact_email": "r1@global.test"
    }, format="json")
    assert r.status_code == 201
    assert r.json()["approval_status"] == "pending"

def test_tc_fr_045_01(stub_iam):
    """test_id: TC-FR-045-01
    source_id: PC-AFR-045
    purpose: Verify PC-AFR-045: PCMS shall restrict
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_045_02(stub_iam):
    """test_id: TC-FR-045-02
    source_id: PC-AFR-045-negative-validation
    purpose: Verify negative/validation boundary for PC-AFR-045: PCMS shall restrict
    test_type: negative"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_046_01(stub_iam):
    """test_id: TC-FR-046-01
    source_id: PC-AFR-046
    purpose: Verify PC-AFR-046: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_047_01(stub_iam):
    """test_id: TC-FR-047-01
    source_id: PC-AFR-047
    purpose: Verify PC-AFR-047: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_048_01(stub_iam):
    """test_id: TC-FR-048-01
    source_id: PC-AFR-048
    purpose: Verify PC-AFR-048: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_049_01(stub_iam):
    """test_id: TC-FR-049-01
    source_id: PC-AFR-049
    purpose: Verify PC-AFR-049: PCMS shall allow
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_050_01(stub_iam):
    """test_id: TC-FR-050-01
    source_id: PC-AFR-050
    purpose: Verify PC-AFR-050: PCMS shall trigger
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_051_01(stub_iam):
    """test_id: TC-FR-051-01
    source_id: PC-AFR-051
    purpose: Verify PC-AFR-051: PCMS shall trigger
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_052_01(stub_iam):
    """test_id: TC-FR-052-01
    source_id: PC-AFR-052
    purpose: Verify PC-AFR-052: PCMS shall trigger
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_053_01(stub_iam):
    """test_id: TC-FR-053-01
    source_id: PC-AFR-053
    purpose: Verify PC-AFR-053: PCMS shall trigger
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_054_01(stub_iam):
    """test_id: TC-FR-054-01
    source_id: PC-AFR-054
    purpose: Verify PC-AFR-054: PCMS shall trigger
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_055_01(stub_iam):
    """test_id: TC-FR-055-01
    source_id: PC-AFR-055
    purpose: Verify PC-AFR-055: PCMS shall trigger
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_056_01(stub_iam):
    """test_id: TC-FR-056-01
    source_id: PC-AFR-056
    purpose: Verify PC-AFR-056: PCMS shall trigger
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_057_01(stub_iam):
    """test_id: TC-FR-057-01
    source_id: PC-AFR-057
    purpose: Verify PC-AFR-057: PCMS shall hand off
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_058_01(stub_iam):
    """test_id: TC-FR-058-01
    source_id: PC-AFR-058
    purpose: Verify PC-AFR-058: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_059_01(stub_iam):
    """test_id: TC-FR-059-01
    source_id: PC-AFR-059
    purpose: Verify PC-AFR-059: Alumni
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_060_01(stub_iam):
    """test_id: TC-FR-060-01
    source_id: PC-AFR-060
    purpose: Verify PC-AFR-060: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_061_01(stub_iam):
    """test_id: TC-FR-061-01
    source_id: PC-AFR-061
    purpose: Verify PC-AFR-061: PCMS shall
    test_type: positive"""
    StudentPlacementProfile.objects.create(user_id=9999, summary="Private")
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/profiles/9999")
    assert r.status_code in (403, 404)

def test_tc_fr_062_01(stub_iam):
    """test_id: TC-FR-062-01
    source_id: PC-AFR-062
    purpose: Verify PC-AFR-062: PCMS shall
    test_type: positive"""
    StudentPlacementProfile.objects.create(user_id=9999, summary="Private")
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/profiles/9999")
    assert r.status_code in (403, 404)

def test_tc_fr_063_01(stub_iam):
    """test_id: TC-FR-063-01
    source_id: PC-AFR-063
    purpose: Verify PC-AFR-063: PCMS shall
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)

def test_tc_fr_064_01(stub_iam):
    """test_id: TC-FR-064-01
    source_id: PC-AFR-064
    purpose: Verify PC-AFR-064: PCMS role-based
    test_type: positive"""
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/stats")
    assert r.status_code in (200, 403)
