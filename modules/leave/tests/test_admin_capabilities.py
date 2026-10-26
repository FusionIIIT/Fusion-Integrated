from datetime import date

import pytest
from django.core.exceptions import ValidationError

from modules.leave.domain import rules
from modules.leave.models import (
    HolidayCalendar,
    LeaveAccount,
    LeaveHierarchyConfig,
    LeavePolicyConfig,
    LeaveRequest,
)
from modules.leave.services.leave_services import (
    effective_holiday_dates,
    maintain_leave_record,
    publish_holiday_calendar,
    save_policy_config,
    stage_holiday_calendar,
    submit_leave_request,
    synchronize_offline_sanctioned_leave,
)

pytestmark = pytest.mark.django_db


def test_hierarchy_route_overrides_client_supplied_authority_ids():
    LeaveHierarchyConfig.objects.create(
        department="CSE", applicant_role="staff", category="EL",
        unit_head_id="trusted-hod", establishment_user_id="trusted-estt",
        sanctioning_authority_id="trusted-dean",
    )
    request = submit_leave_request(
        applicant_id="employee-1", applicant_role="staff", category="EL",
        start_date=date(2026, 4, 6), end_date=date(2026, 4, 6), purpose="routing",
        unit_head_id="attacker", sanctioning_authority_id="attacker",
        department="CSE",
    )
    assert request.unit_head_id == "trusted-hod"
    assert request.establishment_user_id == "trusted-estt"
    assert request.sanctioning_authority_id == "trusted-dean"


def test_missing_hierarchy_route_fails_closed():
    with pytest.raises(ValidationError, match="No current hierarchy route"):
        submit_leave_request(
            applicant_id="employee-1", applicant_role="staff", category="CL",
            start_date=date(2026, 4, 6), end_date=date(2026, 4, 6), purpose="no route",
            department="CSE",
        )


def test_calendar_replacement_does_not_take_effect_until_published():
    old_day = date(2026, 1, 1)
    new_day = date(2026, 1, 2)
    HolidayCalendar.objects.create(date=old_day, title="Old", is_published=True)
    release = stage_holiday_calendar(
        "next year", "admin-1", [{"date": new_day, "title": "New", "is_restricted_holiday": True}]
    )
    assert effective_holiday_dates() == {old_day}

    publish_holiday_calendar(release.pk)

    assert effective_holiday_dates() == {new_day}
    assert release.entries.get().is_restricted_holiday is True


def test_policy_configuration_updates_current_values():
    saved = save_policy_config("CL", {"annual_entitlement": 11.0, "allows_half_day": True})
    assert saved.annual_entitlement == 11.0
    assert saved.allows_half_day is True
    assert LeavePolicyConfig.objects.get(category="CL").annual_entitlement == 11.0


def test_offline_sync_records_approved_history_updates_balance_and_blocks_duplicates():
    account = LeaveAccount.objects.create(
        user_id="employee-1", employee_type="staff", category="CL", year=2026, balance=8.0
    )
    req = synchronize_offline_sanctioned_leave(
        admin_id="leave-admin", applicant_id="employee-1", employee_type="staff",
        category="CL", start_date=date(2026, 4, 6), end_date=date(2026, 4, 7),
        reference_evidence="paper-order-42", unavailable_reason="ELM outage",
    )
    assert req.status == rules.ST_APPROVED
    assert req.is_offline_sync is True
    assert req.offline_sanction_reference == "paper-order-42"
    assert req.chargeable_days == 2
    assert req.audit_logs.get().action == "SYNC_OFFLINE_RECORD"
    account.refresh_from_db()
    assert account.balance == 6

    with pytest.raises(ValidationError, match="already been synchronized"):
        synchronize_offline_sanctioned_leave(
            admin_id="leave-admin", applicant_id="employee-1", employee_type="staff",
            category="CL", start_date=date(2026, 4, 6), end_date=date(2026, 4, 7),
            reference_evidence="paper-order-42", unavailable_reason="ELM outage",
        )


def test_offline_sync_requires_evidence_context_and_sufficient_balance():
    with pytest.raises(ValidationError, match="evidence"):
        synchronize_offline_sanctioned_leave(
            admin_id="leave-admin", applicant_id="employee-1", employee_type="staff",
            category="CL", start_date=date(2026, 4, 6), end_date=date(2026, 4, 6),
            reference_evidence="", unavailable_reason="ELM outage",
        )
    LeaveAccount.objects.create(
        user_id="employee-1", employee_type="staff", category="EL", year=2026, balance=0,
    )
    with pytest.raises(ValidationError, match="exceeds the available"):
        synchronize_offline_sanctioned_leave(
            admin_id="leave-admin", applicant_id="employee-1", employee_type="staff",
            category="EL", start_date=date(2026, 4, 6), end_date=date(2026, 4, 7),
            reference_evidence="paper-order-43", unavailable_reason="ELM outage",
        )


def test_record_maintenance_cannot_change_sanction_status():
    request = LeaveRequest.objects.create(
        applicant_id="employee-1", applicant_role="staff", category="CL",
        start_date=date(2026, 4, 6), end_date=date(2026, 4, 6), purpose="old",
        status=rules.ST_APPROVED,
    )
    corrected = maintain_leave_record(request.pk, "admin-1", {"purpose": "corrected"}, "typo")
    assert corrected.purpose == "corrected"
    assert corrected.status == rules.ST_APPROVED
    assert corrected.audit_logs.get().action == "ADMIN_RECORD_CORRECTION"
    with pytest.raises(ValidationError, match="permitted descriptive"):
        maintain_leave_record(request.pk, "admin-1", {"status": rules.ST_REJECTED}, "change")


def test_current_policy_values_govern_leave_counting_and_substitute_requirement():
    LeaveHierarchyConfig.objects.create(
        department="CSE", applicant_role="staff", category="CL", unit_head_id="hod-1"
    )
    LeavePolicyConfig.objects.create(
        category="CL", annual_entitlement=12, is_continuous_count=True,
        requires_substitute_default=True,
    )
    with pytest.raises(ValidationError, match="substitute is required"):
        submit_leave_request(
            applicant_id="policy-employee", applicant_role="staff", category="CL",
            start_date=date(2026, 4, 10), end_date=date(2026, 4, 13), purpose="policy check",
            department="CSE",
        )

    request = submit_leave_request(
        applicant_id="policy-employee", applicant_role="staff", category="CL",
        start_date=date(2026, 4, 10), end_date=date(2026, 4, 13), purpose="policy check",
        substitute_id="sub-1", department="CSE",
    )
    assert request.chargeable_days == 4
    assert request.status == rules.ST_AWAITING_SUBSTITUTE
