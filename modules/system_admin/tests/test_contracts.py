"""Cross-module public contracts verification tests."""
from datetime import date

import pytest

from modules.system_admin.contracts import (
    get_active_role_holders,
    get_user_admin_statuses,
    get_user_effective_roles,
)
from modules.system_admin.models.role_assignment import RoleAssignment
from modules.system_admin.models.user_account import UserAccount

pytestmark = pytest.mark.django_db


def test_public_contracts_plural_behavior():
    UserAccount.objects.create(
        user_id=8001,
        institute_id="2024BCS801",
        username="contract_user_1",
        email="c1@iiitdmj.ac.in",
        user_type="student",
        status="active",
    )
    UserAccount.objects.create(
        user_id=8002,
        institute_id="2024BCS802",
        username="contract_user_2",
        email="c2@iiitdmj.ac.in",
        user_type="student",
        status="deactivated",
    )

    RoleAssignment.objects.create(
        role_code="placement_coordinator",
        role_name="Placement Coordinator",
        user_id=8001,
        status="active",
        start_date=date.today(),
        assigned_by=1,
    )

    # 1. get_user_admin_statuses
    statuses = get_user_admin_statuses([8001, 8002, 9999])
    assert 8001 in statuses
    assert statuses[8001]["status"] == "active"
    assert 8002 in statuses
    assert statuses[8002]["status"] == "deactivated"
    assert 9999 not in statuses

    # 2. get_active_role_holders
    holders = get_active_role_holders(["placement_coordinator", "director"])
    assert holders["placement_coordinator"] == [8001]
    assert holders["director"] == []

    # 3. get_user_effective_roles
    effective = get_user_effective_roles([8001, 8002])
    assert len(effective[8001]) == 1
    assert effective[8001][0]["role_code"] == "placement_coordinator"
    assert len(effective[8002]) == 0
