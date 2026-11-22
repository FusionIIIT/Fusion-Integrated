"""BW-CMS-01 (WF-01) – Complaint Intake to Resolution Workflow.

Workflow:
Complainant submits a complaint, handler assigns worker/priority,
updates progress, and resolves it (Page 4 – BW-CMS-01).

Transitions:
- submitted -> in_progress (via assign / progress)
- in_progress -> resolved (via resolve)
- submitted -> resolved (direct resolution supported by STT)
"""

import pytest
from modules.complaints.models import ComplaintCategory, ComplaintTransition

@pytest.mark.django_db
def test_wf_001_e2e_intake_to_resolution_happy_path(api_client, stub_iam, make_session):
    """End-to-End: Submission -> Assignment -> Progress Update -> Resolution."""
    # Setup category
    category, _ = ComplaintCategory.objects.get_or_create(
        name="Electrical",
        defaults={"is_active": True, "default_sla_hours": 48},
    )

    # 1. Complainant submits complaint
    complainant_session = make_session(
        user_id=1001,
        permissions=["complaints.complaint.create", "complaints.complaint.view_self"],
        active_role="complainant",
    )
    stub_iam(session=complainant_session)

    submit_payload = {
        "category_id": category.id,
        "location": "Room 204, Hall 3",
        "description": "Ceiling fan speed regulator burnt out",
        "priority": "medium",
        "verification_required": "user",
    }
    submit_res = api_client.post("/api/v1/complaints/", submit_payload, format="json")
    assert submit_res.status_code == 201
    complaint_data = submit_res.json()
    complaint_pk = complaint_data["id"]
    assert complaint_data["status"] == "submitted"
    assert complaint_data["complaint_id"].startswith("CMP-")

    # 2. Handler assigns worker and adjusts priority
    handler_session = make_session(
        user_id=2001,
        permissions=[
            "complaints.complaint.view",
            "complaints.complaint.assign",
            "complaints.complaint.update",
            "complaints.complaint.resolve",
        ],
        active_role="complaint_handler",
        kind="staff",
    )
    stub_iam(session=handler_session)

    assign_payload = {
        "worker_id": 88,
        "worker_name": "Ramesh Electrician",
        "priority": "high",
        "remarks": "Assigned technician Ramesh",
    }
    assign_res = api_client.post(
        f"/api/v1/complaints/{complaint_pk}/assign/",
        assign_payload,
        format="json",
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["assigned_worker_id"] == 88
    assert assign_res.json()["priority"] == "high"

    # 3. Handler logs operational progress
    progress_payload = {"progress_notes": "Procured replacement regulator switch"}
    progress_res = api_client.post(
        f"/api/v1/complaints/{complaint_pk}/progress/",
        progress_payload,
        format="json",
    )
    assert progress_res.status_code == 200
    assert progress_res.json()["status"] == "in_progress"

    # 4. Handler resolves complaint
    resolve_payload = {"resolution_details": "Replaced regulator switch and verified fan operation"}
    resolve_res = api_client.post(
        f"/api/v1/complaints/{complaint_pk}/resolve/",
        resolve_payload,
        format="json",
    )
    assert resolve_res.status_code == 200
    resolve_data = resolve_res.json()
    assert resolve_data["status"] == "resolved"
    assert resolve_data["resolution_details"] == resolve_payload["resolution_details"]

    # Verify audit trail in DB
    transitions = ComplaintTransition.objects.filter(complaint_id=complaint_pk).order_by("created_at")
    assert transitions.count() >= 3

@pytest.mark.django_db
def test_wf_001_direct_resolve_from_submitted(api_client, stub_iam, make_session, complaint_factory):
    """Direct resolution from submitted status without intermediate progress (per STT)."""
    complaint = complaint_factory(status="submitted", verification_required="user")
    handler_session = make_session(
        user_id=2001,
        permissions=["complaints.complaint.view", "complaints.complaint.resolve"],
        active_role="complaint_handler",
    )
    stub_iam(session=handler_session)

    resolve_payload = {"resolution_details": "Quick fix: flipped main circuit breaker"}
    res = api_client.post(
        f"/api/v1/complaints/{complaint.id}/resolve/",
        resolve_payload,
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["status"] == "resolved"
