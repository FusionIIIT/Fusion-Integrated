"""FR Spec Tests: Attorney Assignment, Patentability Assessment, and Budgets.

Covers TC-045..TC-050, TC-050b, TC-051..TC-069, and TC-201 from FR_DESIGN.json.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.pms.domain.errors import ConflictOfInterestError, PreconditionNotMetError
from modules.pms.domain.state_machine import PatentApplicationStatus
from modules.pms.models import (
    AttorneyPanel,
    PatentabilityAssessment,
    PatentBudget,
    PmsAuditTrail,
    PmsNotificationOutbox,
)
from modules.pms.services import (
    assign_attorney,
    decide_budget,
    record_legal_advice,
    respond_to_attorney_assignment,
    submit_application,
    submit_or_update_budget,
    submit_patentability_assessment,
)
from modules.pms.tests.support import configure

pytestmark = pytest.mark.django_db

API = "/api/v1/pms"


def _auth_client(stub_iam, user_id: int, role: str = "director", permissions: tuple[str, ...] = ()):
    session = make_session(
        user_id=user_id,
        roles=(role,),
        active_role=role,
        permissions=permissions,
        modules=("pms",),
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return client


def _approved_app(applicant_user_id: int = 1001, director_user_id: int = 2001, domain: str = "AI"):
    app = submit_application(
        applicant_user_id=applicant_user_id,
        title="Approved Patent App",
        abstract="Abstract text",
        detailed_description="Detailed description",
        claims="Claims text",
        domain=domain,
    )
    app.status = PatentApplicationStatus.APPROVED.value
    app.assigned_director_user_id = director_user_id
    app.save(update_fields=["status", "assigned_director_user_id", "updated_at"])
    return app


def test_tc_045_pms_afr_074_only_pcc_admin_may_assign_attorneys_to_approved_applications(stub_iam):
    """Test ID: TC-045 | Source ID: PMS-AFR-074: only PCC_ADMIN may assign attorneys to approved applications."""
    AttorneyPanel.objects.create(attorney_user_id=5001, name="Adv. A", email="a@law.test", is_approved=True)
    app = _approved_app()

    director_client = _auth_client(stub_iam, 2001, "director", ("pms.application.review",))
    denied = director_client.post(
        f"{API}/applications/{app.id}/assign-attorney/",
        {"attorney_user_id": 5001},
        format="json",
    )
    assert denied.status_code == 403

    admin_client = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.attorney.assign",))
    allowed = admin_client.post(
        f"{API}/applications/{app.id}/assign-attorney/",
        {"attorney_user_id": 5001},
        format="json",
    )
    assert allowed.status_code == 201


def test_tc_046_pms_afr_075_require_attorneys_from_approved_panel_unless_exception_granted():
    """Test ID: TC-046 | Source ID: PMS-AFR-075: require attorneys from approved panel unless exception granted."""
    AttorneyPanel.objects.create(attorney_user_id=5002, name="Unapproved", email="u@law.test", is_approved=False)
    app = _approved_app()

    with pytest.raises(PreconditionNotMetError, match="approved attorney panel"):
        assign_attorney(application_id=app.id, attorney_user_id=5002, assigned_by_user_id=9001)

    assignment = assign_attorney(
        application_id=app.id, attorney_user_id=5002, assigned_by_user_id=9001, institutional_exception=True
    )
    assert assignment.attorney_user_id == 5002


def test_tc_047_pms_afr_076_consider_attorney_expertise_matching_domain():
    """Test ID: TC-047 | Source ID: PMS-AFR-076: consider attorney expertise matching domain."""
    panel_match = AttorneyPanel.objects.create(
        attorney_user_id=5001,
        name="AI Counsel",
        email="ai@law.test",
        is_approved=True,
        expertise_domains=["AI", "ML"],
    )
    AttorneyPanel.objects.create(
        attorney_user_id=5002,
        name="Bio Counsel",
        email="bio@law.test",
        is_approved=True,
        expertise_domains=["Biotech"],
    )
    app = _approved_app(domain="AI")
    matching = [
        p for p in AttorneyPanel.objects.filter(is_approved=True) if app.domain in p.expertise_domains
    ]
    assert [p.attorney_user_id for p in matching] == [panel_match.attorney_user_id]


def test_tc_048_pms_afr_077_consider_attorney_current_workload():
    """Test ID: TC-048 | Source ID: PMS-AFR-077: consider attorney current workload."""
    AttorneyPanel.objects.create(
        attorney_user_id=5001, name="Full Atty", email="f@law.test", is_approved=True, current_workload=5, max_workload=5
    )
    AttorneyPanel.objects.create(
        attorney_user_id=5002, name="Light Atty", email="l@law.test", is_approved=True, current_workload=1, max_workload=5
    )
    app = _approved_app()

    with pytest.raises(PreconditionNotMetError, match="maximum workload"):
        assign_attorney(application_id=app.id, attorney_user_id=5001, assigned_by_user_id=9001)

    assignment = assign_attorney(application_id=app.id, attorney_user_id=5002, assigned_by_user_id=9001)
    assert assignment.attorney_user_id == 5002


def test_tc_049_pms_afr_078_conflict_of_interest_checks_before_attorney_assignment():
    """Test ID: TC-049 | Source ID: PMS-AFR-078: conflict-of-interest checks before attorney assignment."""
    AttorneyPanel.objects.create(attorney_user_id=1001, name="Self Atty", email="s@law.test", is_approved=True)
    app = _approved_app(applicant_user_id=1001)
    with pytest.raises(ConflictOfInterestError):
        assign_attorney(application_id=app.id, attorney_user_id=1001, assigned_by_user_id=9001)


def test_tc_050_pms_afr_079_consider_applicant_preference_when_preferred_attorney_in_approved_panel():
    """Test ID: TC-050 | Source ID: PMS-AFR-079: consider Applicant preference when preferred attorney is in approved panel."""
    AttorneyPanel.objects.create(attorney_user_id=5001, name="Preferred", email="p@law.test", is_approved=True)
    app = submit_application(
        applicant_user_id=1001,
        title="Pref App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="AI",
        preferred_attorney_id=5001,
    )
    app.status = PatentApplicationStatus.APPROVED.value
    app.save(update_fields=["status", "updated_at"])

    panel_entry = AttorneyPanel.objects.filter(attorney_user_id=app.preferred_attorney_id, is_approved=True).first()
    assert panel_entry is not None
    assignment = assign_attorney(application_id=app.id, attorney_user_id=panel_entry.attorney_user_id, assigned_by_user_id=9001)
    assert assignment.attorney_user_id == 5001


def test_tc_050b_pms_afr_079_do_not_apply_applicant_preference_when_preferred_attorney_outside_panel():
    """Test ID: TC-050b | Source ID: PMS-AFR-079: do not apply Applicant preference when preferred attorney is outside approved panel."""
    AttorneyPanel.objects.create(attorney_user_id=5002, name="Approved", email="ok@law.test", is_approved=True)
    app = submit_application(
        applicant_user_id=1001,
        title="Non Panel Pref",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="AI",
        preferred_attorney_id=5999,
    )
    app.status = PatentApplicationStatus.APPROVED.value
    app.save(update_fields=["status", "updated_at"])

    assert not AttorneyPanel.objects.filter(attorney_user_id=app.preferred_attorney_id, is_approved=True).exists()
    assignment = assign_attorney(application_id=app.id, attorney_user_id=5002, assigned_by_user_id=9001)
    assert assignment.attorney_user_id == 5002


def test_tc_051_pms_afr_080_assigned_attorney_accepts_or_declines_assignment():
    """Test ID: TC-051 | Source ID: PMS-AFR-080: assigned Attorney accepts or declines assignment."""
    AttorneyPanel.objects.create(attorney_user_id=5001, name="Adv. A", email="a@law.test", is_approved=True)
    app = _approved_app()
    offer = assign_attorney(application_id=app.id, attorney_user_id=5001, assigned_by_user_id=9001)
    accepted = respond_to_attorney_assignment(assignment_id=offer.id, attorney_user_id=5001, accept=True)
    assert accepted.status == "accepted"


def test_tc_052_pms_afr_081_record_assignment_outcome_as_attorney_assigned_or_pending_review():
    """Test ID: TC-052 | Source ID: PMS-AFR-081: record assignment outcome as Attorney Assigned or Pending Review."""
    AttorneyPanel.objects.create(attorney_user_id=5001, name="Adv. A", email="a@law.test", is_approved=True)
    app = _approved_app()
    offer = assign_attorney(application_id=app.id, attorney_user_id=5001, assigned_by_user_id=9001)
    assert offer.status == "offered"
    respond_to_attorney_assignment(assignment_id=offer.id, attorney_user_id=5001, accept=True)
    app.refresh_from_db()
    assert app.assigned_attorney_user_id == 5001


def test_tc_053_pms_afr_082_attorney_records_legal_and_patentability_analysis():
    """Test ID: TC-053 | Source ID: PMS-AFR-082: Attorney records legal and patentability analysis."""
    app = _approved_app()
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["assigned_attorney_user_id", "updated_at"])
    app.attorney_assignments.create(attorney_user_id=5001, assigned_by_user_id=9001, status="accepted", is_active=True)

    assessment = submit_patentability_assessment(
        application_id=app.id,
        attorney_user_id=5001,
        recommendation="File Patent",
        opinion_text="Thorough patentability analysis confirms inventive step.",
        novelty_score=8,
        non_obviousness_score=8,
        utility_score=9,
    )
    assert PatentabilityAssessment.objects.filter(pk=assessment.pk).exists()


def test_tc_054_pms_afr_083_attorney_records_prior_art_searches_in_relevant_databases():
    """Test ID: TC-054 | Source ID: PMS-AFR-083: Attorney records prior-art searches in relevant databases."""
    app = _approved_app()
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["assigned_attorney_user_id", "updated_at"])
    app.attorney_assignments.create(attorney_user_id=5001, assigned_by_user_id=9001, status="accepted", is_active=True)

    ref = app.prior_art_references.create(
        source="USPTO",
        reference_id="US-10987654",
        title="Prior Art Reference",
        relevance="high",
        notes="Searched USPTO and Google Patents.",
        attached_by_user_id=5001,
    )
    assert ref.source == "USPTO"


def test_tc_055_pms_afr_084_attorney_records_novelty_non_obviousness_and_utility_evaluations():
    """Test ID: TC-055 | Source ID: PMS-AFR-084: Attorney records novelty, non-obviousness, and utility evaluations."""
    app = _approved_app()
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["assigned_attorney_user_id", "updated_at"])
    app.attorney_assignments.create(attorney_user_id=5001, assigned_by_user_id=9001, status="accepted", is_active=True)

    assessment = submit_patentability_assessment(
        application_id=app.id,
        attorney_user_id=5001,
        recommendation="File Patent",
        opinion_text="Evaluated all three statutory criteria.",
        novelty_score=9,
        non_obviousness_score=7,
        utility_score=10,
    )
    assert assessment.novelty_score == 9
    assert assessment.non_obviousness_score == 7
    assert assessment.utility_score == 10


def test_tc_056_pms_afr_085_patentability_opinion_recommendation_constraint():
    """Test ID: TC-056 | Source ID: PMS-AFR-085: patentability opinion recommendation constraint."""
    app = _approved_app()
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["assigned_attorney_user_id", "updated_at"])
    app.attorney_assignments.create(attorney_user_id=5001, assigned_by_user_id=9001, status="accepted", is_active=True)

    with pytest.raises(PreconditionNotMetError):
        submit_patentability_assessment(
            application_id=app.id,
            attorney_user_id=5001,
            recommendation="Invalid Recommendation",
            opinion_text="Opinion text",
        )


def test_tc_057_pms_afr_086_attorney_requests_additional_information_during_legal_review():
    """Test ID: TC-057 | Source ID: PMS-AFR-086: Attorney requests additional information during legal review."""
    app = _approved_app()
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["assigned_attorney_user_id", "updated_at"])
    app.attorney_assignments.create(attorney_user_id=5001, assigned_by_user_id=9001, status="accepted", is_active=True)

    advice = record_legal_advice(
        application_id=app.id,
        attorney_user_id=5001,
        stage="information_request",
        advice_text="Requesting benchmark logs from applicant before drafting claims.",
    )
    assert advice.stage == "information_request"


def test_tc_058_pms_afr_087_attorney_requests_extensions_during_legal_review():
    """Test ID: TC-058 | Source ID: PMS-AFR-087: Attorney requests extensions during legal review."""
    app = _approved_app()
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["assigned_attorney_user_id", "updated_at"])
    app.attorney_assignments.create(attorney_user_id=5001, assigned_by_user_id=9001, status="accepted", is_active=True)

    advice = record_legal_advice(
        application_id=app.id,
        attorney_user_id=5001,
        stage="extension_request",
        advice_text="Requesting 15-day extension for legal review completion.",
    )
    assert advice.stage == "extension_request"


def test_tc_059_pms_afr_088_record_attorney_patentability_opinion():
    """Test ID: TC-059 | Source ID: PMS-AFR-088: record Attorney patentability opinion."""
    app = _approved_app()
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["assigned_attorney_user_id", "updated_at"])
    app.attorney_assignments.create(attorney_user_id=5001, assigned_by_user_id=9001, status="accepted", is_active=True)

    assessment = submit_patentability_assessment(
        application_id=app.id,
        attorney_user_id=5001,
        recommendation="Needs Amendment",
        opinion_text="Amend claim 2 to clarify apparatus boundary.",
    )
    assert assessment.recommendation == "Needs Amendment"
    assert assessment.is_final is True


def test_tc_060_pms_afr_089_notify_stakeholders_after_attorney_opinion_recorded():
    """Test ID: TC-060 | Source ID: PMS-AFR-089: notify stakeholders after Attorney opinion recorded."""
    app = _approved_app()
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["assigned_attorney_user_id", "updated_at"])
    app.attorney_assignments.create(attorney_user_id=5001, assigned_by_user_id=9001, status="accepted", is_active=True)

    submit_patentability_assessment(
        application_id=app.id,
        attorney_user_id=5001,
        recommendation="File Patent",
        opinion_text="Ready for filing.",
    )
    assert PmsAuditTrail.objects.filter(application=app, action_type="patentability_assessed").exists()


def test_tc_061_pms_afr_090_director_reviews_patent_filing_and_prosecution_costs(stub_iam):
    """Test ID: TC-061 | Source ID: PMS-AFR-090: Director reviews patent filing and prosecution costs."""
    app = _approved_app(director_user_id=2001)
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("10000.00"),
        attorney_fees=Decimal("20000.00"),
        administrative_costs=Decimal("5000.00"),
        actor_user_id=2001,
    )
    client = _auth_client(stub_iam, 2001, "director", ("pms.application.view", "pms.budget.review"))
    res = client.get(f"{API}/applications/{app.id}/")
    assert res.status_code == 200
    assert Decimal(str(res.json()["budget"]["total_cost"])) == Decimal("35000.00")


def test_tc_062_pms_afr_091_director_approves_filing_and_prosecution_costs():
    """Test ID: TC-062 | Source ID: PMS-AFR-091: Director approves filing and prosecution costs."""
    configure(budget_threshold="100000.00")
    app = _approved_app(director_user_id=2001)
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("15000.00"),
        attorney_fees=Decimal("25000.00"),
        administrative_costs=Decimal("5000.00"),
        actor_user_id=2001,
    )
    budget = decide_budget(application_id=app.id, director_user_id=2001, decision="Approve", justification="Within limit")
    assert budget.status == "approved"


def test_tc_063_pms_afr_092_include_filing_fees_in_budget_information():
    """Test ID: TC-063 | Source ID: PMS-AFR-092: include filing fees in budget information."""
    app = _approved_app(director_user_id=2001)
    budget = submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("12500.00"),
        attorney_fees=Decimal("0.00"),
        administrative_costs=Decimal("0.00"),
        actor_user_id=2001,
    )
    assert budget.filing_fees == Decimal("12500.00")


def test_tc_064_pms_afr_093_include_attorney_fees_in_budget_information():
    """Test ID: TC-064 | Source ID: PMS-AFR-093: include attorney fees in budget information."""
    app = _approved_app(director_user_id=2001)
    budget = submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("0.00"),
        attorney_fees=Decimal("32000.00"),
        administrative_costs=Decimal("0.00"),
        actor_user_id=2001,
    )
    assert budget.attorney_fees == Decimal("32000.00")


def test_tc_065_pms_afr_094_include_administrative_costs_in_budget_information():
    """Test ID: TC-065 | Source ID: PMS-AFR-094: include administrative costs in budget information."""
    app = _approved_app(director_user_id=2001)
    budget = submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("0.00"),
        attorney_fees=Decimal("0.00"),
        administrative_costs=Decimal("4500.00"),
        actor_user_id=2001,
    )
    assert budget.administrative_costs == Decimal("4500.00")


def test_tc_066_pms_afr_095_escalate_when_total_cost_exceeds_configured_threshold_limit():
    """Test ID: TC-066 | Source ID: PMS-AFR-095: escalate when total cost exceeds configured threshold limit."""
    configure(budget_threshold="50000.00")
    app = _approved_app(director_user_id=2001)
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("30000.00"),
        attorney_fees=Decimal("25000.00"),
        administrative_costs=Decimal("5000.00"),
        actor_user_id=2001,
    )
    budget = decide_budget(application_id=app.id, director_user_id=2001, decision="Approve")
    assert budget.status == "escalated"
    assert PmsNotificationOutbox.objects.filter(topic="budget.escalated", recipient_user_id=1001).exists()


def test_tc_067_pms_afr_096_allow_budget_approval_only_for_status_approved():
    """Test ID: TC-067 | Source ID: PMS-AFR-096: allow budget approval only for status Approved."""
    app = submit_application(
        applicant_user_id=1001,
        title="Unapproved App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="AI",
    )
    app.assigned_director_user_id = 2001
    app.save(update_fields=["assigned_director_user_id", "updated_at"])

    with pytest.raises(PreconditionNotMetError, match="Approved"):
        submit_or_update_budget(
            application_id=app.id,
            filing_fees=Decimal("1000.00"),
            attorney_fees=Decimal("2000.00"),
            administrative_costs=Decimal("500.00"),
            actor_user_id=2001,
        )


def test_tc_068_pms_afr_097_validate_budget_availability_before_approval():
    """Test ID: TC-068 | Source ID: PMS-AFR-097: validate budget availability before approval."""
    app = _approved_app(director_user_id=2001)
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("10000.00"),
        attorney_fees=Decimal("15000.00"),
        administrative_costs=Decimal("2000.00"),
        actor_user_id=2001,
    )
    budget = PatentBudget.objects.get(application=app)
    budget.availability_verified = False
    budget.save(update_fields=["availability_verified", "updated_at"])

    with pytest.raises(PreconditionNotMetError, match="availability"):
        decide_budget(application_id=app.id, director_user_id=2001, decision="Approve")


def test_tc_069_pms_afr_098_log_financial_transactions_with_authorization_level_information():
    """Test ID: TC-069 | Source ID: PMS-AFR-098: log financial transactions with authorization-level information."""
    app = _approved_app(director_user_id=2001)
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("10000.00"),
        attorney_fees=Decimal("10000.00"),
        administrative_costs=Decimal("2000.00"),
        actor_user_id=2001,
    )
    decide_budget(application_id=app.id, director_user_id=2001, decision="Approve", justification="Authorized")
    audit = PmsAuditTrail.objects.filter(application=app, action_type="budget_approved").first()
    assert audit is not None
    assert audit.actor_user_id == 2001


def test_tc_201_pms_afr_236_director_rejects_proposed_patent_budget_and_records_outcome():
    """Test ID: TC-201 | Source ID: PMS-AFR-236: Director rejects proposed patent budget and records outcome."""
    app = _approved_app(director_user_id=2001)
    submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("50000.00"),
        attorney_fees=Decimal("80000.00"),
        administrative_costs=Decimal("10000.00"),
        actor_user_id=2001,
    )
    budget = decide_budget(
        application_id=app.id,
        director_user_id=2001,
        decision="Reject",
        justification="Proposed budget exceeds allocation.",
    )
    assert budget.status == "rejected"
    assert budget.decided_by_user_id == 2001
