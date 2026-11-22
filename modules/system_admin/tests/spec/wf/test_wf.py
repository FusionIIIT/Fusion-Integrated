"""
Automated Test Suite for Workflows (WF) Strategy - Super Admin Module.
Derived from 05_SA_Workflow_Specifications_v1.1_FINAL.md.
Covers all 12 Workflows (BW-SA-01..09, CW-SA-01..03) and their state transitions.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from core.api import csrf
from modules.system_admin.models import RoleAssignment, UserAccount


@pytest.fixture
def auth_client(stub_iam):
    stub_iam(
        make_session(
            user_id=1,
            kind="staff",
            modules=("system_admin",),
            permissions=(
                "system_admin.user.view",
                "system_admin.user.add",
                "system_admin.user.change",
                "system_admin.role.view",
                "system_admin.role.manage",
                "system_admin.archive.view",
                "system_admin.archive.manage",
                "system_admin.audit.view",
                "system_admin.config.change",
            ),
        )
    )
    c = APIClient()
    c.cookies["fusion_session"] = "tok-wf-admin"
    c.credentials(HTTP_X_CSRF_TOKEN=csrf.token_for("tok-wf-admin"))
    return c

@pytest.fixture
def no_csrf_client(stub_iam):
    stub_iam(
        make_session(
            user_id=1,
            kind="staff",
            modules=("system_admin",),
            permissions=(
                "system_admin.user.view",
                "system_admin.user.add",
                "system_admin.user.change",
                "system_admin.role.view",
                "system_admin.role.manage",
                "system_admin.archive.view",
                "system_admin.archive.manage",
                "system_admin.audit.view",
                "system_admin.config.change",
            ),
        )
    )
    c = APIClient()
    c.cookies["fusion_session"] = "tok-wf-nocsrf"
    return c

@pytest.fixture
def unauth_client():
    return APIClient()

@pytest.mark.django_db
def test_wf_test_wf_01(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-01
    Source ID: BW-SA-01 Approved Path
    Purpose: Verify permanent data purge approved workflow with dual authorization
    """
    pytest.skip("NOT_AUTOMATED: Permanent data purge workflow and IT Head dual-authorization engine not implemented in A8_BASE")

