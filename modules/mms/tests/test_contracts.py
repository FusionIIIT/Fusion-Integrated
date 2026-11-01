"""Cross-module contract tests verifying plural contract getters."""

import datetime

import pytest

from modules.mms import contracts
from modules.mms.domain.constants import MessRole, RebateStatus, RegistrationStatus
from modules.mms.models import MessRegistration, MessRoleAssignment, RebateRequest

pytestmark = pytest.mark.django_db


def test_contract_get_student_mess_registrations():
    MessRegistration.objects.create(
        student_id=7001,
        start_date=datetime.date(2026, 8, 1),
        status=RegistrationStatus.REGISTERED.value,
    )
    MessRegistration.objects.create(
        student_id=7002,
        start_date=datetime.date(2026, 8, 1),
        status=RegistrationStatus.REGISTERED.value,
    )

    results = contracts.get_student_mess_registrations([7001, 7002, 7003])
    assert 7001 in results
    assert 7002 in results
    assert 7003 not in results
    assert len(results[7001]) == 1
    assert results[7001][0]["status"] == RegistrationStatus.REGISTERED.value


def test_contract_get_student_approved_rebates():
    RebateRequest.objects.create(
        student_id=7001,
        start_date=datetime.date(2026, 11, 10),
        end_date=datetime.date(2026, 11, 15),
        duration_days=6,
        status=RebateStatus.APPROVED.value,
        approved_start_date=datetime.date(2026, 11, 10),
        approved_end_date=datetime.date(2026, 11, 15),
    )
    RebateRequest.objects.create(
        student_id=7001,
        start_date=datetime.date(2026, 12, 1),
        end_date=datetime.date(2026, 12, 5),
        duration_days=5,
        status=RebateStatus.PENDING.value,
    )

    results = contracts.get_student_approved_rebates([7001])
    assert 7001 in results
    assert len(results[7001]) == 1
    assert results[7001][0]["duration_days"] == 6


def test_contract_get_active_mess_roles():
    MessRoleAssignment.objects.create(
        employee_id=8001,
        role=MessRole.CARETAKER.value,
        start_date=datetime.date.today(),
        is_active=True,
    )
    MessRoleAssignment.objects.create(
        employee_id=8002,
        role=MessRole.WARDEN.value,
        start_date=datetime.date.today(),
        is_active=False,
    )

    roles = contracts.get_active_mess_roles([MessRole.CARETAKER.value, MessRole.WARDEN.value])
    assert MessRole.CARETAKER.value in roles
    assert len(roles[MessRole.CARETAKER.value]) == 1
    assert roles[MessRole.CARETAKER.value][0]["employee_id"] == 8001
    assert len(roles.get(MessRole.WARDEN.value, [])) == 0
