"""Model persistence and constraints tests for PMS."""

import decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone

from modules.pms.models import (
    AttorneyPanel,
    DeadlineTracking,
    DirectorAssignment,
    DirectorReview,
    ExternalFilingRecord,
    Inventor,
    InventorAgreement,
    OfficeAction,
    OfficeActionResponse,
    PatentApplication,
    PatentAuditLog,
    PatentBudget,
    PmsConfiguration,
    PostGrantPatent,
)


@pytest.mark.django_db
class TestPatentApplicationModel:
    def test_create_patent_application(self):
        app = PatentApplication.objects.create(
            user_id=1001,
            application_no="PMS-2026-0001",
            title="Solar Cell Nanomaterial",
            abstract="High efficiency perovskite solar cell.",
            description="Detailed embodiment...",
            claims="Claim 1: A solar cell with perovskite...",
            domain="Renewable Energy",
        )
        assert app.id is not None
        assert app.status == "draft"
        assert app.is_confidential is True
        assert str(app) == "PMS-2026-0001 - Solar Cell Nanomaterial"

    def test_duplicate_application_no_raises(self):
        PatentApplication.objects.create(
            user_id=1001,
            application_no="PMS-2026-0002",
            title="Title A",
            abstract="Abstract A",
            description="Desc A",
            claims="Claim A",
            domain="CSE",
        )
        with pytest.raises(IntegrityError):
            PatentApplication.objects.create(
                user_id=1002,
                application_no="PMS-2026-0002",
                title="Title B",
                abstract="Abstract B",
                description="Desc B",
                claims="Claim B",
                domain="ECE",
            )


@pytest.mark.django_db
class TestInventorsAndAgreements:
    def test_create_inventors_and_agreements(self):
        app = PatentApplication.objects.create(
            user_id=1001,
            application_no="PMS-2026-0003",
            title="Neural Chip",
            abstract="Spiking neural network processor.",
            description="Desc...",
            claims="Claim...",
            domain="CSE",
        )
        lead = Inventor.objects.create(
            application=app,
            user_id=1001,
            name="Alice Smith",
            email="alice@institute.ac.in",
            department="CSE",
            is_lead=True,
            share_percentage=decimal.Decimal("60.00"),
        )
        co = Inventor.objects.create(
            application=app,
            user_id=1002,
            name="Bob Jones",
            email="bob@institute.ac.in",
            department="ECE",
            is_lead=False,
            share_percentage=decimal.Decimal("40.00"),
        )
        agreement = InventorAgreement.objects.create(
            application=app,
            agreement_type="patent_assignment",
            status="completed",
            completed_at=timezone.now(),
        )
        assert app.inventors.count() == 2
        assert app.agreements.count() == 1
        assert lead.is_lead is True
        assert co.share_percentage == decimal.Decimal("40.00")
        assert agreement.status == "completed"


@pytest.mark.django_db
class TestReviewsAndAttorneys:
    def test_director_assignment_and_review(self):
        app = PatentApplication.objects.create(
            user_id=1001,
            application_no="PMS-2026-0004",
            title="Bio-sensor",
            abstract="Wearable glucose monitor.",
            description="Desc...",
            claims="Claim...",
            domain="Biotech",
        )
        assignment = DirectorAssignment.objects.create(
            application=app,
            director_user_id=9001,
            assigned_by_user_id=9999,
            due_at=timezone.now() + timezone.timedelta(days=15),
            status="assigned",
        )
        review = DirectorReview.objects.create(
            application=app,
            director_user_id=9001,
            decision="approve",
            justification="Novel electrochemical sensor architecture demonstrating high sensitivity.",
        )
        assert assignment.status == "assigned"
        assert review.decision == "approve"
        assert app.director_reviews.count() == 1

    def test_attorney_panel_and_budget(self):
        panel = AttorneyPanel.objects.create(
            user_id=8001,
            name="John Doe",
            firm_name="Doe & Partners",
            email="john@doepatents.com",
            specialization="Biotech & Chemistry",
        )
        assert panel.is_active is True

        app = PatentApplication.objects.create(
            user_id=1001,
            application_no="PMS-2026-0005",
            title="Catalyst",
            abstract="Nano catalyst.",
            description="Desc...",
            claims="Claim...",
            domain="Chemistry",
        )
        budget = PatentBudget.objects.create(
            application=app,
            filing_fees=decimal.Decimal("10000.00"),
            attorney_fees=decimal.Decimal("25000.00"),
            administrative_costs=decimal.Decimal("5000.00"),
            total_cost=decimal.Decimal("40000.00"),
            status="approved",
            director_user_id=9001,
        )
        assert app.budget.total_cost == decimal.Decimal("40000.00")
        assert budget.status == "approved"


@pytest.mark.django_db
class TestFilingsAndOfficeActions:
    def test_external_filing_and_office_actions(self):
        app = PatentApplication.objects.create(
            user_id=1001,
            application_no="PMS-2026-0006",
            title="Quantum Cryptography Key Distribution",
            abstract="QKD protocol with entanglement.",
            description="Desc...",
            claims="Claim...",
            domain="Physics",
        )
        ExternalFilingRecord.objects.create(
            application=app,
            jurisdiction="IN",
            filing_number="202611000123",
            filing_date=timezone.now().date(),
            patent_office="Indian Patent Office, New Delhi",
            confirmation_details="Filing receipt CBR-12345",
            recorded_by_user_id=8001,
        )
        oa = OfficeAction.objects.create(
            application=app,
            action_number="FER-01",
            issue_date=timezone.now().date(),
            response_deadline=timezone.now().date() + timezone.timedelta(days=90),
            action_type="first_examination_report",
            description="Objection under section 3(k).",
            recorded_by_user_id=8001,
        )
        resp = OfficeActionResponse.objects.create(
            office_action=oa,
            attorney_user_id=8001,
            draft_text="Clarification of technical effect...",
            requires_applicant_approval=True,
        )
        assert app.filing_record.filing_number == "202611000123"
        assert oa.action_number == "FER-01"
        assert resp.requires_applicant_approval is True


@pytest.mark.django_db
class TestPostGrantAndDeadlines:
    def test_post_grant_and_deadlines(self):
        app = PatentApplication.objects.create(
            user_id=1001,
            application_no="PMS-2026-0007",
            title="Graphene Battery",
            abstract="Fast charging graphene anode.",
            description="Desc...",
            claims="Claim...",
            domain="Energy",
        )
        pg = PostGrantPatent.objects.create(
            application=app,
            patent_number="IN456789",
            grant_date=timezone.now().date(),
            expiry_date=timezone.now().date() + timezone.timedelta(days=7300),
        )
        dl = DeadlineTracking.objects.create(
            application=app,
            deadline_type="maintenance",
            due_date=timezone.now() + timezone.timedelta(days=365),
        )
        cfg = PmsConfiguration.objects.create(
            key="BUDGET_ESCALATION_THRESHOLD",
            value="150000.00",
            description="Threshold above which budget requires executive escalation",
        )
        audit = PatentAuditLog.objects.create(
            application=app,
            user_id=1001,
            actor_role="applicant",
            action_type="create_application",
            new_state="draft",
        )
        assert pg.patent_number == "IN456789"
        assert dl.deadline_type == "maintenance"
        assert cfg.key == "BUDGET_ESCALATION_THRESHOLD"
        assert audit.action_type == "create_application"
