import pytest
from django.core.management import call_command

from modules.elm.contracts import get_leave_balances, get_leave_requests
from modules.elm.models import LeaveBalance, LeaveRequest

pytestmark = pytest.mark.django_db


def test_elm_module_registry_is_visible():
    call_command("seed_modules", stdout=None)
    assert "leave_elm" in [
        row[0] for row in __import__("modules.accesscontrol.models",
                                    fromlist=["Module"]).Module.objects.values_list(
            "code"
        )
    ]


def test_contracts_return_plural_batches():
    LeaveRequest.objects.create(
        user_id=101,
        leave_type="CL",
        start_date="2026-01-10",
        end_date="2026-01-10",
        days_requested=1,
        status="pending",
        reason="Family event",
    )
    LeaveBalance.objects.create(
        user_id=101,
        leave_type="CL",
        year="2026",
        entitled_days=8,
        used_days=1,
        remaining_days=7,
    )

    reqs = get_leave_requests([101], status="pending")
    balances = get_leave_balances([101])

    assert reqs[101][0]["leave_type"] == "CL"
    assert balances[101]["CL"]["remaining_days"] == 7.0
