# Plain ordinary user tests: faculty/staff with no extra roles or optional fields (Step 5.2).
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.psm import registry
from modules.psm.services.policy import seed_default_policy

pytestmark = pytest.mark.django_db


def _plain_employee(stub_iam, uid=2001, kind="faculty"):
    stub_iam(
        make_session(
            user_id=uid,
            kind=kind,
            active_role=kind,
            roles=(kind,),
            modules=("psm",),
            permissions=tuple(registry.ROLE_GRANTS[kind]),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token plain")
    return c


def test_plain_faculty_submits_tracks_modifies_repeats_and_withdraws(stub_iam):
    # CFR-PSM-001, CFR-PSM-002, PSM-UC-001, PSM-UC-003, PSM-UC-005, PSM-UC-023, PSM-UC-024
    seed_default_policy()
    client = _plain_employee(stub_iam, uid=2001, kind="faculty")
    r_create = client.post(
        "/api/v1/psm/indents",
        {
            "department": "CSE",
            "item_description": "Whiteboard Markers",
            "quantity": 10,
            "estimated_cost": "1200.00",
            "justification": "Classroom teaching supplies",
        },
        format="json",
    )
    assert r_create.status_code == 201
    indent_id = r_create.data["id"]
    assert r_create.data["status"] == "submitted"
    assert r_create.data["indent_number"].startswith("IND-")
    assert r_create.data["version"] == 1

    r_detail = client.get(f"/api/v1/psm/indents/{indent_id}")
    assert r_detail.status_code == 200
    assert len(r_detail.data["versions"]) == 1
    assert len(r_detail.data["transitions"]) == 1

    r_mod = client.patch(f"/api/v1/psm/indents/{indent_id}", {"quantity": 12}, format="json")
    assert r_mod.status_code == 200
    assert r_mod.data["version"] == 2
    assert r_mod.data["quantity"] == 12

    r_rep = client.post(f"/api/v1/psm/indents/{indent_id}/repeat", {}, format="json")
    assert r_rep.status_code == 201
    assert r_rep.data["status"] == "draft"
    assert r_rep.data["id"] != indent_id

    draft_id = r_rep.data["id"]
    r_draft_mod = client.patch(f"/api/v1/psm/indents/{draft_id}", {"quantity": 15}, format="json")
    assert r_draft_mod.status_code == 200
    assert r_draft_mod.data["status"] == "draft"
    assert r_draft_mod.data["indent_number"] is None
    assert r_draft_mod.data["submitted_at"] is None
    assert r_draft_mod.data["quantity"] == 15

    r_draft_sub = client.post(f"/api/v1/psm/indents/{draft_id}/submit", {}, format="json")
    assert r_draft_sub.status_code == 200
    assert r_draft_sub.data["status"] == "submitted"
    assert r_draft_sub.data["indent_number"].startswith("IND-")
    assert r_draft_sub.data["submitted_at"] is not None

    r_wd = client.post(
        f"/api/v1/psm/indents/{indent_id}/withdraw", {"reason": "No longer needed"}, format="json"
    )
    assert r_wd.status_code == 200
    assert r_wd.data["status"] == "withdrawn"


def test_plain_staff_reaches_dashboard_and_notifications(stub_iam):
    # PSM-UC-030, BR-PSM-006
    seed_default_policy()
    client = _plain_employee(stub_iam, uid=2002, kind="staff")
    assert client.get("/api/v1/psm/dashboard").status_code == 200
    assert client.get("/api/v1/psm/notifications").status_code == 200
