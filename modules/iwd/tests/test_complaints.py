"""Tests for IWD complaint models, services, selectors, API, and contracts (Increment 3).

Verifies:
- Complaint and Engineer models, constraints, and audit transition logging
- Concurrency-safe automatic assignment based on trade expertise and workload
- Tie-breaking using lowest user_id
- Approach B: graceful no-match handling (persisting in SUBMITTED with assigned_engineer_id=None)
- Selector scoping: complainants see own, engineers see assigned, admins see all
- API endpoints: POST /api/v1/iwd/complaints/, GET /api/v1/iwd/complaints/, GET /api/v1/iwd/complaints/<pk>/
- Strict 404 behavior on out-of-scope detail requests
- Contracts batched retrieval
"""
from __future__ import annotations

import pytest
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from core.api.exceptions import BadRequestError
from modules.iwd.contracts import get_complaints
from modules.iwd.domain.state_machine import IWDState
from modules.iwd.models import Complaint, ComplaintTransition, Engineer
from modules.iwd.selectors.complaints import (
    get_active_workload,
    get_complaint_for_user,
    get_unassigned_complaints,
    visible_complaints,
)
from modules.iwd.services.complaints import submit_complaint

pytestmark = pytest.mark.django_db


# -- Helpers -------------------------------------------------------------------

def make_client_for_session(stub_iam, session):
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-valid-token")
    return client


# -- 1. Models & Invariants ----------------------------------------------------

class TestComplaintModels:
    def test_engineer_creation_and_str(self):
        eng = Engineer.objects.create(user_id=201, specialization="civil", is_active=True)
        assert str(eng) == "Engineer u201 (civil)"
        assert eng.is_active is True

    def test_engineer_user_id_unique(self):
        Engineer.objects.create(user_id=202, specialization="electrical")
        with pytest.raises(IntegrityError):
            Engineer.objects.create(user_id=202, specialization="civil")

    def test_complaint_creation_and_str(self):
        c = Complaint.objects.create(
            user_id=101,
            category="civil",
            location="Core Lab 101",
            urgency="high",
            remarks="Ceiling leakage",
        )
        assert str(c) == f"Complaint #{c.pk} u101 [Submitted]"
        assert c.status == IWDState.SUBMITTED.value
        assert c.assigned_engineer_id is None

    def test_complaint_transition_str(self):
        c = Complaint.objects.create(
            user_id=101,
            category="electrical",
            location="Library 2F",
        )
        t = ComplaintTransition.objects.create(
            complaint=c,
            from_status="None",
            to_status=IWDState.SUBMITTED.value,
            actor_user_id=101,
            actor_label="Institute Employee",
            reason="Created",
        )
        assert str(t) == f"Complaint #{c.pk} None->Submitted"


# -- 2. Services & Auto-Assignment Logic ---------------------------------------

