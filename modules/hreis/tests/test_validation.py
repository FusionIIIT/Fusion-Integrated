from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.hreis.models import EmployeeServiceRecord, HRPolicyVersion, LeaveBalanceEntry
from modules.hreis.services.requests import create_request

pytestmark = pytest.mark.django_db


def actor(user_id=60, permissions=("hreis.request.create",), role="faculty"):
    permissions = frozenset(permissions)
    return SimpleNamespace(
        user_id=user_id,
        active_role=role,
        permissions=permissions,
        has_permission=lambda code: code in permissions,
    )


def setup_user_and_policy(payload=None):
    EmployeeServiceRecord.objects.create(user_id=60, employee_category="faculty")
    HRPolicyVersion.objects.create(
        policy_name="hr",
        version=1,
        effective_from=date.today(),
        payload=payload
        or {
            "approval_routes": {
                "leave": {"faculty": ["HOD (CSE)"]},
                "appraisal": {"faculty": ["HOD (CSE)"]},
                "ltc_advance": {"faculty": ["HOD (CSE)"]},
                "cpda_advance": {"faculty": ["HOD (CSE)"]},
            },
            "eligible_leave_types": {"faculty": ["earned"]},
            "appraisal_windows": {
                "2026": {
                    "opens": date.today().isoformat(),
                    "closes": date.today().isoformat(),
                }
            },
        },
    )


@pytest.mark.parametrize(
    ("request_type", "data", "policy", "message"),
    [
        (
            "leave",
            {"leave_type": "unknown", "duration_days": "1", "justification": "x"},
            None,
            "supported leave types",
        ),
        (
            "leave",
            {"leave_type": "earned", "duration_days": "x", "justification": "x"},
            None,
            "valid leave duration",
        ),
        (
            "leave",
            {"leave_type": "earned", "duration_days": "0", "justification": "x"},
            None,
            "positive leave duration",
        ),
        (
            "leave",
            {"leave_type": "earned", "duration_days": "NaN", "justification": "x"},
            None,
            "positive leave duration",
        ),
        (
            "leave",
            {"leave_type": "earned", "duration_days": "1", "justification": "x"},
            {"approval_routes": {"leave": {"faculty": ["HOD (CSE)"]}}},
            "eligibility is not configured",
        ),
        (
            "leave",
            {"leave_type": "medical", "duration_days": "1", "justification": "x"},
            None,
            "does not allow this leave type",
        ),
        ("appraisal", {"cycle_key": "missing"}, None, "No appraisal window is configured"),
        (
            "appraisal",
            {"cycle_key": "2026"},
            {
                "approval_routes": {"appraisal": {"faculty": ["HOD (CSE)"]}},
                "appraisal_windows": {"2026": {"opens": "bad", "closes": "bad"}},
            },
            "configured appraisal window is invalid",
        ),
        (
            "appraisal",
            {"cycle_key": "2026"},
            {
                "approval_routes": {"appraisal": {"faculty": ["HOD (CSE)"]}},
                "appraisal_windows": {
                    "2026": {
                        "opens": (date.today() - timedelta(days=4)).isoformat(),
                        "closes": (date.today() - timedelta(days=1)).isoformat(),
                    }
                },
            },
            "submission window is closed",
        ),
        ("ltc_advance", {"form_data": {}, "supporting_documents": []}, None, "prescribed LTC form"),
        (
            "ltc_advance",
            {"form_data": {"purpose": "travel"}, "supporting_documents": []},
            None,
            "documents required for LTC",
        ),
        (
            "ltc_advance",
            {"form_data": {"purpose": "travel"}, "supporting_documents": [""]},
            None,
            "documents required for LTC",
        ),
        (
            "cpda_advance",
            {"amount": "x", "purpose": "conference", "supporting_documents": ["receipt"]},
            None,
            "valid CPDA amount",
        ),
        (
            "cpda_advance",
            {"amount": "Infinity", "purpose": "conference", "supporting_documents": ["receipt"]},
            None,
            "CPDA purpose",
        ),
        (
            "cpda_advance",
            {"amount": "10", "purpose": "", "supporting_documents": ["receipt"]},
            None,
            "CPDA purpose",
        ),
        (
            "cpda_advance",
            {"amount": "10", "purpose": "conference", "supporting_documents": []},
            None,
            "documents required for CPDA",
        ),
        (
            "cpda_advance",
            {"amount": "10", "purpose": "conference", "supporting_documents": [3]},
            None,
            "documents required for CPDA",
        ),
    ],
)
def test_invalid_request_inputs_are_actionable(request_type, data, policy, message):
    setup_user_and_policy(policy)
    with pytest.raises(BadRequestError, match=message):
        create_request(
            actor=actor(),
            request_type=request_type,
            data=data,
            idempotency_key="validation-key-60",
        )


