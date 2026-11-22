"""WF Test Suite 3: User Deactivation and Archival Lifecycle (BW-SA-06..08, CW-SA-03)."""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from modules.systemadmin.models import BasicUserProfile
from modules.systemadmin.services.archival_service import ArchivalError, ArchivalService
from modules.systemadmin.services.user_service import UserService


def ensure_test_user(iid, utype="faculty", dept="CSE"):
    u = BasicUserProfile.objects.filter(institute_id=iid).first()
    if not u:
        kw = {
            "institute_id": iid,
            "user_type": utype,
            "full_name": f"User {iid}",
            "institute_email": f"{iid.lower()}@iiitdmj.ac.in",
            "date_of_joining": date(2024, 1, 1),
            "department": dept,
        }
        if utype == "student":
            kw["programme"] = "B.Tech"
            kw["batch_year"] = 2026
        else:
            kw["employee_id"] = f"EMP_{iid}"
        u = UserService.create_basic_user(**kw)
    return u


pytestmark = pytest.mark.django_db

# --- BW-SA-06: Deactivated User Reactivation ---


def test_wf_014_deactivated_user_reactivation_path():
    """TEST_WF_014 | BW-SA-06: Verify deactivated user reactivation basis path: active -> deactivated -> reactivated -> active."""
    u = ensure_test_user("WF_USER_014", "faculty")
    assert u.status == "active"

    # Step 1: Deactivate
    UserService.deactivate_user(user_id=u.id, reason="Temporary leave")
    u.refresh_from_db()
    assert u.status == "deactivated"
    assert u.has_dashboard_access is False

    # Step 2: Reactivate
    UserService.reactivate_user(user_id=u.id, reason="Returned from leave")
    u.refresh_from_db()
    assert u.status == "active"
    assert u.has_dashboard_access is True


# --- BW-SA-07: Archived User Restoration Within Reversible Window ---


def test_wf_015_archived_user_restoration_within_window_path():
    """TEST_WF_015 | BW-SA-07: Verify archived user restoration within reversible window: deactivated -> archived reversible -> restored active."""
    u = ensure_test_user("WF_USER_015", "faculty")
    UserService.deactivate_user(user_id=u.id, reason="Retired")

    # Step 1: Archive (with bypass_interval=True or elapsed interval)
    archived = ArchivalService.archive_user(user_id=u.id, reason="Archival", bypass_interval=True)
    assert archived.status == "reversible"
    u.refresh_from_db()
    assert u.status == "archived"

    # Step 2: Restore within reversible window
    restored = ArchivalService.restore_archived_user(
        archived_user_id=archived.id, authorization_ref="DIR-WF-REST-015"
    )
    assert restored.status == "active"
    archived.refresh_from_db()
    assert archived.status == "restored"


# --- BW-SA-08: Archived User Reversibility Window Expiry ---


def test_wf_016_archived_user_reversibility_expiry_path():
    """TEST_WF_016 | BW-SA-08: Verify archived user reversibility window expiry path: deactivated -> archived reversible -> window expires -> permanent non-restorable."""
    u = ensure_test_user("WF_USER_016", "faculty")
    UserService.deactivate_user(user_id=u.id, reason="Left institute")
    archived = ArchivalService.archive_user(user_id=u.id, reason="Archival", bypass_interval=True)
    assert archived.status == "reversible"

    # Simulate window expiry
    archived.reversibility_deadline = timezone.now() - timedelta(days=1)
    archived.save()

    finalized_count = ArchivalService.finalize_non_restorable_archived_users()
    assert finalized_count >= 1
    archived.refresh_from_db()
    assert archived.status == "permanent_non_restorable"


# --- CW-SA-03: Deactivated User Resolution and Archive Lifecycle ---


def test_wf_017_cw_user_reactivation_branch():
    """TEST_WF_017 | CW-SA-03: Verify composite lifecycle branch 1A: deactivated user direct reactivation path."""
    u = ensure_test_user("WF_CW_017", "faculty")
    UserService.deactivate_user(user_id=u.id, reason="Sabbatical")
    UserService.reactivate_user(user_id=u.id, reason="Resumed duties")
    u.refresh_from_db()
    assert u.status == "active"


def test_wf_018_cw_user_archival_and_restore_branch():
    """TEST_WF_018 | CW-SA-03: Verify composite lifecycle branch 1B -> 2A: deactivated user archival followed by valid restoration."""
    u = ensure_test_user("WF_CW_018", "faculty")
    UserService.deactivate_user(user_id=u.id, reason="Separation")
    archived = ArchivalService.archive_user(
        user_id=u.id, reason="Standard archive", bypass_interval=True
    )
    restored = ArchivalService.restore_archived_user(
        archived_user_id=archived.id, authorization_ref="AUTH-CW-018"
    )
    assert restored.status == "active"


def test_wf_019_cw_user_archival_and_finalize_branch():
    """TEST_WF_019 | CW-SA-03: Verify composite lifecycle branch 1B -> 2B: deactivated user archival followed by reversibility window expiry."""
    u = ensure_test_user("WF_CW_019", "faculty")
    UserService.deactivate_user(user_id=u.id, reason="Retired")
    archived = ArchivalService.archive_user(
        user_id=u.id, reason="Long term archive", bypass_interval=True
    )
    archived.reversibility_deadline = timezone.now() - timedelta(days=2)
    archived.save()
    ArchivalService.finalize_non_restorable_archived_users()
    archived.refresh_from_db()
    assert archived.status == "permanent_non_restorable"


def test_wf_020_cw_user_archival_guard_unelapsed_interval():
    """TEST_WF_020 | CW-SA-03: Verify composite lifecycle guard condition: premature archival rejected when deactivation interval unelapsed."""
    u = ensure_test_user("WF_CW_020", "faculty")
    UserService.deactivate_user(user_id=u.id, reason="Just left")
    u.refresh_from_db()
    u.deactivated_at = timezone.now() - timedelta(days=1)
    u.save()
    with pytest.raises(ArchivalError):
        ArchivalService.archive_user(user_id=u.id, reason="Too early", bypass_interval=False)


def test_wf_021_cw_user_restoration_guard_post_window():
    """TEST_WF_021 | CW-SA-03: Verify composite lifecycle guard condition: restoration rejected after reversible period expires."""
    u = ensure_test_user("WF_CW_021", "faculty")
    UserService.deactivate_user(user_id=u.id, reason="Resigned")
    archived = ArchivalService.archive_user(user_id=u.id, reason="Archived", bypass_interval=True)
    archived.reversibility_deadline = timezone.now() - timedelta(days=10)
    archived.save()
    with pytest.raises(ArchivalError):
        ArchivalService.restore_archived_user(
            archived_user_id=archived.id, authorization_ref="AUTH-TOO-LATE"
        )
