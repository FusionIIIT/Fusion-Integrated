"""BR-002 – Active Complaint Supervisor Role Assignment Uniqueness.

Business Rule:
Exactly one active Complaint Supervisor must exist at any time; assigning
a new supervisor deactivates the previous one (Page 2 – Time-Bound Role Management).

Ambiguity Note (BR-A-001):
Enforced via application logic in `assign_cms_role` and role API, rather than
a database-level partial unique index.
"""

import pytest
from django.utils import timezone
from datetime import timedelta

from modules.complaints.models import CmsRoleAssignment
from modules.complaints import services

@pytest.mark.django_db
def test_br_002_supervisor_assignment_deactivates_previous_service():
    """Service-level: Assigning a new supervisor deactivates the previously active supervisor."""
    now = timezone.now()
    start = now
    end = now + timedelta(days=365)

    # First supervisor assignment
    s1 = services.assign_cms_role(
        role_type=CmsRoleAssignment.ROLE_SUPERVISOR,
        user_id=301,
        assigned_by_user_id=1,
        start_date=start,
        end_date=end,
    )
    assert s1.is_active is True

    # Second supervisor assignment mid-cycle
    s2 = services.assign_cms_role(
        role_type=CmsRoleAssignment.ROLE_SUPERVISOR,
        user_id=302,
        assigned_by_user_id=1,
        start_date=start + timedelta(days=30),
        end_date=end,
    )

    s1.refresh_from_db()
    s2.refresh_from_db()

    # Former supervisor is deactivated, new supervisor is active
    assert s1.is_active is False
    assert s2.is_active is True

    # Exactly one active supervisor exists
    active_supervisors = CmsRoleAssignment.objects.filter(
        role_type=CmsRoleAssignment.ROLE_SUPERVISOR,
        is_active=True,
    )
    assert active_supervisors.count() == 1
    assert active_supervisors.first().user_id == 302

@pytest.mark.django_db
def test_br_002_supervisor_assignment_api_deactivates_previous(api_client, stub_iam, make_session):
    """API-level: POST /api/v1/complaints/roles/ for supervisor deactivates existing active supervisor."""
    admin_session = make_session(
        user_id=1,
        permissions=["complaints.role.manage"],
        kind="admin",
        active_role="admin",
    )
    stub_iam(session=admin_session)

    now = timezone.now()
    start_str = now.isoformat()
    end_str = (now + timedelta(days=365)).isoformat()

    # Assign first supervisor via API
    payload1 = {
        "role_type": "supervisor",
        "user_id": 401,
        "start_date": start_str,
        "end_date": end_str,
    }
    res1 = api_client.post("/api/v1/complaints/roles/", payload1, format="json")
    assert res1.status_code == 201
    assert res1.json()["is_active"] is True

    # Assign second supervisor via API
    payload2 = {
        "role_type": "supervisor",
        "user_id": 402,
        "start_date": start_str,
        "end_date": end_str,
    }
    res2 = api_client.post("/api/v1/complaints/roles/", payload2, format="json")
    assert res2.status_code == 201
    assert res2.json()["is_active"] is True

    # Verify only the second supervisor remains active in DB
    active_supervisors = CmsRoleAssignment.objects.filter(
        role_type="supervisor",
        is_active=True,
    )
    assert active_supervisors.count() == 1
    assert active_supervisors.first().user_id == 402