class TestComplaintServices:
    def test_submit_complaint_success_with_auto_assignment(self):
        eng = Engineer.objects.create(user_id=301, specialization="civil", is_active=True)
        c = submit_complaint(
            complainant_id=101,
            category="civil",
            location="Room 204",
            urgency="medium",
            remarks="Window latch broken",
        )
        assert c.status == IWDState.ASSIGNED.value
        assert c.assigned_engineer_id == eng.user_id
        assert c.assigned_at is not None

        # Verify audit transitions
        transitions = list(c.transitions.order_by("created_at", "id"))
        assert len(transitions) == 2
        assert transitions[0].from_status == "None"
        assert transitions[0].to_status == IWDState.SUBMITTED.value
        assert transitions[0].actor_user_id == 101

        assert transitions[1].from_status == IWDState.SUBMITTED.value
        assert transitions[1].to_status == IWDState.ASSIGNED.value
        assert transitions[1].actor_user_id is None
        assert transitions[1].actor_label == "System"

    def test_auto_assignment_matches_trade_specialization(self):
        Engineer.objects.create(user_id=301, specialization="civil", is_active=True)
        elec_eng = Engineer.objects.create(user_id=302, specialization="electrical", is_active=True)

        c = submit_complaint(
            complainant_id=102,
            category="electrical",
            location="Lab 3",
            urgency="high",
        )
        assert c.status == IWDState.ASSIGNED.value
        assert c.assigned_engineer_id == elec_eng.user_id

    def test_auto_assignment_selects_lowest_workload(self):
        eng1 = Engineer.objects.create(user_id=301, specialization="civil", is_active=True)
        eng2 = Engineer.objects.create(user_id=302, specialization="civil", is_active=True)

        # Give eng1 an active assigned complaint
        Complaint.objects.create(
            user_id=100,
            category="civil",
            location="Hall 1",
            status=IWDState.ASSIGNED.value,
            assigned_engineer_id=eng1.user_id,
        )
        assert get_active_workload(eng1.user_id) == 1
        assert get_active_workload(eng2.user_id) == 0

        # Next civil complaint should be assigned to eng2
        c2 = submit_complaint(
            complainant_id=103,
            category="civil",
            location="Hall 2",
        )
        assert c2.assigned_engineer_id == eng2.user_id

    def test_auto_assignment_tie_break_lowest_user_id(self):
        # Both have 0 workload
        Engineer.objects.create(user_id=405, specialization="civil", is_active=True)
        Engineer.objects.create(user_id=402, specialization="civil", is_active=True)

        c = submit_complaint(
            complainant_id=104,
            category="civil",
            location="Admin Block",
        )
        assert c.assigned_engineer_id == 402

    def test_no_eligible_engineer_approach_b(self):
        # No engineers exist for electrical
        c = submit_complaint(
            complainant_id=105,
            category="electrical",
            location="Power House",
            urgency="emergency",
        )
        # Approach B: Persisted in SUBMITTED, assigned_engineer_id is None, no rollback
        assert c.status == IWDState.SUBMITTED.value
        assert c.assigned_engineer_id is None
        assert c.assigned_at is None

        # Exactly 1 transition recorded
        transitions = list(c.transitions.all())
        assert len(transitions) == 1
        assert transitions[0].to_status == IWDState.SUBMITTED.value

    def test_validation_errors(self):
        with pytest.raises(BadRequestError) as exc_info:
            submit_complaint(complainant_id=101, category="plumbing", location="Bath")
        assert exc_info.value.code == "invalid_category"

        with pytest.raises(BadRequestError) as exc_info:
            submit_complaint(complainant_id=101, category="civil", location="Bath", urgency="critical")
        assert exc_info.value.code == "invalid_urgency"

        with pytest.raises(BadRequestError) as exc_info:
            submit_complaint(complainant_id=101, category="civil", location="   ")
        assert exc_info.value.code == "missing_location"


# -- 3. Selectors & Scoping ----------------------------------------------------

