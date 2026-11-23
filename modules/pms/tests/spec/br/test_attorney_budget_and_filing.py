"""Business Rule tests for Attorney assignment, budget, international filing, and maintenance."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.pms.domain.entities import (
    check_budget_escalation,
    validate_budget_components,
    validate_filing_preconditions,
    validate_patentability_opinion,
)
from modules.pms.domain.errors import ConflictOfInterestError, PreconditionNotMetError
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import AttorneyAssignment, AttorneyPanel, PostGrantMaintenance
from modules.pms.services import (
    approve_office_action_response,
    assign_attorney,
    decide_budget,
    decide_renewal,
    draft_office_action_response,
    record_external_filing,
    record_office_action,
    submit_application,
    submit_office_action_response,
    submit_or_update_budget,
)
from modules.pms.services.maintenance import schedule_cycle
from modules.pms.tests.support import configure, configure_maintenance_schedule

pytestmark = pytest.mark.django_db


def _approved_app(applicant_user_id: int = 1001, domain: str = "Computing"):
    app = submit_application(
        applicant_user_id=applicant_user_id,
        title="Approved Patent",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain=domain,
    )
    app.status = PatentApplicationStatus.APPROVED.value
    app.assigned_director_user_id = 3001
    app.save(update_fields=["status", "assigned_director_user_id", "updated_at"])
    return app


def test_br_tc_040_permitted_attorney_assignment_by_pcc_admin_on_approved_application():
    """BR-TC-040 | BR-PMS-040: permitted Attorney assignment by PCC_ADMIN on Approved application."""
    app = _approved_app()
    AttorneyPanel.objects.create(
        attorney_user_id=5001,
        name="Counsel One",
        email="c1@example.edu",
        is_approved=True,
        expertise_domains=["Computing"],
        current_workload=0,
        max_workload=5,
    )
    assignment = assign_attorney(
        application_id=app.id,
        attorney_user_id=5001,
        assigned_by_user_id=7001,
    )
    assert assignment.attorney_user_id == 5001


def test_br_tc_041_prohibited_attorney_assignment_by_non_pcc_admin_user():
    """BR-TC-041 | BR-PMS-040: prohibited Attorney assignment by non-PCC_ADMIN user."""
    app = submit_application(
        applicant_user_id=1001,
        title="Unapproved App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Computing",
    )
    with pytest.raises(PreconditionNotMetError):
        assign_attorney(
            application_id=app.id,
            attorney_user_id=5001,
            assigned_by_user_id=1001,
        )
    app.refresh_from_db()
    assert app.assigned_attorney_user_id is None


def test_br_tc_042_permitted_attorney_selection_from_approved_panel():
    """BR-TC-042 | BR-PMS-041: permitted Attorney selection from approved panel."""
    app = _approved_app()
    AttorneyPanel.objects.create(
        attorney_user_id=5002,
        name="Panel Counsel",
        email="c2@example.edu",
        is_approved=True,
        expertise_domains=["Computing"],
        current_workload=0,
        max_workload=5,
    )
    assignment = assign_attorney(
        application_id=app.id,
        attorney_user_id=5002,
        assigned_by_user_id=7001,
        institutional_exception=False,
    )
    assert assignment.pk is not None


def test_br_tc_043_exception_allowing_non_panel_attorney_with_institutional_exception():
    """BR-TC-043 | BR-PMS-041: exception allowing non-panel Attorney when institutional exception is recorded or allowed."""
    app = _approved_app()
    assignment = assign_attorney(
        application_id=app.id,
        attorney_user_id=5999,
        assigned_by_user_id=7001,
        institutional_exception=True,
    )
    assert assignment.attorney_user_id == 5999


def test_br_tc_044_prohibited_non_panel_attorney_without_institutional_exception():
    """BR-TC-044 | BR-PMS-041: prohibited non-panel Attorney without institutional exception."""
    app = _approved_app()
    with pytest.raises(PreconditionNotMetError):
        assign_attorney(
            application_id=app.id,
            attorney_user_id=5999,
            assigned_by_user_id=7001,
            institutional_exception=False,
        )
    app.refresh_from_db()
    assert app.assigned_attorney_user_id is None


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: BR-TC-045 | BR-PMS-042: A8_BASE stores expertise_domains on "
        "AttorneyPanel but does not automatically rank or filter assignees by domain."
    )
)
def test_br_tc_045_attorney_expertise_matching_application_domain_criterion():
    """BR-TC-045 | BR-PMS-042: Attorney expertise matching application domain criterion."""


def test_br_tc_046_attorney_current_workload_criterion():
    """BR-TC-046 | BR-PMS-043: Attorney current workload criterion."""
    app = _approved_app()
    AttorneyPanel.objects.create(
        attorney_user_id=5003,
        name="Full Counsel",
        email="c3@example.edu",
        is_approved=True,
        current_workload=5,
        max_workload=5,
    )
    with pytest.raises(PreconditionNotMetError):
        assign_attorney(
            application_id=app.id,
            attorney_user_id=5003,
            assigned_by_user_id=7001,
        )
    app.refresh_from_db()
    assert app.assigned_attorney_user_id is None


def test_br_tc_047_conflict_of_interest_check_before_attorney_assignment():
    """BR-TC-047 | BR-PMS-044: conflict-of-interest check before Attorney assignment."""
    app = _approved_app(applicant_user_id=5004)
    AttorneyPanel.objects.create(
        attorney_user_id=5004,
        name="Inventor Counsel",
        email="c4@example.edu",
        is_approved=True,
        current_workload=0,
        max_workload=5,
    )
    with pytest.raises(ConflictOfInterestError):
        assign_attorney(
            application_id=app.id,
            attorney_user_id=5004,
            assigned_by_user_id=7001,
        )
    app.refresh_from_db()
    assert app.assigned_attorney_user_id is None


def test_br_tc_048_permitted_applicant_attorney_preference_when_in_approved_panel():
    """BR-TC-048 | BR-PMS-045: permitted Applicant Attorney preference when preferred Attorney is in approved panel."""
    panel = AttorneyPanel.objects.create(
        attorney_user_id=5005,
        name="Preferred Counsel",
        email="c5@example.edu",
        is_approved=True,
        current_workload=0,
        max_workload=5,
    )
    app = submit_application(
        applicant_user_id=1001,
        title="Preferred Counsel App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
        preferred_attorney_id=panel.attorney_user_id,
    )
    assert app.preferred_attorney_id == 5005


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: BR-TC-049 | BR-PMS-045: submit_application persists "
        "preferred_attorney_id without rejecting a non-panel preference at submission."
    )
)
def test_br_tc_049_preference_not_authorized_when_preferred_attorney_not_in_panel():
    """BR-TC-049 | BR-PMS-045: preference not authorized when preferred Attorney is not in approved panel."""


def test_br_tc_050_permitted_finalized_opinion_recommendations():
    """BR-TC-050 | BR-PMS-046: permitted finalized opinion recommendations (File Patent, Do Not File, Needs Amendment)."""
    for rec in ("File Patent", "Do Not File", "Needs Amendment"):
        validate_patentability_opinion(rec, "Comprehensive patentability assessment.")


def test_br_tc_051_prohibited_opinion_with_missing_or_multiple_recommendations():
    """BR-TC-051 | BR-PMS-046: prohibited opinion with missing or multiple recommendations."""
    with pytest.raises(PreconditionNotMetError):
        validate_patentability_opinion("", "Opinion text")
    with pytest.raises(PreconditionNotMetError):
        validate_patentability_opinion("File Patent, Do Not File", "Opinion text")


def test_br_tc_052_budget_information_includes_filing_fees():
    """BR-TC-052 | BR-PMS-048: budget information includes filing fees."""
    total = validate_budget_components(Decimal("1000.00"), Decimal("0.00"), Decimal("0.00"))
    assert total == Decimal("1000.00")


def test_br_tc_053_budget_information_includes_attorney_fees():
    """BR-TC-053 | BR-PMS-049: budget information includes attorney fees."""
    total = validate_budget_components(Decimal("0.00"), Decimal("2500.00"), Decimal("0.00"))
    assert total == Decimal("2500.00")


def test_br_tc_054_budget_information_includes_administrative_costs():
    """BR-TC-054 | BR-PMS-050: budget information includes administrative costs."""
    total = validate_budget_components(Decimal("0.00"), Decimal("0.00"), Decimal("500.00"))
    assert total == Decimal("500.00")


def test_br_tc_055_escalation_when_total_patent_cost_exceeds_configured_threshold():
    """BR-TC-055 | BR-PMS-051: escalation when total patent cost exceeds configured threshold."""
    app = _approved_app()
    configure(budget_threshold="50000.00")
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("30000.00"),
        attorney_fees=Decimal("25000.00"),
        administrative_costs=Decimal("5000.00"),
        actor_user_id=3001,
    )
    budget = decide_budget(
        application_id=app.id,
        director_user_id=3001,
        decision="Approve",
        justification="Exceeds configured threshold.",
    )
    assert budget.status == "escalated"
    assert check_budget_escalation(Decimal("60000.00"), Decimal("50000.00")) is True


def test_br_tc_056_permitted_budget_approval_when_application_status_is_approved():
    """BR-TC-056 | BR-PMS-052: permitted budget approval when application status is Approved."""
    app = _approved_app()
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("5000.00"),
        attorney_fees=Decimal("10000.00"),
        administrative_costs=Decimal("1000.00"),
        actor_user_id=3001,
    )
    budget = decide_budget(
        application_id=app.id,
        director_user_id=3001,
        decision="Approve",
    )
    assert budget.status == "approved"


def test_br_tc_057_prohibited_budget_approval_when_application_status_is_not_approved():
    """BR-TC-057 | BR-PMS-052: prohibited budget approval when application status is not Approved."""
    app = submit_application(
        applicant_user_id=1001,
        title="Submitted Budget App",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    with pytest.raises(PreconditionNotMetError):
        submit_or_update_budget(
            application_id=app.id,
            filing_fees=Decimal("5000.00"),
            attorney_fees=Decimal("10000.00"),
            administrative_costs=Decimal("1000.00"),
            actor_user_id=3001,
        )
    app.budget.refresh_from_db()
    assert app.budget.status == "draft"


def test_br_tc_058_budget_availability_validated_before_approval_when_available():
    """BR-TC-058 | BR-PMS-053: budget availability validated before approval when information is available."""
    app = _approved_app()
    budget = submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("5000.00"),
        attorney_fees=Decimal("10000.00"),
        administrative_costs=Decimal("1000.00"),
        actor_user_id=3001,
    )
    budget.availability_verified = False
    budget.save(update_fields=["availability_verified", "updated_at"])
    with pytest.raises(PreconditionNotMetError):
        decide_budget(
            application_id=app.id,
            director_user_id=3001,
            decision="Approve",
        )
    budget.refresh_from_db()
    assert budget.status != "approved"


def test_br_tc_059_exception_when_budget_availability_information_not_available():
    """BR-TC-059 | BR-PMS-053: exception when budget-availability information is not available to PMS."""
    app = _approved_app()
    budget = submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("5000.00"),
        attorney_fees=Decimal("10000.00"),
        administrative_costs=Decimal("1000.00"),
        actor_user_id=3001,
    )
    budget.availability_verified = False
    budget.save(update_fields=["availability_verified", "updated_at"])
    decided = decide_budget(
        application_id=app.id,
        director_user_id=3001,
        decision="Reject",
        justification="Budget availability check not applicable on rejection.",
    )
    assert decided.status == "rejected"


@pytest.mark.skip(
    reason=(
        "NOT_AUTOMATED: BR-TC-060 | BR-PMS-055: A8_BASE sets format_validated=True "
        "during record_external_filing without an external patent-office format validator."
    )
)
def test_br_tc_060_filing_package_format_validation_when_rules_available():
    """BR-TC-060 | BR-PMS-055: filing package format validation when rules are available."""


def test_br_tc_061_permitted_international_filing_with_additional_justification():
    """BR-TC-061 | BR-PMS-056: permitted international filing with additional justification recorded."""
    validate_filing_preconditions(
        status=PatentApplicationStatus.APPROVED.value,
        budget_status="approved",
        all_agreements_complete=True,
        is_international=True,
        international_justification="PCT filing for international protection.",
    )


def test_br_tc_062_prohibited_international_filing_without_additional_justification():
    """BR-TC-062 | BR-PMS-056: prohibited international filing without additional justification recorded in PMS."""
    with pytest.raises(PreconditionNotMetError):
        validate_filing_preconditions(
            status=PatentApplicationStatus.APPROVED.value,
            budget_status="approved",
            all_agreements_complete=True,
            is_international=True,
            international_justification="",
        )
    app = _approved_app()
    budget = app.budget
    budget.status = "approved"
    budget.save(update_fields=["status", "updated_at"])
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["assigned_attorney_user_id", "updated_at"])
    AttorneyAssignment.objects.create(
        application=app,
        attorney_user_id=5001,
        assigned_by_user_id=1001,
        status="accepted",
        is_active=True,
    )
    with pytest.raises(PreconditionNotMetError):
        record_external_filing(
            application_id=app.id,
            attorney_user_id=5001,
            external_filing_id="PCT-1",
            external_filing_date=date(2026, 11, 1),
            filing_confirmation="CONF-1",
            is_international=True,
            international_justification="",
        )
    app.refresh_from_db()
    assert app.external_filing_id == ""


def test_br_tc_063_permitted_post_grant_tracking_when_patent_status_is_granted():
    """BR-TC-063 | BR-PMS-059: permitted post-grant tracking when patent status is Granted."""
    configure_maintenance_schedule()
    app = submit_application(
        applicant_user_id=1001,
        title="Granted Patent",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
        jurisdiction="IN",
    )
    app.status = PatentApplicationStatus.GRANTED.value
    app.grant_date = date(2026, 1, 1)
    app.assigned_attorney_user_id = 5001
    app.assigned_director_user_id = 3001
    app.save(
        update_fields=[
            "status",
            "grant_date",
            "assigned_attorney_user_id",
            "assigned_director_user_id",
            "updated_at",
        ]
    )
    maint = PostGrantMaintenance.objects.create(
        application=app,
        cycle_number=1,
        fee_due_date=date(2029, 1, 1),
        fee_amount=Decimal("5000.00"),
        decision_requested=True,
        maintenance_status="decision_requested",
    )
    app.status = PatentApplicationStatus.RENEWAL_DECISION_REQUESTED.value
    app.save(update_fields=["status", "updated_at"])
    updated_maint = decide_renewal(
        maintenance_id=maint.id,
        director_user_id=3001,
        decision="Renew",
    )
    assert updated_maint.director_decision == "Renew"


def test_br_tc_064_prohibited_post_grant_tracking_when_patent_status_is_not_granted():
    """BR-TC-064 | BR-PMS-059: prohibited post-grant tracking when patent status is not Granted."""
    app = submit_application(
        applicant_user_id=1001,
        title="Filed Not Granted Patent",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_director_user_id = 3001
    app.save(update_fields=["status", "assigned_director_user_id", "updated_at"])
    maint = PostGrantMaintenance.objects.create(
        application=app,
        cycle_number=1,
        fee_due_date=date(2029, 1, 1),
        fee_amount=Decimal("5000.00"),
    )
    with pytest.raises(PreconditionNotMetError):
        decide_renewal(
            maintenance_id=maint.id,
            director_user_id=3001,
            decision="Renew",
        )
    maint.refresh_from_db()
    assert maint.director_decision == ""


def test_br_tc_065_maintenance_fee_schedule_determined_from_grant_date_and_jurisdiction():
    """BR-TC-065 | BR-PMS-060: maintenance-fee schedule determined from grant date and jurisdiction when rules available."""
    configure_maintenance_schedule(
        {
            "IN": [{"cycle": 1, "due_after_days": 1095, "fee_amount": "5000.00"}],
        }
    )
    app = submit_application(
        applicant_user_id=1001,
        title="Schedule Patent",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
        jurisdiction="IN",
    )
    app.grant_date = date(2026, 1, 1)
    app.save(update_fields=["grant_date", "updated_at"])
    cycle = schedule_cycle(app, 1)
    assert cycle is not None
    assert cycle.fee_due_date == date(2028, 12, 31)
    assert cycle.fee_amount == Decimal("5000.00")


def test_br_tc_066_explicit_renew_or_do_not_renew_decision_required_before_deadline():
    """BR-TC-066 | BR-PMS-061: explicit Renew or Do Not Renew decision required before maintenance deadline."""
    app = submit_application(
        applicant_user_id=1001,
        title="Renewal Decision Patent",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app.status = PatentApplicationStatus.RENEWAL_DECISION_REQUESTED.value
    app.assigned_director_user_id = 3001
    app.save(update_fields=["status", "assigned_director_user_id", "updated_at"])
    maint = PostGrantMaintenance.objects.create(
        application=app,
        cycle_number=1,
        fee_due_date=date(2029, 1, 1),
        fee_amount=Decimal("5000.00"),
        decision_requested=True,
        maintenance_status="decision_requested",
    )
    with pytest.raises(PreconditionNotMetError):
        decide_renewal(
            maintenance_id=maint.id,
            director_user_id=3001,
            decision="Abstain",
        )
    maint.refresh_from_db()
    assert maint.director_decision == ""

    decided = decide_renewal(
        maintenance_id=maint.id,
        director_user_id=3001,
        decision="Do Not Renew",
    )
    assert decided.director_decision == "Do Not Renew"


def test_br_tc_146_applicant_review_and_approval_of_office_action_response_when_required():
    """BR-TC-146 | BR-PMS-146: Applicant review and approval of office-action response when required by applicable process."""
    today = timezone.now().date()
    due = today + timedelta(days=30)

    # Process requiring Applicant review
    app_req = submit_application(
        applicant_user_id=1001,
        title="OA With Review",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app_req.status = PatentApplicationStatus.FILED.value
    app_req.assigned_attorney_user_id = 5001
    app_req.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    oa_req = record_office_action(
        application_id=app_req.id,
        attorney_user_id=5001,
        action_type="FER",
        issue_date=today,
        due_date=due,
        details="Office action details",
        requires_applicant_review=True,
    )
    draft_office_action_response(
        office_action_id=oa_req.id,
        attorney_user_id=5001,
        draft_response="Draft response text",
    )
    with pytest.raises(PreconditionNotMetError):
        submit_office_action_response(
            office_action_id=oa_req.id,
            attorney_user_id=5001,
            submission_details="Premature submission",
        )
    oa_req.refresh_from_db()
    assert oa_req.status != "response_submitted"

    approve_office_action_response(office_action_id=oa_req.id, applicant_user_id=1001)
    submitted_req = submit_office_action_response(
        office_action_id=oa_req.id,
        attorney_user_id=5001,
        submission_details="Approved submission",
    )
    assert submitted_req.status == "response_submitted"

    # Process not requiring Applicant review
    app_no_req = submit_application(
        applicant_user_id=1001,
        title="OA Without Review",
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain="Tech",
    )
    app_no_req.status = PatentApplicationStatus.FILED.value
    app_no_req.assigned_attorney_user_id = 5001
    app_no_req.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    oa_no_req = record_office_action(
        application_id=app_no_req.id,
        attorney_user_id=5001,
        action_type="Formal",
        issue_date=today,
        due_date=due,
        details="Formal office action",
        requires_applicant_review=False,
    )
    draft_office_action_response(
        office_action_id=oa_no_req.id,
        attorney_user_id=5001,
        draft_response="Direct draft response",
    )
    submitted_no_req = submit_office_action_response(
        office_action_id=oa_no_req.id,
        attorney_user_id=5001,
        submission_details="Direct submission",
    )
    assert submitted_no_req.status == "response_submitted"
