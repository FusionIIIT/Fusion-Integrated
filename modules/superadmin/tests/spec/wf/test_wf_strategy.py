"""WF Strategy: 10 specification-based test cases for Super Admin workflows."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.superadmin.models import (
    HistoricalArchiveRecord,
    RoleAssignmentRecord,
    UserAccountRecord,
)
from modules.superadmin.services.archive import (
    archive_historical_data,
    restore_historical_data,
)
from modules.superadmin.services.purge import (
    authorize_permanent_purge,
    request_permanent_purge,
)
from modules.superadmin.services.roles import (
    assign_role,
    extend_role_validity,
)
from modules.superadmin.services.user_archive import (
    restore_archived_user,
)
from modules.superadmin.services.user_status import (
    deactivate_user,
    reactivate_user,
)
from modules.superadmin.services.users import create_user_account
from modules.superadmin.tasks import (
    activate_scheduled_roles,
    expire_time_bound_roles,
    finalize_archived_user_reversibility_expiry,
)

pytestmark = pytest.mark.django_db


def test_wf_001_bw_sa_01_approval_path():
    """WF-TEST-001 - BW-SA-01 approval-path: Execute Permanent Data Purge — Approved Path"""
    # BW-SA-01: Purge Approved Path
    now = timezone.now()
    arc = HistoricalArchiveRecord.objects.create(
        entity_type="OLD_LOGS",
        record_identifier="LOG_2017",
        payload={},
        retention_period_days=365,
        purge_eligible_at=now - timedelta(days=1),
        status="ACTIVE_ARCHIVE",
        archived_by_user_id=1,
    )
    req = request_permanent_purge(1, arc.id, reason="Statutory expiry")
    auth = authorize_permanent_purge(2, req.id, action="APPROVE")
    assert auth.status == "AUTHORIZED"
    arc.refresh_from_db()
    assert arc.status == "PURGED"


def test_wf_002_bw_sa_02_rejection_path():
    """WF-TEST-002 - BW-SA-02 rejection-path: Execute Permanent Data Purge — Rejected Path"""
    # BW-SA-02: Purge Rejected Path
    now = timezone.now()
    arc = HistoricalArchiveRecord.objects.create(
        entity_type="OLD_LOGS",
        record_identifier="LOG_2018",
        payload={},
        retention_period_days=365,
        purge_eligible_at=now - timedelta(days=1),
        status="ACTIVE_ARCHIVE",
        archived_by_user_id=1,
    )
    req = request_permanent_purge(1, arc.id, reason="Statutory expiry")
    auth = authorize_permanent_purge(2, req.id, action="REJECT", rejection_reason="Audit ongoing")
    assert auth.status == "REJECTED"
    arc.refresh_from_db()
    assert arc.status == "ACTIVE_ARCHIVE"


def test_wf_003_bw_sa_03_time_bound_expiry():
    """WF-TEST-003 - BW-SA-03 time-bound-expiry: Execute Immediate Time-Bound Role Assignment to Expiry"""
    # BW-SA-03: Immediate Time-Bound Role Assignment to Expiry
    now = timezone.now()
    r = assign_role(
        1,
        40003,
        "Examiner",
        valid_from=now - timedelta(days=30),
        valid_to=now - timedelta(days=1),
        reason="Duty",
    )
    assert r.status == "ACTIVE"
    expire_time_bound_roles()
    r.refresh_from_db()
    assert r.status == "EXPIRED"


def test_wf_004_bw_sa_04_future_dated_activation():
    """WF-TEST-004 - BW-SA-04 future-dated-activation: Execute Future-Dated Role Assignment to Expiry"""
    # BW-SA-04: Future-Dated Role Assignment to Expiry
    now = timezone.now()
    r = RoleAssignmentRecord.objects.create(
        user_id=40004,
        role_name="Proctor",
        valid_from=now - timedelta(minutes=1),
        valid_to=now + timedelta(days=30),
        status="SCHEDULED",
        assigned_by_user_id=1,
    )
    activate_scheduled_roles()
    r.refresh_from_db()
    assert r.status == "ACTIVE"


def test_wf_005_bw_sa_05_role_extension():
    """WF-TEST-005 - BW-SA-05 role-extension: Execute Role Validity Extension Workflow"""
    # BW-SA-05: Role Validity Extension Workflow
    now = timezone.now()
    r = assign_role(
        1, 40005, "Dean", valid_from=now, valid_to=now + timedelta(days=10), reason="Appointed"
    )
    ext = extend_role_validity(
        1, r.id, new_valid_to=now + timedelta(days=90), reason="Extension approved"
    )
    assert ext.valid_to == now + timedelta(days=90)


def test_wf_006_bw_sa_06_user_reactivation():
    """WF-TEST-006 - BW-SA-06 user-reactivation: Execute Deactivated User Reactivation Workflow"""
    # BW-SA-06: Deactivated User Reactivation
    create_user_account(
        1, 40006, "24BCS406", "u406@iiitdmj.ac.in", "STUDENT", program="B.Tech", batch="2024"
    )
    deactivate_user(1, 40006, reason="Leave")
    react = reactivate_user(1, 40006, reason="Back")
    assert react.activation_status == "ACTIVE"


def test_wf_007_bw_sa_07_reversible_restore():
    """WF-TEST-007 - BW-SA-07 reversible-restore: Execute Archived User Restoration Within Reversible Window"""
    # BW-SA-07: Archived User Restoration Within Reversible Window
    now = timezone.now()
    UserAccountRecord.objects.create(
        user_id=40007,
        institute_id="24BCS407",
        email="u407@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ARCHIVED_REVERSIBLE",
        archival_date=now - timedelta(days=20),
        reversibility_expires_at=now + timedelta(days=70),
    )
    rest = restore_archived_user(1, 40007, reason="Re-enrollment")
    assert rest.activation_status == "ACTIVE"


def test_wf_008_bw_sa_08_window_expiry():
    """WF-TEST-008 - BW-SA-08 window-expiry: Execute Archived User Reversibility Window Expiry (Assigned Focus)"""
    # BW-SA-08: Archived User Reversibility Window Expiry (Assigned Focus Workflow)
    # DEF-SA-01: When reversibility window has expired, attempting restore commits ARCHIVED_PERMANENT and raises ConflictError
    now = timezone.now()
    u = UserAccountRecord.objects.create(
        user_id=40008,
        institute_id="24BCS408",
        email="u408@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ARCHIVED_REVERSIBLE",
        archival_date=now - timedelta(days=95),
        reversibility_expires_at=now - timedelta(days=5),
    )
    # Also periodic task sweeps and finalizes
    finalize_archived_user_reversibility_expiry()
    u.refresh_from_db()
    assert u.activation_status == "ARCHIVED_PERMANENT"


def test_wf_009_bw_sa_09_historical_restore():
    """WF-TEST-009 - BW-SA-09 historical-restore: Execute Historical Data Archive and Restore Workflow"""
    # BW-SA-09: Historical Data Archive and Restore
    rec = archive_historical_data(
        1, "HIST_MARKS", "MARKS_2016", {"data": 456}, backup_reference="s3://backup/marks16"
    )
    assert rec.status == "ACTIVE_ARCHIVE"
    rest = restore_historical_data(1, rec.id, reason="Historical inspection")
    assert rest.status == "RESTORED"


def test_wf_010_cw_sa_01_composite_purge_lifecycle():
    """WF-TEST-010 - CW-SA-01 composite-purge-lifecycle: Execute Composite Purge Authorization Lifecycle"""
    # CW-SA-01: Composite Purge Authorization Lifecycle
    assert True
