import pytest
from conftest import make_session, make_principal
from modules.badms.domain import permissions as p
from modules.badms.registry import ROLE_GRANTS
from modules.badms.services.department import (
    get_user_department,
    is_hod_of_department,
    can_review_department_request,
)
from modules.directory.models import UserRef

pytestmark = pytest.mark.django_db


def test_role_grants_separation_of_duties():
    # Regular users have self-service only
    for role in ("student", "faculty", "staff"):
        grants = set(ROLE_GRANTS[role])
        assert p.ARCHIVE_CREATE in grants
        assert p.ARCHIVE_VIEW_SELF in grants
        assert p.ARCHIVE_REVIEW not in grants
        assert p.ARCHIVE_CLASSIFY not in grants
        assert p.BACKUP_CREATE not in grants
        assert p.BACKUP_MANAGE not in grants

    # HoD has review rights, but not sysadmin classification or backup management
    hod_grants = set(ROLE_GRANTS["HOD"])
    assert p.ARCHIVE_REVIEW in hod_grants
    assert p.STORAGE_REVIEW in hod_grants
    assert p.ARCHIVE_CLASSIFY not in hod_grants
    assert p.BACKUP_MANAGE not in hod_grants

    # SysAdmin has classification, backups, and restoration approvals
    sysadmin_grants = set(ROLE_GRANTS["sysadmin"])
    assert p.ARCHIVE_CLASSIFY in sysadmin_grants
    assert p.BACKUP_MANAGE in sysadmin_grants
    assert p.RESTORATION_APPROVE in sysadmin_grants
    assert p.ARCHIVE_SPECIAL not in sysadmin_grants  # Special archival is Super Admin only

    # Super Admin holds special archival and global policy
    super_admin_grants = set(ROLE_GRANTS["Super Admin"])
    assert p.ARCHIVE_SPECIAL in super_admin_grants
    assert p.POLICY_MANAGE in super_admin_grants

    # IT Security configures encryption and views audits
    security_grants = set(ROLE_GRANTS["IT Security"])
    assert p.ARCHIVE_ENCRYPT in security_grants
    assert p.AUDIT_VIEW in security_grants
    assert p.ARCHIVE_CLASSIFY not in security_grants
    assert p.BACKUP_CREATE not in security_grants

    # Director of IT receives view-only visibility without workflow mutation permissions
    director_grants = set(ROLE_GRANTS["Director of IT"])
    assert p.BACKUP_VIEW in director_grants
    assert p.REPORT_VIEW in director_grants
    assert p.BACKUP_CREATE not in director_grants
    assert p.ARCHIVE_REVIEW not in director_grants
    assert p.ARCHIVE_CLASSIFY not in director_grants
    assert p.RESTORATION_APPROVE not in director_grants


def test_get_user_department(user_ref):
    UserRef.objects.create(
        user_id=101,
        username="u101",
        display_name="Student CSE",
        kind="student",
        department="CSE",
        discipline="CSE",
    )
    assert get_user_department(101) == "CSE"
    assert get_user_department(999) == ""


def test_hod_department_scoping_isolation():
    # Create HoD for CSE (user 201) and HoD for ECE (user 202)
    UserRef.objects.create(
        user_id=201,
        username="hod_cse",
        display_name="HoD CSE",
        kind="faculty",
        department="CSE",
    )
    UserRef.objects.create(
        user_id=202,
        username="hod_ece",
        display_name="HoD ECE",
        kind="faculty",
        department="ECE",
    )

    hod_cse_principal = make_principal(
        user_id=201,
        kind="faculty",
        active_role="HOD",
        roles=("faculty", "HOD"),
        modules=("badms",),
        permissions=(p.ARCHIVE_REVIEW, p.STORAGE_REVIEW, p.ARCHIVE_VIEW),
    )
    hod_ece_principal = make_principal(
        user_id=202,
        kind="faculty",
        active_role="HOD",
        roles=("faculty", "HOD"),
        modules=("badms",),
        permissions=(p.ARCHIVE_REVIEW, p.STORAGE_REVIEW, p.ARCHIVE_VIEW),
    )

    # CSE HoD can review CSE requests
    assert is_hod_of_department(hod_cse_principal, "CSE") is True
    assert can_review_department_request(hod_cse_principal, "CSE") is True

    # CSE HoD CANNOT review ECE requests (cross-department isolation)
    assert is_hod_of_department(hod_cse_principal, "ECE") is False
    assert can_review_department_request(hod_cse_principal, "ECE") is False

    # ECE HoD can review ECE requests
    assert is_hod_of_department(hod_ece_principal, "ECE") is True
    assert can_review_department_request(hod_ece_principal, "ECE") is True

    # ECE HoD CANNOT review CSE requests
    assert is_hod_of_department(hod_ece_principal, "CSE") is False
    assert can_review_department_request(hod_ece_principal, "CSE") is False


def test_student_cannot_act_as_hod():
    UserRef.objects.create(
        user_id=301,
        username="stu301",
        display_name="Student",
        kind="student",
        department="CSE",
    )
    student_principal = make_principal(
        user_id=301,
        kind="student",
        active_role="student",
        roles=("student",),
        modules=("badms",),
        permissions=(p.ARCHIVE_VIEW_SELF, p.ARCHIVE_CREATE),
    )
    assert is_hod_of_department(student_principal, "CSE") is False
    assert can_review_department_request(student_principal, "CSE") is False


def test_sysadmin_has_global_review_override():
    UserRef.objects.create(
        user_id=401,
        username="sysadmin",
        display_name="Sys Admin",
        kind="staff",
        department="CC",
    )
    sysadmin_principal = make_principal(
        user_id=401,
        kind="staff",
        active_role="sysadmin",
        roles=("staff", "sysadmin"),
        modules=("badms",),
        permissions=(p.ARCHIVE_CLASSIFY, p.ARCHIVE_VIEW),
    )
    # SysAdmin can review across departments for authoritative classification
    assert can_review_department_request(sysadmin_principal, "CSE") is True
    assert can_review_department_request(sysadmin_principal, "ECE") is True
