"""Business Rule tests for office-action deadlines, withdrawal, and licensing."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.pms.domain.errors import PreconditionNotMetError, WithdrawalNotAllowedError
from modules.pms.domain.state_machine import (
    WITHDRAWAL_ELIGIBLE_STATES,
    PatentApplicationStatus,
)
from modules.pms.models import LicensingRequest
from modules.pms.services import (
    monitor_and_process_deadlines,
    record_office_action,
    record_withdrawal_consent,
    request_office_action_extension,
    review_licensing_request,
    submit_application,
    submit_licensing_request,
    withdraw_application,
)

pytestmark = pytest.mark.django_db


def test_br_tc_067_office_action_response_recorded_within_applicable_deadline():
    """BR-TC-067 | BR-PMS-065: office-action response recorded within applicable deadline."""
    app = submit_application(
        applicant_user_id=1001,
        title="OA Timely App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    today = timezone.now().date()
    oa = record_office_action(
        application_id=app.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=today,
        due_date=today + timedelta(days=30),
        details="Response within window",
        requires_applicant_review=False,
    )
    assert oa.due_date >= today


def test_br_tc_068_exception_when_permitted_extension_applies_for_office_action_response():
    """BR-TC-068 | BR-PMS-065: exception when permitted extension applies for office-action response."""
    app = submit_application(
        applicant_user_id=1001,
        title="OA Extension App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    today = timezone.now().date()
    oa = record_office_action(
        application_id=app.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=today - timedelta(days=40),
        due_date=today - timedelta(days=5),
        details="Initial deadline passed",
        requires_applicant_review=False,
    )
    extended = request_office_action_extension(
        office_action_id=oa.id,
        attorney_user_id=5001,
        extension_months=2,
    )
    assert extended.extension_months == 2
    assert extended.due_date > today


def test_br_tc_069_automated_office_action_response_deadline_tracking():
    """BR-TC-069 | BR-PMS-066: automated office-action response deadline tracking when deadline rules/data available."""
    app = submit_application(
        applicant_user_id=1001,
        title="OA Deadline Tracking App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    now = timezone.now()
    record_office_action(
        application_id=app.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=now.date(),
        due_date=(now + timedelta(days=15)).date(),
        details="Due in 15 days",
        requires_applicant_review=False,
    )
    stats = monitor_and_process_deadlines(now=now)
    assert stats["alerts_sent"] >= 1


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: BR-TC-070 | BR-PMS-066: OfficeAction requires a non-null due_date "
        "in the model schema and has no separate deadline-rule-availability flag."
    )
)
def test_br_tc_070_exception_when_applicable_deadline_data_rules_unavailable():
    """BR-TC-070 | BR-PMS-066: exception when applicable deadline data/rules are unavailable."""


def test_br_tc_071_permitted_withdrawal_before_the_filing_stage():
    """BR-TC-071 | BR-PMS-067: permitted withdrawal when the application is before the filing stage."""
    app = submit_application(
        applicant_user_id=1001,
        title="Pre-Filing App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    withdrawn = withdraw_application(
        application_id=app.id,
        applicant_user_id=1001,
        reason="No longer pursuing filing.",
    )
    assert withdrawn.status == PatentApplicationStatus.WITHDRAWN.value
    assert withdrawn.is_withdrawn is True


def test_br_tc_072_prohibited_withdrawal_at_or_after_the_filing_stage():
    """BR-TC-072 | BR-PMS-067: prohibited withdrawal once the application has reached the filing stage."""
    app = submit_application(
        applicant_user_id=1001,
        title="Filed App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.save(update_fields=["status", "updated_at"])
    with pytest.raises(WithdrawalNotAllowedError):
        withdraw_application(
            application_id=app.id,
            applicant_user_id=1001,
            reason="Late withdrawal attempt.",
        )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.FILED.value
    assert app.is_withdrawn is False


def test_br_tc_073_permitted_withdrawal_when_status_is_withdrawal_eligible():
    """BR-TC-073 | BR-PMS-068: permitted withdrawal when current application status is eligible under PMS rule/configuration."""
    assert PatentApplicationStatus.APPROVED in WITHDRAWAL_ELIGIBLE_STATES
    app = submit_application(
        applicant_user_id=1001,
        title="Approved Pre-Filing App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.APPROVED.value
    app.save(update_fields=["status", "updated_at"])
    withdrawn = withdraw_application(
        application_id=app.id,
        applicant_user_id=1001,
        reason="Withdrawing before filing.",
    )
    assert withdrawn.status == PatentApplicationStatus.WITHDRAWN.value


def test_br_tc_074_prohibited_withdrawal_when_status_is_not_withdrawal_eligible():
    """BR-TC-074 | BR-PMS-068: prohibited withdrawal when current application status is not withdrawal-eligible."""
    app = submit_application(
        applicant_user_id=1001,
        title="Granted App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.GRANTED.value
    app.save(update_fields=["status", "updated_at"])
    with pytest.raises(WithdrawalNotAllowedError):
        withdraw_application(
            application_id=app.id,
            applicant_user_id=1001,
            reason="Cannot withdraw granted patent.",
        )
    app.refresh_from_db()
    assert app.status == PatentApplicationStatus.GRANTED.value
    assert app.is_withdrawn is False


def test_br_tc_075_permitted_withdrawal_request_with_applicant_provided_reason():
    """BR-TC-075 | BR-PMS-069: permitted withdrawal request when an Applicant-provided reason is supplied."""
    app = submit_application(
        applicant_user_id=1001,
        title="Reason Provided App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    withdrawn = withdraw_application(
        application_id=app.id,
        applicant_user_id=1001,
        reason="Strategic pivot.",
    )
    assert withdrawn.withdrawal_reason == "Strategic pivot."


def test_br_tc_076_prohibited_withdrawal_request_without_applicant_provided_reason():
    """BR-TC-076 | BR-PMS-069: prohibited withdrawal request without an Applicant-provided reason."""
    app = submit_application(
        applicant_user_id=1001,
        title="Missing Reason App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    with pytest.raises(WithdrawalNotAllowedError):
        withdraw_application(
            application_id=app.id,
            applicant_user_id=1001,
            reason="   ",
        )
    app.refresh_from_db()
    assert app.is_withdrawn is False
    assert app.status == PatentApplicationStatus.SUBMITTED.value


def test_br_tc_077_co_inventor_consent_recorded_when_required_for_withdrawal():
    """BR-TC-077 | BR-PMS-070: co-inventor consent for withdrawal is recorded when required by the applicable process."""
    app = submit_application(
        applicant_user_id=1001,
        title="Co-Inventor Withdrawal App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
        coinventors_data=[
            {
                "user_id": 2001,
                "name": "Co Inventor",
                "email": "co@example.edu",
                "ownership_percentage": "100.00",
            }
        ],
    )
    coinv = app.coinventors.first()
    assert coinv is not None
    with pytest.raises(WithdrawalNotAllowedError):
        withdraw_application(
            application_id=app.id,
            applicant_user_id=1001,
            reason="Withdrawing with co-inventor.",
        )
    app.refresh_from_db()
    assert app.is_withdrawn is False

    record_withdrawal_consent(coinventor_id=coinv.id, user_id=2001, consent_given=True)
    withdrawn = withdraw_application(
        application_id=app.id,
        applicant_user_id=1001,
        reason="Withdrawing with co-inventor.",
    )
    assert withdrawn.status == PatentApplicationStatus.WITHDRAWN.value


def test_br_tc_095_licensing_or_technology_transfer_request_routing():
    """BR-TC-095 | BR-PMS-088: licensing/technology-transfer requests are routed to the appropriate committee or Director per the institutional process."""
    app = submit_application(
        applicant_user_id=1001,
        title="Licensable Tech",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Biotech",
    )
    app.assigned_director_user_id = 3001
    app.save(update_fields=["assigned_director_user_id", "updated_at"])

    req = submit_licensing_request(
        application_id=app.id,
        applicant_user_id=1001,
        licensee_name="BioCorp",
        request_type="exclusive_license",
        commercial_terms="5% royalty",
    )
    reviewed = review_licensing_request(
        request_id=req.id,
        director_user_id=3001,
        status="under_review",
        negotiation_notes="Routed to Director for review.",
    )
    assert reviewed.status == "under_review"


def test_br_tc_096_confidentiality_controls_on_license_records():
    """BR-TC-096 | BR-PMS-091: confidentiality controls on license records."""
    app = submit_application(
        applicant_user_id=1001,
        title="Confidential License App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Biotech",
    )
    req = submit_licensing_request(
        application_id=app.id,
        applicant_user_id=1001,
        licensee_name="SecretPartner",
        request_type="non_exclusive",
        commercial_terms="Confidential terms",
    )
    stored = LicensingRequest.objects.get(pk=req.id)
    assert stored.is_confidential is True

    with pytest.raises(PreconditionNotMetError):
        review_licensing_request(
            request_id=req.id,
            director_user_id=3001,
            status="invalid_status",
        )
    stored.refresh_from_db()
    assert stored.status == req.status
    assert stored.is_confidential is True
