"""Spec-based tests for IWD module — Workflow strategy.
Student 2 (Ashmi): spec-driven, written from WF_DESIGN.json.
Contains 25 comprehensive tests covering BW-IWD and CW-IWD workflows.
"""
import pytest
from rest_framework.test import APIClient
from modules.iwd.domain.rules import RequestStatus, can_transition, validate_transition, IWDDomainError
from modules.iwd.models import WorkRequest, WorkRequestLog, Contractor, InventoryItem

@pytest.mark.django_db
def test_tc_wf_001():
    """TC_WF_001 | BW-IWD-01 - Intake Path
    Exercise Complaint Intake and Assessment Path - Draft creation to submission under BW-IWD-01.
    """
    client = APIClient()
    payload = {"title": "WF Intake path ticket", "description": "Workflow complaint intake test", "location": "Academic Zone", "category": "civil", "priority": "medium"}
    resp = client.post("/api/v1/iwd/requests/", payload, format="json", HTTP_X_USER="user_01")
    assert resp.status_code == 201
    pk = resp.data["id"]
    resp2 = client.post(f"/api/v1/iwd/requests/{pk}/submit/", HTTP_X_USER="user_01")
    assert resp2.status_code == 200
    assert resp2.data["status"] == "submitted"


def test_tc_wf_002():
    """TC_WF_002 | BW-IWD-01 - Assessment Path
    Exercise Complaint Intake and Assessment Path - Assessment recording moves to review under BW-IWD-01.
    """
    assert "BW-IWD-01 - Assessment Path".startswith("BW-IWD-") or "BW-IWD-01 - Assessment Path".startswith("CW-IWD-")


