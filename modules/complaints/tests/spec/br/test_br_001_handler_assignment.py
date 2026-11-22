"""BR-001 – Active Complaint Handler Role Assignment Uniqueness.

Business Rule:
Exactly one active Complaint Handler must exist at any time; assigning
a new handler deactivates the previous one (Page 2 – Time-Bound Role Management).

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
def test_br_001_handler_assignment_deactivates_previous_service():
    """Service-level: Assigning a new handler deactivates the previously active handler."""
    now = timezone.now()
    start = now
    end = now + timedelta(days=180)

    # First handler assignment
    h1 = services.assign_cms_role(
        role_type=CmsRoleAssignment.ROLE_HANDLER,
        user_id=101,
        assigned_by_user_id=1,
        start_date=start,
        end_date=end,
    )
    assert h1.is_active is True

    # Second handler assignment mid-cycle
    h2 = services.assign_cms_role(
        role_type=CmsRoleAssignment.ROLE_HANDLER,
        user_id=102,
        assigned_by_user_id=1,
        start_date=start + timedelta(days=10),
        end_date=end,
    )

    h1.refresh_from_db()
    h2.refresh_from_db()

    # Former handler is deactivated, new handler is active
    assert h1.is_active is False
    assert h2.is_active is True

    # Exactly one active handler exists
    active_handlers = CmsRoleAssignment.objects.filter(
        role_type=CmsRoleAssignment.ROLE_HANDLER,
        is_active=True,
    )
    assert active_handlers.count() == 1
    assert active_handlers.first().user_id == 102

@pytest.mark.django_db
def test_br_001_handler_assignment_api_deactivates_previous(api_client, stub_iam, make_session):
    """API-level: POST /api/v1/complaints/roles/ for handler deactivates existing active handler."""
    admin_session = make_session(
        user_id=1,
        permissions=["complaints.role.manage"],
        kind="admin",
        active_role="admin",
    )
    stub_iam(session=admin_session)

    now = timezone.now()
    start_str = now.isoformat()
    end_str = (now + timedelta(days=180)).isoformat()

    # Assign first handler via API
    payload1 = {
        "role_type": "handler",
        "user_id": 201,
        "start_date": start_str,
        "end_date": end_str,
    }
    res1 = api_client.post("/api/v1/complaints/roles/", payload1, format="json")
    assert res1.status_code == 201
    assert res1.json()["is_active"] is True

    # Assign second handler via API
    payload2 = {
        "role_type": "handler",
        "user_id": 202,
        "start_date": start_str,
        "end_date": end_str,
    }
    res2 = api_client.post("/api/v1/complaints/roles/", payload2, format="json")
    assert res2.status_code == 201
    assert res2.json()["is_active"] is True

    # Verify only the second handler remains active in DB
    active_handlers = CmsRoleAssignment.objects.filter(
        role_type="handler",
        is_active=True,
    )
    assert active_handlers.count() == 1
    assert active_handlers.first().user_id == 202
