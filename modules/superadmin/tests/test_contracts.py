"""Tests for Super Admin external plural contracts."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.superadmin.contracts import (
    get_active_role_assignments,
    get_archived_user_statuses,
    get_user_account_records,
)
from modules.superadmin.models import RoleAssignmentRecord, UserAccountRecord

pytestmark = pytest.mark.django_db


def test_empty_contract_queries_return_empty_dicts():
    assert get_user_account_records([]) == {}
    assert get_active_role_assignments([]) == {}
    assert get_archived_user_statuses([]) == {}


def test_get_user_account_records_plural_contract():
    UserAccountRecord.objects.create(
        user_id=101,
        institute_id="24BCS101",
        email="u101@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ACTIVE",
    )
    UserAccountRecord.objects.create(
        user_id=102,
        institute_id="24BCS102",
        email="u102@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="DEACTIVATED",
    )

    records = get_user_account_records([101, 102, 999])
    assert len(records) == 2
    assert records[101].institute_id == "24BCS101"
    assert records[101].activation_status == "ACTIVE"
    assert records[102].activation_status == "DEACTIVATED"
    assert 999 not in records


def test_get_active_role_assignments_plural_contract():
    now = timezone.now()
    RoleAssignmentRecord.objects.create(
        user_id=201,
        role_name="Faculty Advisor",
        valid_from=now - timedelta(days=5),
        status="ACTIVE",
        assigned_by_user_id=1,
    )
    # Expired role should not be in active roles
    RoleAssignmentRecord.objects.create(
        user_id=201,
        role_name="Course Instructor",
        valid_from=now - timedelta(days=50),
        valid_to=now - timedelta(days=1),
        status="EXPIRED",
        assigned_by_user_id=1,
    )

    active_map = get_active_role_assignments([201, 999])
    assert 201 in active_map
    assert len(active_map[201]) == 1
    assert active_map[201][0].role_name == "Faculty Advisor"
    assert active_map[999] == []


def test_get_archived_user_statuses_plural_contract():
    now = timezone.now()
    UserAccountRecord.objects.create(
        user_id=301,
        institute_id="24BCS301",
        email="u301@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ARCHIVED_REVERSIBLE",
        archival_date=now - timedelta(days=10),
        reversibility_expires_at=now + timedelta(days=80),
    )

    res = get_archived_user_statuses([301, 999])
    assert 301 in res
    assert res[301].status == "ARCHIVED_REVERSIBLE"
    assert res[301].is_reversible is True
    assert 999 not in res