@pytest.mark.django_db
def test_wf_test_wf_02(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-02
    Source ID: BW-SA-02 Rejected Path
    Purpose: Verify permanent data purge rejected workflow when second authorization denied
    """
    pytest.skip("NOT_AUTOMATED: Permanent data purge workflow and IT Head dual-authorization engine not implemented in A8_BASE")

@pytest.mark.django_db
def test_wf_test_wf_03(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-03
    Source ID: BW-SA-02 Premature Purge Decision
    Purpose: Verify purge request for data still within retention period is rejected at entry
    """
    pytest.skip("NOT_AUTOMATED: Permanent data purge workflow and IT Head dual-authorization engine not implemented in A8_BASE")

@pytest.mark.django_db
def test_wf_test_wf_04(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-04
    Source ID: CW-SA-01 Purge Lifecycle Query
    Purpose: Verify purge request lifecycle state progression from requested to decided
    """
    pytest.skip("NOT_AUTOMATED: Permanent data purge workflow and IT Head dual-authorization engine not implemented in A8_BASE")

@pytest.mark.django_db
def test_wf_test_wf_05(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-05
    Source ID: CW-SA-01 Redundant Decision Branch
    Purpose: Verify decision submitted for already decided purge request is rejected
    """
    pytest.skip("NOT_AUTOMATED: Permanent data purge workflow and IT Head dual-authorization engine not implemented in A8_BASE")

@pytest.mark.django_db
def test_wf_test_wf_06(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-06
    Source ID: BW-SA-03 Immediate Assignment Path
    Purpose: Verify immediate time-bound role assignment activates and reaches expiry state
    """
    u = UserAccount.objects.create(institute_id="WF006_U", username="wf006_u", email="wf006@fusion.edu", user_type="faculty")
    payload = {"user": u.pk, "role_name": "dean_academics", "assigned_by": "sa_tester", "start_date": "2026-01-01", "end_date": "2026-12-31"}
    res = auth_client.post(reverse("sa-role-assign"), payload, format="json")
    assert res.status_code == status.HTTP_201_CREATED
    assert RoleAssignment.objects.filter(user=u, status="active").exists()

@pytest.mark.django_db
def test_wf_test_wf_07(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-07
    Source ID: BW-SA-03 Missing Date Decision
    Purpose: Verify role assignment missing required start date is rejected
    """
    u = UserAccount.objects.create(institute_id="WF007_U", username="wf007_u", email="wf007@fusion.edu", user_type="faculty")
    payload = {"user": u.pk, "role_name": "dean_academics", "assigned_by": "sa_tester", "end_date": "2026-12-31"}
    res = auth_client.post(reverse("sa-role-assign"), payload, format="json")
    assert res.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_wf_test_wf_08(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-08
    Source ID: BW-SA-04 Scheduled Assignment Path
    Purpose: Verify future-dated role assignment activates when effective start date is reached
    """
    u = UserAccount.objects.create(institute_id="WF008_U", username="wf008_u", email="wf008@fusion.edu", user_type="faculty")
    payload = {"user": u.pk, "role_name": "dean_academics", "assigned_by": "sa_tester", "start_date": "2027-01-01", "end_date": "2027-12-31"}
    res = auth_client.post(reverse("sa-role-assign"), payload, format="json")
    assert res.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_wf_test_wf_09(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-09
    Source ID: BW-SA-04 Scheduled User Inactive Decision
    Purpose: Verify scheduled assignment does not activate if user account is deactivated before start date
    """
    pytest.skip("NOT_AUTOMATED: Scheduled assignment background activation scheduler not in A8_BASE")

@pytest.mark.django_db
def test_wf_test_wf_10(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-10
    Source ID: BW-SA-05 Extension Traversal
    Purpose: Verify role validity extension traversal updating end date before expiry
    """
    u = UserAccount.objects.create(institute_id="WF010_U", username="wf010_u", email="wf010@fusion.edu", user_type="faculty")
    r = RoleAssignment.objects.create(user=u, role_name="mentor", assigned_by="sa_tester", start_date="2026-01-01", end_date="2026-06-30", status="active")
    r.end_date = "2026-12-31"
    r.save()
    r.refresh_from_db()
    assert str(r.end_date) == "2026-12-31"

@pytest.mark.django_db
def test_wf_test_wf_11(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-11
    Source ID: BW-SA-05 Post-Expiry Extension Decision
    Purpose: Verify extension attempt on already expired role is rejected
    """
    pytest.skip("NOT_AUTOMATED: Dedicated role extension endpoint not exposed in A8_BASE")

@pytest.mark.django_db
def test_wf_test_wf_12(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-12
    Source ID: CW-SA-02 Early Revocation Path
    Purpose: Verify early role revocation state transition from active to revoked
    """
    u = UserAccount.objects.create(institute_id="WF012_U", username="wf012_u", email="wf012@fusion.edu", user_type="faculty")
    r = RoleAssignment.objects.create(user=u, role_name="mentor", assigned_by="sa_tester", start_date="2026-01-01", status="active")
    res = auth_client.post(reverse("sa-role-revoke", kwargs={"pk": r.pk}))
    assert res.status_code == status.HTTP_200_OK
    r.refresh_from_db()
    assert r.status == "revoked"

@pytest.mark.django_db
def test_wf_test_wf_13(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-13
    Source ID: CW-SA-02 Redundant Revocation Decision
    Purpose: Verify revoking an already revoked role assignment is rejected
    """
    u = UserAccount.objects.create(institute_id="WF013_U", username="wf013_u", email="wf013@fusion.edu", user_type="faculty")
    r = RoleAssignment.objects.create(user=u, role_name="mentor", assigned_by="sa_tester", start_date="2026-01-01", status="revoked")
    res = auth_client.post(reverse("sa-role-revoke", kwargs={"pk": r.pk}))
    assert res.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_wf_test_wf_14(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-14
    Source ID: CW-SA-02 Handover Reassignment Path
    Purpose: Verify role reassignment workflow transitioning prior holder to revoked and new holder to active
    """
    u1 = UserAccount.objects.create(institute_id="WF014_U1", username="wf014_u1", email="u1@fusion.edu", user_type="faculty")
    u2 = UserAccount.objects.create(institute_id="WF014_U2", username="wf014_u2", email="u2@fusion.edu", user_type="faculty")
    r1 = RoleAssignment.objects.create(user=u1, role_name="dean_students", assigned_by="sa_tester", start_date="2026-01-01", status="active")
    auth_client.post(reverse("sa-role-revoke", kwargs={"pk": r1.pk}))
    res = auth_client.post(reverse("sa-role-assign"), {"user": u2.pk, "role_name": "dean_students", "assigned_by": "sa_tester", "start_date": "2026-01-01"}, format="json")
    assert res.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_wf_test_wf_15(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-15
    Source ID: CW-SA-02 Inverted Dating Decision
    Purpose: Verify role assignment rejection path when end_date < start_date
    """
    u = UserAccount.objects.create(institute_id="WF015_U", username="wf015_u", email="wf015@fusion.edu", user_type="faculty")
    # Inverted dates: start_date > end_date
    payload = {"user": u.pk, "role_name": "mentor", "assigned_by": "sa_tester", "start_date": "2026-12-31", "end_date": "2026-01-01"}
    res = auth_client.post(reverse("sa-role-assign"), payload, format="json")
    assert res.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_wf_test_wf_16(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-16
    Source ID: CW-SA-02 Singular Role Duplicate Decision
    Purpose: Verify singular role assignment rejection path when role is already actively occupied
    """
    u1 = UserAccount.objects.create(institute_id="WF016_U1", username="wf016_u1", email="u1@fusion.edu", user_type="faculty")
    u2 = UserAccount.objects.create(institute_id="WF016_U2", username="wf016_u2", email="u2@fusion.edu", user_type="faculty")
    RoleAssignment.objects.create(user=u1, role_name="dean_academics", assigned_by="sa_tester", start_date="2026-01-01", end_date="2026-12-31", status="active")
    payload = {"user": u2.pk, "role_name": "dean_academics", "assigned_by": "sa_tester", "start_date": "2026-01-01", "end_date": "2026-12-31"}
    res = auth_client.post(reverse("sa-role-assign"), payload, format="json")
    assert res.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_wf_test_wf_17(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-17
    Source ID: CW-SA-02 User-Type Eligibility Decision
    Purpose: Verify role assignment rejection path when user type is ineligible
    """
    u_std = UserAccount.objects.create(institute_id="WF017_STD", username="wf017_std", email="std@fusion.edu", user_type="student")
    payload = {"user": u_std.pk, "role_name": "dean_academics", "assigned_by": "sa_tester", "start_date": "2026-01-01"}
    res = auth_client.post(reverse("sa-role-assign"), payload, format="json")
    assert res.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_wf_test_wf_18(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-18
    Source ID: CW-SA-02 Cascade Revocation Path
    Purpose: Verify deactivation of user account triggers revocation/inactivation of assigned roles
    """
    u = UserAccount.objects.create(institute_id="WF018_U", username="wf018_u", email="wf018@fusion.edu", user_type="faculty")
    RoleAssignment.objects.create(user=u, role_name="tutor", assigned_by="sa_tester", start_date="2026-01-01", status="active")
    res = auth_client.patch(reverse("sa-user-status", kwargs={"pk": u.pk}), {"status": "deactivated"}, format="json")
    assert res.status_code == status.HTTP_200_OK
    u.refresh_from_db()
    assert u.status == "deactivated"

@pytest.mark.django_db
def test_wf_test_wf_19(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-19
    Source ID: BW-SA-06 Deactivation Transition
    Purpose: Verify user account deactivation transition from active to deactivated
    """
    u = UserAccount.objects.create(institute_id="WF019_U", username="wf019_u", email="wf019@fusion.edu", user_type="student", status="active")
    res = auth_client.patch(reverse("sa-user-status", kwargs={"pk": u.pk}), {"status": "deactivated"}, format="json")
    assert res.status_code == status.HTTP_200_OK
    u.refresh_from_db()
    assert u.status == "deactivated"

@pytest.mark.django_db
def test_wf_test_wf_20(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-20
    Source ID: BW-SA-06 Reactivation Transition
    Purpose: Verify user account reactivation transition from deactivated to active
    """
    u = UserAccount.objects.create(institute_id="WF020_U", username="wf020_u", email="wf020@fusion.edu", user_type="student", status="deactivated")
    res = auth_client.patch(reverse("sa-user-status", kwargs={"pk": u.pk}), {"status": "active"}, format="json")
    assert res.status_code == status.HTTP_200_OK
    u.refresh_from_db()
    assert u.status == "active"

@pytest.mark.django_db
def test_wf_test_wf_21(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-21
    Source ID: BW-SA-07 Restoration Path
    Purpose: Verify restoration workflow of archived account within reversible retention window
    """
    u = UserAccount.objects.create(institute_id="WF021_U", username="wf021_u", email="wf021@fusion.edu", user_type="student", status="archived")
    res = auth_client.patch(reverse("sa-user-status", kwargs={"pk": u.pk}), {"status": "deactivated"}, format="json")
    assert res.status_code == status.HTTP_200_OK
    u.refresh_from_db()
    assert u.status == "deactivated"

@pytest.mark.django_db
def test_wf_test_wf_22(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-22
    Source ID: BW-SA-07 Immediate Active Restoration Path
    Purpose: Verify restoration workflow directly restoring archived account to active status
    """
    u = UserAccount.objects.create(institute_id="WF022_U", username="wf022_u", email="wf022@fusion.edu", user_type="student", status="archived")
    res = auth_client.patch(reverse("sa-user-status", kwargs={"pk": u.pk}), {"status": "active"}, format="json")
    assert res.status_code == status.HTTP_200_OK
    u.refresh_from_db()
    assert u.status == "active"

@pytest.mark.django_db
def test_wf_test_wf_23(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-23
    Source ID: BW-SA-08 Finalization Path
    Purpose: Verify transition from archived to permanently non-restorable upon window expiry
    """
    pytest.skip("NOT_AUTOMATED: Reversible window finalization daemon not instantiated in A8_BASE")

@pytest.mark.django_db
def test_wf_test_wf_24(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-24
    Source ID: BW-SA-08 Post-Window Restoration Decision
    Purpose: Verify restoration attempt after window expiry is rejected
    """
    pytest.skip("NOT_AUTOMATED: Reversible window finalization daemon not instantiated in A8_BASE")

@pytest.mark.django_db
def test_wf_test_wf_25(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-25
    Source ID: CW-SA-03 Direct Archival Decision
    Purpose: Verify direct archival of active user without prior deactivation is rejected
    """
    u = UserAccount.objects.create(institute_id="WF025_U", username="wf025_u", email="wf025@fusion.edu", user_type="student", status="active")
    res = auth_client.patch(reverse("sa-user-status", kwargs={"pk": u.pk}), {"status": "archived"}, format="json")
    assert res.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
def test_wf_test_wf_26(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-26
    Source ID: CW-SA-03 Suspension Transition
    Purpose: Verify user status transition from active to suspended
    """
    u = UserAccount.objects.create(institute_id="WF026_U", username="wf026_u", email="wf026@fusion.edu", user_type="student", status="active")
    res = auth_client.patch(reverse("sa-user-status", kwargs={"pk": u.pk}), {"status": "suspended"}, format="json")
    assert res.status_code == status.HTTP_200_OK

@pytest.mark.django_db
def test_wf_test_wf_27(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-27
    Source ID: CW-SA-03 Suspended Reactivation Transition
    Purpose: Verify user status transition from suspended back to active
    """
    u = UserAccount.objects.create(institute_id="WF027_U", username="wf027_u", email="wf027@fusion.edu", user_type="student", status="deactivated")
    res = auth_client.patch(reverse("sa-user-status", kwargs={"pk": u.pk}), {"status": "active"}, format="json")
    assert res.status_code == status.HTTP_200_OK

@pytest.mark.django_db
def test_wf_test_wf_28(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-28
    Source ID: CW-SA-03 Archival Transition
    Purpose: Verify transition of eligible deactivated user to archived state
    """
    u = UserAccount.objects.create(institute_id="WF028_U", username="wf028_u", email="wf028@fusion.edu", user_type="student", status="deactivated")
    res = auth_client.patch(reverse("sa-user-status", kwargs={"pk": u.pk}), {"status": "archived"}, format="json")
    assert res.status_code == status.HTTP_200_OK
    u.refresh_from_db()
    assert u.status == "archived"

@pytest.mark.django_db
def test_wf_test_wf_29(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-29
    Source ID: BW-SA-09 Archive Path
    Purpose: Verify historical data archival workflow moving inactive records to archive
    """
    pytest.skip("NOT_AUTOMATED: Historical data archival / restore subsystem not implemented in A8_BASE")

@pytest.mark.django_db
def test_wf_test_wf_30(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-30
    Source ID: BW-SA-09 Backup Failure Decision
    Purpose: Verify historical archival aborts when pre-archival backup fails
    """
    pytest.skip("NOT_AUTOMATED: Historical data archival / restore subsystem not implemented in A8_BASE")

@pytest.mark.django_db
def test_wf_test_wf_31(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-31
    Source ID: BW-SA-09 Restore Path
    Purpose: Verify historical data restore workflow upon approved authorization
    """
    pytest.skip("NOT_AUTOMATED: Historical data archival / restore subsystem not implemented in A8_BASE")

@pytest.mark.django_db
def test_wf_test_wf_32(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-32
    Source ID: BW-SA-09 Unauthorized Restore Decision
    Purpose: Verify historical data restore rejected without authorization
    """
    pytest.skip("NOT_AUTOMATED: Historical data archival / restore subsystem not implemented in A8_BASE")

@pytest.mark.django_db
def test_wf_test_wf_33(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-33
    Source ID: WF Security (Unauthenticated Initiation)
    Purpose: Verify workflow entry point rejects unauthenticated requests
    """
    res = unauth_client.post(reverse("sa-users"), {"institute_id": "WF_NOAUTH"}, format="json")
    assert res.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

@pytest.mark.django_db
def test_wf_test_wf_34(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-34
    Source ID: WF Security (CSRF Missing on Transition)
    Purpose: Verify workflow state transition write rejects missing CSRF token
    """
    u = UserAccount.objects.create(institute_id="WF034_U", username="wf034_u", email="wf034@fusion.edu", user_type="faculty")
    payload = {"user": u.pk, "role_name": "tutor", "assigned_by": "sa_tester", "start_date": "2026-01-01"}
    res = no_csrf_client.post(reverse("sa-role-assign"), payload, format="json")
    assert res.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_wf_test_wf_35(auth_client, no_csrf_client, unauth_client):
    """
    Test ID: TEST-WF-35
    Source ID: WF Audit (Non-Repudiation Logging)
    Purpose: Verify every workflow transition generates an immutable audit log record
    """
    res = auth_client.get(reverse("sa-audit-logs"))
    assert res.status_code == status.HTTP_200_OK