class TestComplaintSelectors:
    def test_scoping_isolation(self):
        c1 = Complaint.objects.create(user_id=101, category="civil", location="A", assigned_engineer_id=201)
        c2 = Complaint.objects.create(user_id=102, category="electrical", location="B", assigned_engineer_id=202)
        c3 = Complaint.objects.create(user_id=103, category="civil", location="C", assigned_engineer_id=None, status=IWDState.SUBMITTED.value)

        # Complainant 101
        p_emp = make_session(user_id=101, permissions=("iwd.complaint.view_self",), modules=("iwd",))
        assert list(visible_complaints(p_emp)) == [c1]

        # Engineer 202
        p_eng = make_session(user_id=202, permissions=("iwd.complaint.view", "iwd.complaint.assess"), modules=("iwd",), active_role="iwd_engineer")
        assert list(visible_complaints(p_eng)) == [c2]

        # Admin
        p_admin = make_session(user_id=901, permissions=("iwd.complaint.view", "iwd.inventory.manage"), modules=("iwd",), active_role="iwd_admin")
        assert set(visible_complaints(p_admin)) == {c1, c2, c3}

        # Unassigned queue for admin
        assert list(get_unassigned_complaints(p_admin)) == [c3]

    def test_get_complaint_for_user_respects_scoping(self):
        c1 = Complaint.objects.create(user_id=101, category="civil", location="A")
        p_other = make_session(user_id=102, permissions=("iwd.complaint.view_self",), modules=("iwd",))
        assert get_complaint_for_user(c1.pk, p_other) is None

    def test_active_role_admin_dormant_role_denied_institute_visibility(self):
        """BR-IWD-001: A user with dormant iwd_admin in roles but active_role='faculty' sees only own complaints."""
        c_own = Complaint.objects.create(user_id=101, category="civil", location="My Office")
        c_other = Complaint.objects.create(user_id=102, category="civil", location="Other Office")

        # active_role is faculty, dormant iwd_admin in roles; permissions derived from active role only
        p = make_session(
            user_id=101,
            permissions=("iwd.complaint.view_self", "iwd.complaint.create"),
            modules=("iwd",),
            active_role="faculty",
            roles=("faculty", "iwd_admin"),
        )
        visible = list(visible_complaints(p))
        assert c_own in visible
        assert c_other not in visible
        assert len(visible) == 1

    def test_active_role_admin_retains_administrative_visibility(self):
        """A user with active_role='iwd_admin' retains full administrative visibility."""
        c1 = Complaint.objects.create(user_id=101, category="civil", location="Office 1")
        c2 = Complaint.objects.create(user_id=102, category="electrical", location="Office 2")

        p = make_session(
            user_id=901,
            permissions=("iwd.complaint.view", "iwd.inventory.manage"),
            modules=("iwd",),
            active_role="iwd_admin",
            roles=("faculty", "iwd_admin"),
        )
        assert set(visible_complaints(p)) == {c1, c2}

    def test_auditor_active_role_denied_general_complaint_queue(self):
        """Auditor with iwd.bill.audit and iwd.complaint.view has no general complaint row visibility in Inc 3."""
        Complaint.objects.create(user_id=101, category="civil", location="Office 1")
        Complaint.objects.create(user_id=102, category="electrical", location="Office 2")

        p = make_session(
            user_id=801,
            permissions=("iwd.complaint.view", "iwd.bill.audit"),
            modules=("iwd",),
            active_role="auditor",
            roles=("auditor",),
        )
        assert list(visible_complaints(p)) == []

    def test_accounts_officer_active_role_denied_general_complaint_queue(self):
        """Accounts Officer with iwd.payment.settle and iwd.complaint.view has no general complaint visibility."""
        Complaint.objects.create(user_id=101, category="civil", location="Office 1")
        Complaint.objects.create(user_id=102, category="electrical", location="Office 2")

        p = make_session(
            user_id=802,
            permissions=("iwd.complaint.view", "iwd.payment.settle"),
            modules=("iwd",),
            active_role="accounts_officer",
            roles=("accounts_officer",),
        )
        assert list(visible_complaints(p)) == []

    def test_operational_permission_does_not_grant_global_visibility(self):
        """An operational permission like iwd.inventory.manage cannot grant global complaint visibility."""
        c_own = Complaint.objects.create(user_id=101, category="civil", location="My Lab")
        Complaint.objects.create(user_id=102, category="civil", location="Other Lab")

        p = make_session(
            user_id=101,
            permissions=("iwd.complaint.view_self", "iwd.inventory.manage"),
            modules=("iwd",),
            active_role="faculty",
            roles=("faculty",),
        )
        visible = list(visible_complaints(p))
        assert visible == [c_own]

    def test_engineer_with_operational_permission_retains_assigned_only_scoping(self):
        """Engineer with an extra operational permission still sees only assigned complaints."""
        c_assigned = Complaint.objects.create(user_id=102, category="civil", location="Lab A", assigned_engineer_id=201)
        Complaint.objects.create(user_id=103, category="civil", location="Lab B", assigned_engineer_id=202)

        p = make_session(
            user_id=201,
            permissions=("iwd.complaint.view", "iwd.complaint.assess", "iwd.inventory.manage"),
            modules=("iwd",),
            active_role="iwd_engineer",
            roles=("iwd_engineer",),
        )
        assert list(visible_complaints(p)) == [c_assigned]

    def test_oversight_roles_retain_institute_wide_visibility(self):
        """iwd_admin, Department Head, and Director all retain full institute-wide visibility."""
        c1 = Complaint.objects.create(user_id=101, category="civil", location="Office 1")
        c2 = Complaint.objects.create(user_id=102, category="electrical", location="Office 2")

        for role in ("iwd_admin", "Department Head", "Director"):
            p = make_session(
                user_id=900,
                permissions=("iwd.complaint.view",),
                modules=("iwd",),
                active_role=role,
                roles=(role,),
            )
            assert set(visible_complaints(p)) == {c1, c2}, f"Role {role} failed to see all complaints"

    def test_active_role_faculty_dormant_engineer_denied_engineer_visibility(self):
        """A user with dormant iwd_engineer in roles but active_role='faculty' sees only own complaints."""
        c_assigned = Complaint.objects.create(user_id=102, category="civil", location="Lab 1", assigned_engineer_id=101)
        c_own = Complaint.objects.create(user_id=101, category="civil", location="My Lab")

        p = make_session(
            user_id=101,
            permissions=("iwd.complaint.view_self", "iwd.complaint.create"),
            modules=("iwd",),
            active_role="faculty",
            roles=("faculty", "iwd_engineer"),
        )
        visible = list(visible_complaints(p))
        assert c_own in visible
        assert c_assigned not in visible
        assert len(visible) == 1

    def test_legitimate_access_through_explicit_permissions(self):
        """Legitimate access via explicit administrative permission grants institute-wide visibility."""
        c1 = Complaint.objects.create(user_id=101, category="civil", location="Office 1")
        c2 = Complaint.objects.create(user_id=102, category="civil", location="Office 2")

        p = make_session(
            user_id=902,
            permissions=("iwd.complaint.view", "iwd.estimate.review_low"),
            modules=("iwd",),
            active_role="Department Head",
            roles=("Department Head",),
        )
        assert set(visible_complaints(p)) == {c1, c2}


