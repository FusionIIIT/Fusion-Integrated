"""End-to-end user and governance journey tests."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.superadmin.models import (
    AuditLogRecord,
    RoleHandoverRecord,
)
from modules.superadmin.services.archive import archive_historical_data
from modules.superadmin.services.purge import (
    authorize_permanent_purge,
    request_permanent_purge,
)
from modules.superadmin.services.roles import (
    assign_role,
    reassign_role_with_handover,
)
from modules.superadmin.services.user_archive import (
    archive_user,
    restore_archived_user,
)
from modules.superadmin.services.user_status import (
    deactivate_user,
    reactivate_user,
)
from modules.superadmin.services.users import create_user_account

pytestmark = pytest.mark.django_db


def test_complete_user_lifecycle_journey():
    # 1. Create account
    user = create_user_account(
        actor_user_id=1,
        user_id=9501,
        institute_id="24BCS9501",
        email="u9501@iiitdmj.ac.in",
        user_type="STUDENT",
        program="B.Tech",
        batch="2024",
    )
    assert user.activation_status == "ACTIVE"

    # 2. Deactivate account
    deactivate_user(actor_user_id=1, user_id=9501, reason="Temporary suspension")
    user.refresh_from_db()
    assert user.activation_status == "DEACTIVATED"

    # 3. Reactivate account
    reactivate_user(actor_user_id=1, user_id=9501, reason="Suspension lifted")
    user.refresh_from_db()
    assert user.activation_status == "ACTIVE"

    # 4. Deactivate again and archive
    deactivate_user(actor_user_id=1, user_id=9501, reason="Graduation")
    archive_user(actor_user_id=1, user_id=9501, reason="Completed degree")
    user.refresh_from_db()
    assert user.activation_status == "ARCHIVED_REVERSIBLE"
    assert user.reversibility_expires_at is not None

    # 5. Restore within reversibility window
    restore_archived_user(actor_user_id=1, user_id=9501, reason="Joined M.Tech program")
    user.refresh_from_db()
    assert user.activation_status == "ACTIVE"

    # 6. Verify audit logs were written for every step
    logs = AuditLogRecord.objects.filter(target_entity="USER", target_id="9501")
    assert logs.count() >= 5


def test_complete_role_handover_journey():
    now = timezone.now()
    # 1. Initial assignment to User 1
    assignment = assign_role(
        actor_user_id=1,
        user_id=9601,
        role_name="Head of Department (CSE)",
        valid_from=now,
        is_singular=True,
        reason="Initial appointment",
    )
    assert assignment.status == "ACTIVE"

    # 2. Reassign with handover to User 2
    old_assign, new_assign = reassign_role_with_handover(
        actor_user_id=1,
        assignment_id=assignment.id,
        successor_user_id=9602,
        effective_date=now + timedelta(days=1),
        handover_summary="Transferred pending departmental reviews.",
    )
    assert old_assign.status == "REVOKED"
    assert new_assign.user_id == 9602
    assert new_assign.status == "ACTIVE"

    # Handover record created
    handover = RoleHandoverRecord.objects.get(role_assignment=new_assign)
    assert handover.from_user_id == 9601
    assert handover.to_user_id == 9602
    assert handover.audit_access_granted is True


def test_complete_purge_dual_authorization_journey():
    # 1. Historical archive created
    archive = archive_historical_data(
        actor_user_id=1,
        entity_type="EXAM_MARKS_2018",
        record_identifier="EXAM_2018_SEM1",
        payload={"department": "ECE"},
        retention_period_days=365,
    )
    # Fast forward purge eligibility
    archive.purge_eligible_at = timezone.now() - timedelta(days=1)
    archive.save()

    # 2. Super Admin requests purge
    req = request_permanent_purge(
        actor_user_id=1,
        archive_id=archive.id,
        reason="Statutory retention expired",
    )
    assert req.status == "REQUESTED"

    # 3. IT Head authorizes purge
    authorized_req = authorize_permanent_purge(
        actor_user_id=2,  # Different user satisfies separation of duties
        request_id=req.id,
        action="APPROVE",
    )
    assert authorized_req.status == "AUTHORIZED"

    archive.refresh_from_db()
    assert archive.status == "PURGED"