def test_missing_employee_record_is_reported():
    HRPolicyVersion.objects.create(
        policy_name="hr", version=1, effective_from=date.today(), payload={}
    )
    with pytest.raises(BadRequestError, match="service record is missing"):
        create_request(
            actor=actor(),
            request_type="leave",
            data={},
            idempotency_key="missing-record-60",
        )


def test_unknown_approval_designation_fails_closed():
    setup_user_and_policy(
        {
            "approval_routes": {"leave": {"faculty": ["Not A Designation"]}},
            "eligible_leave_types": {"faculty": ["earned"]},
        }
    )
    LeaveBalanceEntry.objects.create(
        user_id=60,
        leave_type="earned",
        delta_days="2",
        reason="Opening balance",
        actor_user_id=99,
    )
    with pytest.raises(BadRequestError, match="not present in the approved HR role list"):
        create_request(
            actor=actor(),
            request_type="leave",
            data={"leave_type": "earned", "duration_days": "1", "justification": "x"},
            idempotency_key="bad-route-60",
        )


def test_request_create_permission_and_key_are_required():
    with pytest.raises(PermissionDeniedError):
        create_request(
            actor=actor(permissions=()), request_type="leave", data={}, idempotency_key="valid-key"
        )
    with pytest.raises(BadRequestError, match="Idempotency-Key"):
        create_request(actor=actor(), request_type="leave", data={}, idempotency_key="short")


def test_unsupported_request_type_and_invalid_data_are_rejected():
    setup_user_and_policy()
    with pytest.raises(BadRequestError, match="supported HR request type"):
        create_request(
            actor=actor(), request_type="unsupported", data={}, idempotency_key="unknown-type-60"
        )
    with pytest.raises(BadRequestError, match="must be an object"):
        create_request(actor=actor(), request_type="leave", data=[], idempotency_key="bad-data-60")


def test_leave_balance_insufficient_and_missing_route_are_reported():
    setup_user_and_policy()
    with pytest.raises(BadRequestError, match="balance is insufficient"):
        create_request(
            actor=actor(),
            request_type="leave",
            data={"leave_type": "earned", "duration_days": "1", "justification": "x"},
            idempotency_key="insufficient-60",
        )


def test_missing_route_is_reported():
    setup_user_and_policy({"eligible_leave_types": {"faculty": ["earned"]}})
    LeaveBalanceEntry.objects.create(
        user_id=60,
        leave_type="earned",
        delta_days="2",
        reason="Opening balance",
        actor_user_id=99,
    )
    with pytest.raises(BadRequestError, match="No approval route is configured"):
        create_request(
            actor=actor(),
            request_type="leave",
            data={"leave_type": "earned", "duration_days": "1", "justification": "x"},
            idempotency_key="missing-route-60",
        )


def test_duplicate_appraisal_cycle_is_reported():
    setup_user_and_policy()
    args = {
        "actor": actor(),
        "request_type": "appraisal",
        "data": {"cycle_key": "2026"},
    }
    create_request(**args, idempotency_key="appraisal-first-60")
    with pytest.raises(ConflictError, match="already exists"):
        create_request(**args, idempotency_key="appraisal-second-60")
