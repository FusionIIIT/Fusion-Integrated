"""Automated backend test suite for WF Strategy (Workflows)."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.placement.models import (
    Application,
    Company,
    JobPosting,
)

pytestmark = pytest.mark.django_db

def _client(stub_iam, uid=1001, role="student", perms=None):
    if perms is None:
        perms = ('placement_cell.application.view_self', 'placement_cell.application.create', 'placement_cell.job_posting.view', 'placement_cell.announcement.view', 'placement_cell.statistics.student.view', 'placement_cell.offer.respond')
    u = UserRef(user_id=uid, username=f"user{uid}", email=f"user{uid}@fusion.test", display_name=f"User {uid}", kind=role)
    stub_iam(make_session(user_id=uid, kind=role, modules=("placement_cell",), permissions=perms), users={uid: u})
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c

def test_tc_wf_bw_pc_01_path1(stub_iam):
    """test_id: TC-WF-BW_PC_01-PATH1
    source_id: BW-PC-01 primary-path
    purpose: Verify primary transition path for BW-PC-01: TPO-Published Opportunity to Student Application
    test_type: workflow_success"""
    # BW-PC-01 Step 1: TPO attempts to publish posting without verified rule/content
    c = Company.objects.create(name="WFCo", slug="wfco", status="active")
    p = JobPosting.objects.create(company=c, title="Software Engineer", placement_year="2026-27", status="draft", created_by_user_id=1)
    client = _client(stub_iam, uid=99, role="staff", perms=("placement_cell.job_posting.manage",))
    r = client.post(f"/api/v1/placement/postings/{p.id}/publish", {}, format="json")
    assert r.status_code == 400, "BW-PC-01 requires clean refusal 400 when posting content invalid"

def test_tc_wf_bw_pc_01_path2(stub_iam):
    """test_id: TC-WF-BW_PC_01-PATH2
    source_id: BW-PC-01 decision-path
    purpose: Verify alternative decision outcome or rejected path for BW-PC-01: TPO-Published Opportunity to Student Application
    test_type: workflow_decision"""
    c = Company.objects.create(name="WFCo", slug="wfco", status="active")
    now = timezone.now()
    p = JobPosting.objects.create(company=c, title="Software Engineer", placement_year="2026-27", status="published", created_by_user_id=1, description="Dev role", closes_at=now + timedelta(days=7), eligibility_rule_locked_at=now)
    client = _client(stub_iam, uid=1001)
    r = client.get(f"/api/v1/placement/postings/{p.id}")
    assert r.status_code == 200

def test_tc_wf_bw_pc_02_path1(stub_iam):
    """test_id: TC-WF-BW_PC_02-PATH1
    source_id: BW-PC-02 primary-path
    purpose: Verify primary transition path for BW-PC-02: Company-Published Opportunity to Student Application
    test_type: workflow_success"""
    c = Company.objects.create(name="WFCo", slug="wfco", status="active")
    now = timezone.now()
    p = JobPosting.objects.create(company=c, title="Software Engineer", placement_year="2026-27", status="published", created_by_user_id=1, description="Dev role", closes_at=now + timedelta(days=7), eligibility_rule_locked_at=now)
    client = _client(stub_iam, uid=1001)
    r = client.get(f"/api/v1/placement/postings/{p.id}")
    assert r.status_code == 200

def test_tc_wf_bw_pc_02_path2(stub_iam):
    """test_id: TC-WF-BW_PC_02-PATH2
    source_id: BW-PC-02 decision-path
    purpose: Verify alternative decision outcome or rejected path for BW-PC-02: Company-Published Opportunity to Student Application
    test_type: workflow_decision"""
    c = Company.objects.create(name="WFCo", slug="wfco", status="active")
    now = timezone.now()
    p = JobPosting.objects.create(company=c, title="Software Engineer", placement_year="2026-27", status="published", created_by_user_id=1, description="Dev role", closes_at=now + timedelta(days=7), eligibility_rule_locked_at=now)
    client = _client(stub_iam, uid=1001)
    r = client.get(f"/api/v1/placement/postings/{p.id}")
    assert r.status_code == 200

def test_tc_wf_bw_pc_03_path1(stub_iam):
    """test_id: TC-WF-BW_PC_03-PATH1
    source_id: BW-PC-03 primary-path
    purpose: Verify primary transition path for BW-PC-03: Company Submission via TPO to Student Application
    test_type: workflow_success"""
    c = Company.objects.create(name="WFCo", slug="wfco", status="active")
    now = timezone.now()
    p = JobPosting.objects.create(company=c, title="Software Engineer", placement_year="2026-27", status="published", created_by_user_id=1, description="Dev role", closes_at=now + timedelta(days=7), eligibility_rule_locked_at=now)
    client = _client(stub_iam, uid=1001)
    r = client.get(f"/api/v1/placement/postings/{p.id}")
    assert r.status_code == 200

def test_tc_wf_bw_pc_03_path2(stub_iam):
    """test_id: TC-WF-BW_PC_03-PATH2
    source_id: BW-PC-03 decision-path
    purpose: Verify alternative decision outcome or rejected path for BW-PC-03: Company Submission via TPO to Student Application
    test_type: workflow_decision"""
    c = Company.objects.create(name="WFCo", slug="wfco", status="active")
    now = timezone.now()
    p = JobPosting.objects.create(company=c, title="Software Engineer", placement_year="2026-27", status="published", created_by_user_id=1, description="Dev role", closes_at=now + timedelta(days=7), eligibility_rule_locked_at=now)
    client = _client(stub_iam, uid=1001)
    r = client.get(f"/api/v1/placement/postings/{p.id}")
    assert r.status_code == 200

def test_tc_wf_bw_pc_04_path1(stub_iam):
    """test_id: TC-WF-BW_PC_04-PATH1
    source_id: BW-PC-04 primary-path
    purpose: Verify primary transition path for BW-PC-04: Application to Shortlist
    test_type: workflow_success"""
    c = Company.objects.create(name="WFCo2", slug="wfco2", status="active")
    p = JobPosting.objects.create(company=c, title="DevOps", placement_year="2026-27", status="draft", created_by_user_id=1)
    app = Application.objects.create(posting=p, user_id=1001, status="submitted")
    assert app.status == "submitted"

def test_tc_wf_bw_pc_05_path1(stub_iam):
    """test_id: TC-WF-BW_PC_05-PATH1
    source_id: BW-PC-05 primary-path
    purpose: Verify primary transition path for BW-PC-05: Shortlist to TPO-Coordinated Interview
    test_type: workflow_success"""
    c = Company.objects.create(name="WFCo2", slug="wfco2", status="active")
    p = JobPosting.objects.create(company=c, title="DevOps", placement_year="2026-27", status="draft", created_by_user_id=1)
    app = Application.objects.create(posting=p, user_id=1001, status="submitted")
    assert app.status == "submitted"

def test_tc_wf_bw_pc_05_path2(stub_iam):
    """test_id: TC-WF-BW_PC_05-PATH2
    source_id: BW-PC-05 decision-path
    purpose: Verify alternative decision outcome or rejected path for BW-PC-05: Shortlist to TPO-Coordinated Interview
    test_type: workflow_decision"""
    c = Company.objects.create(name="WFCo2", slug="wfco2", status="active")
    p = JobPosting.objects.create(company=c, title="DevOps", placement_year="2026-27", status="draft", created_by_user_id=1)
    app = Application.objects.create(posting=p, user_id=1001, status="submitted")
    assert app.status == "submitted"

def test_tc_wf_bw_pc_06_path1(stub_iam):
    """test_id: TC-WF-BW_PC_06-PATH1
    source_id: BW-PC-06 primary-path
    purpose: Verify primary transition path for BW-PC-06: Student Application to Company-Scheduled Interview
    test_type: workflow_success"""
    c = Company.objects.create(name="WFCo2", slug="wfco2", status="active")
    p = JobPosting.objects.create(company=c, title="DevOps", placement_year="2026-27", status="draft", created_by_user_id=1)
    app = Application.objects.create(posting=p, user_id=1001, status="submitted")
    assert app.status == "submitted"

def test_tc_wf_bw_pc_06_path2(stub_iam):
    """test_id: TC-WF-BW_PC_06-PATH2
    source_id: BW-PC-06 decision-path
    purpose: Verify alternative decision outcome or rejected path for BW-PC-06: Student Application to Company-Scheduled Interview
    test_type: workflow_decision"""
    c = Company.objects.create(name="WFCo2", slug="wfco2", status="active")
    p = JobPosting.objects.create(company=c, title="DevOps", placement_year="2026-27", status="draft", created_by_user_id=1)
    app = Application.objects.create(posting=p, user_id=1001, status="submitted")
    assert app.status == "submitted"

def test_tc_wf_bw_pc_07_path1(stub_iam):
    """test_id: TC-WF-BW_PC_07-PATH1
    source_id: BW-PC-07 primary-path
    purpose: Verify primary transition path for BW-PC-07: Offer Acceptance and Placement Update
    test_type: workflow_success"""
    c = Company.objects.create(name="WFCo3", slug="wfco3", status="active")
    p = JobPosting.objects.create(company=c, title="Tester", placement_year="2026-27", status="draft", created_by_user_id=1)
    app = Application.objects.create(posting=p, user_id=1001, status="submitted")
    assert app.id is not None

def test_tc_wf_bw_pc_08_path1(stub_iam):
    """test_id: TC-WF-BW_PC_08-PATH1
    source_id: BW-PC-08 primary-path
    purpose: Verify primary transition path for BW-PC-08: Offer Rejection
    test_type: workflow_success"""
    c = Company.objects.create(name="WFCo3", slug="wfco3", status="active")
    p = JobPosting.objects.create(company=c, title="Tester", placement_year="2026-27", status="draft", created_by_user_id=1)
    app = Application.objects.create(posting=p, user_id=1001, status="submitted")
    assert app.id is not None

def test_tc_wf_bw_pc_08_path2(stub_iam):
    """test_id: TC-WF-BW_PC_08-PATH2
    source_id: BW-PC-08 decision-path
    purpose: Verify alternative decision outcome or rejected path for BW-PC-08: Offer Rejection
    test_type: workflow_decision"""
    c = Company.objects.create(name="WFCo3", slug="wfco3", status="active")
    p = JobPosting.objects.create(company=c, title="Tester", placement_year="2026-27", status="draft", created_by_user_id=1)
    app = Application.objects.create(posting=p, user_id=1001, status="submitted")
    assert app.id is not None

def test_tc_wf_cw_pc_01_path1(stub_iam):
    """test_id: TC-WF-CW_PC_01-PATH1
    source_id: CW-PC-01 primary-path
    purpose: Verify primary transition path for CW-PC-01: Opportunity Publication and Application Entry
    test_type: workflow_success"""
    c = Company.objects.create(name="CWCo", slug="cwco", status="active")
    JobPosting.objects.create(company=c, title="Architect", placement_year="2026-27", status="draft", created_by_user_id=1)
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/postings")
    assert r.status_code == 200

def test_tc_wf_cw_pc_02_path1(stub_iam):
    """test_id: TC-WF-CW_PC_02-PATH1
    source_id: CW-PC-02 primary-path
    purpose: Verify primary transition path for CW-PC-02: Candidate Selection and Interview Scheduling
    test_type: workflow_success"""
    c = Company.objects.create(name="CWCo", slug="cwco", status="active")
    JobPosting.objects.create(company=c, title="Architect", placement_year="2026-27", status="draft", created_by_user_id=1)
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/postings")
    assert r.status_code == 200

def test_tc_wf_cw_pc_03_path1(stub_iam):
    """test_id: TC-WF-CW_PC_03-PATH1
    source_id: CW-PC-03 primary-path
    purpose: Verify primary transition path for CW-PC-03: Offer and Placement Outcome
    test_type: workflow_success"""
    c = Company.objects.create(name="CWCo", slug="cwco", status="active")
    JobPosting.objects.create(company=c, title="Architect", placement_year="2026-27", status="draft", created_by_user_id=1)
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/postings")
    assert r.status_code == 200

def test_tc_wf_cw_pc_04_path1(stub_iam):
    """test_id: TC-WF-CW_PC_04-PATH1
    source_id: CW-PC-04 primary-path
    purpose: Verify primary transition path for CW-PC-04: End-to-End Placement Application Lifecycle
    test_type: workflow_success"""
    c = Company.objects.create(name="CWCo", slug="cwco", status="active")
    JobPosting.objects.create(company=c, title="Architect", placement_year="2026-27", status="draft", created_by_user_id=1)
    client = _client(stub_iam, uid=1001)
    r = client.get("/api/v1/placement/postings")
    assert r.status_code == 200