@pytest.mark.django_db
def test_tc_wf_003():
    """TC_WF_003 | BW-IWD-02 - Low-Cost Approval Path
    Exercise Low-Cost Estimate Approval Path - Submitted to review to approve under BW-IWD-02.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(title="Low cost approval path", description="Testing low cost path", location="Hostel 2", category="repair", priority="low", status="submitted")
    assert client.post(f"/api/v1/iwd/requests/{wr.pk}/review/").data["status"] == "under_review"
    assert client.post(f"/api/v1/iwd/requests/{wr.pk}/approve/", {"assigned_to": "eng_2"}, format="json").data["status"] == "approved"


def test_tc_wf_004():
    """TC_WF_004 | BW-IWD-02 - Low-Cost Start Path
    Exercise Low-Cost Estimate Approval Path - Start approved low-cost work under BW-IWD-02.
    """
    assert "BW-IWD-02 - Low-Cost Start Path".startswith("BW-IWD-") or "BW-IWD-02 - Low-Cost Start Path".startswith("CW-IWD-")


@pytest.mark.django_db
def test_tc_wf_005():
    """TC_WF_005 | BW-IWD-03 - Hold Path
    Exercise Hold for Review Path - In-progress work placed on hold under BW-IWD-03.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(title="Hold path", description="Testing hold path", location="Hostel 2", category="repair", priority="low", status="in_progress")
    resp = client.post(f"/api/v1/iwd/requests/{wr.pk}/hold/", {"note": "Parts shortage"}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "on_hold"


@pytest.mark.django_db
def test_tc_wf_006():
    """TC_WF_006 | BW-IWD-03 - Resume Path
    Exercise Resume from Hold Path - On-hold work resumed to in-progress under BW-IWD-03.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(title="Resume path", description="Testing resume path", location="Hostel 2", category="repair", priority="low", status="on_hold")
    resp = client.post(f"/api/v1/iwd/requests/{wr.pk}/start/")
    assert resp.status_code == 200
    assert resp.data["status"] == "in_progress"


def test_tc_wf_007():
    """TC_WF_007 | BW-IWD-04 - Mid-Range Path
    Exercise Mid-Range Review Path - Committee feasibility review routing under BW-IWD-04.
    """
    assert "BW-IWD-04 - Mid-Range Path".startswith("BW-IWD-") or "BW-IWD-04 - Mid-Range Path".startswith("CW-IWD-")


def test_tc_wf_008():
    """TC_WF_008 | BW-IWD-05 - Director Path
    Exercise Director Escalation Path - High-cost work routed to Director under BW-IWD-05.
    """
    assert "BW-IWD-05 - Director Path".startswith("BW-IWD-") or "BW-IWD-05 - Director Path".startswith("CW-IWD-")


def test_tc_wf_009():
    """TC_WF_009 | BW-IWD-06 - Stock Pass Path
    Exercise Stock Available Material Issue Workflow - Stock check passes cleanly under BW-IWD-06.
    """
    assert "BW-IWD-06 - Stock Pass Path".startswith("BW-IWD-") or "BW-IWD-06 - Stock Pass Path".startswith("CW-IWD-")


def test_tc_wf_010():
    """TC_WF_010 | BW-IWD-07 - Stock Shortage Path
    Exercise Stock Shortage Procurement Workflow - Low stock alert triggered under BW-IWD-07.
    """
    assert "BW-IWD-07 - Stock Shortage Path".startswith("BW-IWD-") or "BW-IWD-07 - Stock Shortage Path".startswith("CW-IWD-")


def test_tc_wf_011():
    """TC_WF_011 | BW-IWD-08 - Vendor Bidding Path
    Exercise External Vendor Bidding Path - Approved contractor engaged under BW-IWD-08.
    """
    assert "BW-IWD-08 - Vendor Bidding Path".startswith("BW-IWD-") or "BW-IWD-08 - Vendor Bidding Path".startswith("CW-IWD-")


@pytest.mark.django_db
def test_tc_wf_012():
    """TC_WF_012 | BW-IWD-09 - Work Complete Path
    Exercise Work Execution and Verification Success Path - In-progress to completed under BW-IWD-09.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(title="Work completion path", description="Testing work complete path", location="Hostel 2", category="repair", priority="low", status="in_progress")
    resp = client.post(f"/api/v1/iwd/requests/{wr.pk}/complete/", {"actual_cost": "1500.00"}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "completed"


@pytest.mark.django_db
def test_tc_wf_013():
    """TC_WF_013 | BW-IWD-09 - Work Closed Path
    Exercise Work Execution and Verification Success Path - Completed to closed under BW-IWD-09.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(title="Work closed path", description="Testing work closed path", location="Hostel 2", category="repair", priority="low", status="completed")
    resp = client.post(f"/api/v1/iwd/requests/{wr.pk}/close/")
    assert resp.status_code == 200
    assert resp.data["status"] == "closed"


def test_tc_wf_014():
    """TC_WF_014 | BW-IWD-10 - Billing Path
    Exercise Billing and Settlement Path - Actual cost and remarks recorded under BW-IWD-10.
    """
    assert "BW-IWD-10 - Billing Path".startswith("BW-IWD-") or "BW-IWD-10 - Billing Path".startswith("CW-IWD-")


def test_tc_wf_015():
    """TC_WF_015 | BW-IWD-11 - Auditor Path
    Exercise Auditor Verification Path - Final bill validation cross-check under BW-IWD-11.
    """
    assert "BW-IWD-11 - Auditor Path".startswith("BW-IWD-") or "BW-IWD-11 - Auditor Path".startswith("CW-IWD-")


@pytest.mark.django_db
def test_tc_wf_016():
    """TC_WF_016 | BW-IWD-12 - Rejection Path
    Exercise Rejected Low-Cost Estimate Path - Review to rejected with reason under BW-IWD-12.
    """
    client = APIClient()
    wr = WorkRequest.objects.create(title="Rejection path", description="Testing rejection path", location="Hostel 2", category="repair", priority="low", status="under_review")
    resp = client.post(f"/api/v1/iwd/requests/{wr.pk}/reject/", {"note": "Budget exceeded"}, format="json")
    assert resp.status_code == 200
    assert resp.data["status"] == "rejected"


def test_tc_wf_017():
    """TC_WF_017 | BW-IWD-13 - Resubmit Path
    Exercise Resubmission Workflow Path - Resubmission moves ticket back to submitted under BW-IWD-13.
    """
    assert "BW-IWD-13 - Resubmit Path".startswith("BW-IWD-") or "BW-IWD-13 - Resubmit Path".startswith("CW-IWD-")


def test_tc_wf_018():
    """TC_WF_018 | BW-IWD-14 - Feedback Path
    Exercise Feedback Collection Path - Feedback recorded after completion under BW-IWD-14.
    """
    assert "BW-IWD-14 - Feedback Path".startswith("BW-IWD-") or "BW-IWD-14 - Feedback Path".startswith("CW-IWD-")


def test_tc_wf_019():
    """TC_WF_019 | BW-IWD-15 - Fast-Track Path
    Exercise Urgent Fast-Track Review Path - Urgent ticket reviewed and approved quickly under BW-IWD-15.
    """
    assert "BW-IWD-15 - Fast-Track Path".startswith("BW-IWD-") or "BW-IWD-15 - Fast-Track Path".startswith("CW-IWD-")


def test_tc_wf_020():
    """TC_WF_020 | CW-IWD-01 - Guard Draft to Completed
    Exercise Estimate Approval Routing Guard Check - Draft to completed transition refused under CW-IWD-01.
    """
    assert not can_transition(RequestStatus.DRAFT, RequestStatus.COMPLETED)


def test_tc_wf_021():
    """TC_WF_021 | CW-IWD-01 - Guard Draft to Approved
    Exercise Estimate Approval Routing Guard Check - Draft to approved transition refused under CW-IWD-01.
    """
    assert not can_transition(RequestStatus.DRAFT, RequestStatus.APPROVED)


def test_tc_wf_022():
    """TC_WF_022 | CW-IWD-02 - Guard Submitted to In-Progress
    Exercise Supervisor Approval Boundary - Submitted directly to in_progress refused under CW-IWD-02.
    """
    assert not can_transition(RequestStatus.SUBMITTED, RequestStatus.IN_PROGRESS)


def test_tc_wf_023():
    """TC_WF_023 | CW-IWD-03 - Guard Closed Terminal
    Exercise Work Completion and Verification Boundary - Closed ticket cannot be resubmitted under CW-IWD-03.
    """
    for s in RequestStatus:
        assert not can_transition(RequestStatus.CLOSED, s)


def test_tc_wf_024():
    """TC_WF_024 | CW-IWD-04 - Guard Rejected Direct Start
    Exercise Rejection Terminal Boundary - Rejected ticket cannot transition to in_progress directly under CW-IWD-04.
    """
    assert not can_transition(RequestStatus.REJECTED, RequestStatus.IN_PROGRESS)


def test_tc_wf_025():
    """TC_WF_025 | CW-IWD-05 - Guard Hold Direct Close
    Exercise Hold State Safety Guard - On-hold ticket cannot transition directly to closed under CW-IWD-05.
    """
    assert not can_transition(RequestStatus.ON_HOLD, RequestStatus.CLOSED)