# -- 4. API Endpoints ----------------------------------------------------------

class TestComplaintAPI:
    def test_submit_complaint_unauthenticated_401(self):
        client = APIClient()
        resp = client.post("/api/v1/iwd/complaints/", {"category": "civil", "location": "Room 1"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_submit_complaint_forbidden_without_create_perm_403(self, stub_iam):
        session = make_session(user_id=101, permissions=("iwd.complaint.view_self",), modules=("iwd",))
        client = make_client_for_session(stub_iam, session)
        resp = client.post("/api/v1/iwd/complaints/", {"category": "civil", "location": "Room 1"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_submit_complaint_success_and_auto_assigned_201(self, stub_iam):
        Engineer.objects.create(user_id=501, specialization="civil", is_active=True)
        session = make_session(user_id=101, permissions=("iwd.complaint.create", "iwd.complaint.view_self"), modules=("iwd",))
        client = make_client_for_session(stub_iam, session)

        payload = {
            "category": "civil",
            "location": "Hostel 3, Room 104",
            "urgency": "medium",
            "remarks": "Broken chair",
        }
        resp = client.post("/api/v1/iwd/complaints/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["user_id"] == 101
        assert data["category"] == "civil"
        assert data["status"] == IWDState.ASSIGNED.value
        assert data["assigned_engineer_id"] == 501
        assert len(data["transitions"]) == 2

    def test_submit_complaint_no_engineer_returns_201_submitted(self, stub_iam):
        session = make_session(user_id=101, permissions=("iwd.complaint.create", "iwd.complaint.view_self"), modules=("iwd",))
        client = make_client_for_session(stub_iam, session)

        payload = {"category": "electrical", "location": "Server Room"}
        resp = client.post("/api/v1/iwd/complaints/", payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["status"] == IWDState.SUBMITTED.value
        assert data["assigned_engineer_id"] is None

    def test_list_complaints_employee_scoped(self, stub_iam):
        Complaint.objects.create(user_id=101, category="civil", location="A")
        Complaint.objects.create(user_id=102, category="civil", location="B")

        session = make_session(user_id=101, permissions=("iwd.complaint.create", "iwd.complaint.view_self"), modules=("iwd",))
        client = make_client_for_session(stub_iam, session)

        resp = client.get("/api/v1/iwd/complaints/")
        assert resp.status_code == status.HTTP_200_OK
        results = resp.json()
        assert len(results) == 1
        assert results[0]["user_id"] == 101

    def test_detail_complaint_out_of_scope_returns_404(self, stub_iam):
        other_complaint = Complaint.objects.create(user_id=102, category="civil", location="B")

        session = make_session(user_id=101, permissions=("iwd.complaint.view_self",), modules=("iwd",))
        client = make_client_for_session(stub_iam, session)

        resp = client.get(f"/api/v1/iwd/complaints/{other_complaint.pk}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_complaint_authorized_returns_200(self, stub_iam):
        c = Complaint.objects.create(user_id=101, category="civil", location="My Office")
        ComplaintTransition.objects.create(
            complaint=c, from_status="None", to_status="Submitted", actor_user_id=101
        )

        session = make_session(user_id=101, permissions=("iwd.complaint.view_self",), modules=("iwd",))
        client = make_client_for_session(stub_iam, session)

        resp = client.get(f"/api/v1/iwd/complaints/{c.pk}/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == c.pk
        assert len(data["transitions"]) == 1

    def test_api_list_dormant_admin_role_cannot_view_other_complaints(self, stub_iam):
        """API regression test: dormant admin role does not expose all complaints via API."""
        c_own = Complaint.objects.create(user_id=101, category="civil", location="Own Office")
        Complaint.objects.create(user_id=102, category="civil", location="Other Office")

        session = make_session(
            user_id=101,
            permissions=("iwd.complaint.view_self",),
            modules=("iwd",),
            active_role="faculty",
            roles=("faculty", "iwd_admin"),
        )
        client = make_client_for_session(stub_iam, session)

        resp = client.get("/api/v1/iwd/complaints/")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == c_own.pk

    def test_api_auditor_gets_empty_complaint_list_and_404_detail(self, stub_iam):
        """API regression test: Auditor gets empty list (200) and 404 on complaint detail."""
        c = Complaint.objects.create(user_id=101, category="civil", location="Lab 1")
        session = make_session(
            user_id=801,
            permissions=("iwd.complaint.view", "iwd.bill.audit"),
            modules=("iwd",),
            active_role="auditor",
            roles=("auditor",),
        )
        client = make_client_for_session(stub_iam, session)

        # List returns empty
        resp = client.get("/api/v1/iwd/complaints/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

        # Detail returns 404
        resp_detail = client.get(f"/api/v1/iwd/complaints/{c.pk}/")
        assert resp_detail.status_code == status.HTTP_404_NOT_FOUND

    def test_api_unassigned_filter_does_not_bypass_employee_scoping(self, stub_iam):
        """API test: unassigned=true filter on employee only returns their own unassigned complaints."""
        c_own_unassigned = Complaint.objects.create(
            user_id=101, category="civil", location="My Office", assigned_engineer_id=None, status="Submitted"
        )
        Complaint.objects.create(
            user_id=102, category="civil", location="Other Office", assigned_engineer_id=None, status="Submitted"
        )

        session = make_session(
            user_id=101,
            permissions=("iwd.complaint.view_self",),
            modules=("iwd",),
            active_role="faculty",
            roles=("faculty",),
        )
        client = make_client_for_session(stub_iam, session)

        resp = client.get("/api/v1/iwd/complaints/?unassigned=true")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == c_own_unassigned.pk


# -- 5. Contracts --------------------------------------------------------------

class TestComplaintContracts:
    def test_get_complaints_plural_retrieval(self):
        c1 = Complaint.objects.create(user_id=101, category="civil", location="A")
        c2 = Complaint.objects.create(user_id=102, category="electrical", location="B")

        result = get_complaints([c1.pk, c2.pk, 99999])
        assert len(result) == 2
        assert result[c1.pk].complainant_id == 101
        assert result[c1.pk].issue_category == "civil"
        assert result[c2.pk].complainant_id == 102
        assert result[c2.pk].issue_category == "electrical"

