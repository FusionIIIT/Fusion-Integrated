"""Tests for SPACS services layer."""
from datetime import timedelta
import pytest
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.spacs.models import (
    ApplicationDocument,
    AwardCandidate,
    AwardCycle,
    ScholarshipApplication,
    SchemeCatalogue,
    SchemePolicyVersion,
    SpacsAuditLog,
)
from modules.spacs.services import applications as app_service
from modules.spacs.services import awards as award_service
from modules.spacs.services import catalogue as cat_service
from modules.spacs.services import documents as doc_service
from modules.spacs.services import tasks as task_service

pytestmark = pytest.mark.django_db


class FakePrincipal:
    def __init__(self, user_id=1, roles=("student",), permissions=()):
        self.user_id = user_id
        self.roles = roles
        self.permissions = frozenset(permissions)
        self.modules = ("spacs",)

    def has_permission(self, code: str) -> bool:
        return code in self.permissions


@pytest.fixture
def student():
    return FakePrincipal(
        user_id=1001,
        roles=("student",),
        permissions=(
            "spacs.catalogue.view",
            "spacs.application.view_self",
            "spacs.application.create",
            "spacs.application.update",
            "spacs.application.delete",
            "spacs.award.view",
        ),
    )


@pytest.fixture
def assistant():
    return FakePrincipal(
        user_id=2001,
        roles=("spacs_assistant",),
        permissions=(
            "spacs.catalogue.view",
            "spacs.application.view",
            "spacs.application.review",
            "spacs.award.view",
            "spacs.export.view",
        ),
    )


@pytest.fixture
def convener():
    return FakePrincipal(
        user_id=3001,
        roles=("spacs_convener",),
        permissions=(
            "spacs.catalogue.view",
            "spacs.catalogue.manage",
            "spacs.application.view",
            "spacs.application.approve",
            "spacs.award.manage",
            "spacs.award.review",
            "spacs.award.approve",
            "spacs.award.publish",
            "spacs.award.view",
            "spacs.export.view",
            "spacs.audit.view",
        ),
    )


@pytest.fixture
def committee():
    return FakePrincipal(
        user_id=4001,
        roles=("award_committee",),
        permissions=(
            "spacs.catalogue.view",
            "spacs.award.review",
            "spacs.award.view",
        ),
    )


@pytest.fixture
def published_scheme(convener):
    now = timezone.now()
    scheme = cat_service.create_catalogue_entry(
        code="mcm-scheme",
        name="Merit-cum-Means",
        scheme_type="scholarship",
        description="MCM Scheme",
        actor=convener,
    )
    version = cat_service.create_policy_version(
        scheme_id=scheme.id,
        title="MCM Policy v1",
        eligibility_criteria={"min_cpi": 6.5, "max_parental_income": 600000},
        required_documents=[{"type": "income_cert", "name": "Income Certificate", "required": True}],
        is_renewable=True,
        renewal_rules={"min_cpi": 6.5, "max_years": 4},
        policy_approval_reference="Senate Res 12.3",
        policy_approved_by="Senate",
        effective_from=now.date() - timedelta(days=10),
        effective_to=now.date() + timedelta(days=100),
        application_window_start=now - timedelta(days=5),
        application_window_end=now + timedelta(days=30),
        renewal_window_start=now - timedelta(days=5),
        renewal_window_end=now + timedelta(days=30),
        actor=convener,
    )
    cat_service.publish_policy_version(version_id=version.id, actor=convener)
    scheme.refresh_from_db()
    return scheme


# --- Catalogue Service Tests ---

def test_catalogue_creation_and_publication(convener):
    scheme = cat_service.create_catalogue_entry(
        code="test-award",
        name="Test Award",
        scheme_type="award",
        actor=convener,
    )
    assert scheme.status == "draft"

    # Version without approval reference cannot be published (BR-SPACS-015)
    version = cat_service.create_policy_version(
        scheme_id=scheme.id,
        title="Award Policy v1",
        actor=convener,
    )
    with pytest.raises(ConflictError) as exc:
        cat_service.publish_policy_version(version_id=version.id, actor=convener)
    assert "approved policy reference" in str(exc.value)

    # Add approval and publish
    version.policy_approval_reference = "BOG Order 10"
    version.effective_from = timezone.now().date()
    version.save()

    published = cat_service.publish_policy_version(version_id=version.id, actor=convener)
    assert published.status == "published"
    scheme.refresh_from_db()
    assert scheme.status == "published"


def test_catalogue_retirement(convener, published_scheme):
    retired = cat_service.retire_catalogue_entry(
        scheme_id=published_scheme.id,
        reason="Scheme superseded by new institute policy",
        actor=convener,
    )
    assert retired.status == "retired"
    assert retired.retired_reason != ""


# --- Scholarship Application Service Tests ---

def test_application_lifecycle(student, assistant, convener, published_scheme):
    # 1. Create draft
    app = app_service.create_draft_application(
        scheme_id=published_scheme.id,
        academic_cycle="2026-27",
        application_data={"cpi": 7.5, "parental_income": 400000},
        actor=student,
    )
    assert app.status == "draft"

    # 2. Attach required document
    doc_service.attach_document(
        application_id=app.id,
        student_user_id=student.user_id,
        doc_type="income_cert",
        title="Income Certificate 2026",
        file_url="https://drive.google.com/test-doc",
        actor=student,
    )

    # 3. Submit application
    submitted = app_service.submit_application(
        application_id=app.id,
        actor=student,
    )
    assert submitted.status == "submitted"
    assert submitted.application_number.startswith("SPACS-")

    # 4. Prevent duplicate active application (BR-SPACS-002)
    with pytest.raises(ConflictError) as exc:
        app2 = app_service.create_draft_application(
            scheme_id=published_scheme.id,
            academic_cycle="2026-27",
            actor=student,
        )
        doc_service.attach_document(
            application_id=app2.id,
            student_user_id=student.user_id,
            doc_type="income_cert",
            title="Income Cert",
            file_url="https://doc",
            actor=student,
        )
        app_service.submit_application(application_id=app2.id, actor=student)
    assert "already have an active" in str(exc.value)

    # 5. Assistant starts verification & requests correction (UC-SPACS-002)
    app_service.verify_application(
        application_id=submitted.id,
        action_type="start",
        actor=assistant,
    )
    corrected_app = app_service.verify_application(
        application_id=submitted.id,
        action_type="request_correction",
        reason="Please attach latest financial year certificate",
        actor=assistant,
    )
    assert corrected_app.status == "correction_required"

    # 6. Student modifies and resubmits (UC-SPACS-003, BR-SPACS-011)
    resubmitted = app_service.modify_application(
        application_id=corrected_app.id,
        updated_data={"cpi": 7.8},
        resubmit=True,
        actor=student,
    )
    assert resubmitted.status == "resubmitted"

    # 7. Assistant verifies application (UC-SPACS-002)
    verified = app_service.verify_application(
        application_id=resubmitted.id,
        action_type="verify",
        findings={"income_verified": True, "academic_verified": True},
        actor=assistant,
    )
    assert verified.status == "verified"

    # 8. Convener approves application (UC-SPACS-006, BR-SPACS-018)
    approved = app_service.decide_application(
        application_id=verified.id,
        decision="approve",
        reason="Sanctioned under category A",
        actor=convener,
    )
    assert approved.status == "approved"
    assert approved.decision_outcome == "approved"

    # Check audit log was populated
    assert SpacsAuditLog.objects.filter(entity_id=str(app.id)).count() > 0


def test_application_withdrawal(student, published_scheme):
    app = app_service.create_draft_application(
        scheme_id=published_scheme.id,
        academic_cycle="2026-27",
        actor=student,
    )
    doc_service.attach_document(
        application_id=app.id,
        student_user_id=student.user_id,
        doc_type="income_cert",
        title="Income",
        file_url="https://doc",
        actor=student,
    )
    submitted = app_service.submit_application(
        application_id=app.id,
        student_facts={"cpi": 8.0, "parental_income": 300000},
        actor=student,
    )

    withdrawn = app_service.withdraw_application(
        application_id=submitted.id,
        reason="No longer required",
        actor=student,
    )
    assert withdrawn.status == "withdrawn"
    assert withdrawn.withdrawal_reason == "No longer required"


def test_scholarship_renewal(student, published_scheme):
    # Create approved application
    app = ScholarshipApplication.objects.create(
        application_number="SPACS-2025-001",
        student_user_id=student.user_id,
        scheme=published_scheme,
        policy_version=published_scheme.versions.first(),
        academic_cycle="2025-26",
        status="approved",
        application_data={"bank_account": "9876543210", "cpi": 8.0},
    )

    renewal = app_service.submit_renewal(
        prior_application_id=app.id,
        academic_cycle="2026-27",
        renewal_data={"cpi": 7.9},
        current_facts={"cpi": 7.9, "active_backlogs": 0},
        actor=student,
    )
    assert renewal.status == "submitted"
    assert renewal.is_renewal is True
    assert renewal.prior_application_id == app.id
    # Prefilled reusable field
    assert renewal.application_data["bank_account"] == "9876543210"


# --- Convocation Award Service Tests ---

def test_award_cycle_flow(convener, committee):
    now = timezone.now()
    award_scheme = cat_service.create_catalogue_entry(
        code="directors-silver",
        name="Director's Silver Medal",
        scheme_type="award",
        actor=convener,
    )
    version = cat_service.create_policy_version(
        scheme_id=award_scheme.id,
        title="Silver Medal Rules",
        candidate_source_method="academic_pool",
        policy_approval_reference="Senate 34",
        effective_from=now.date() - timedelta(days=30),
        effective_to=now.date() + timedelta(days=300),
        actor=convener,
    )
    cat_service.publish_policy_version(version_id=version.id, actor=convener)

    # 1. Create award cycle (BW-SPACS-08)
    cycle = award_service.create_award_cycle(
        scheme_id=award_scheme.id,
        academic_cycle="2025-26",
        convocation_year=2026,
        evaluating_body="Director's Silver Medal Committee",
        actor=convener,
    )
    assert cycle.status == "open"

    # 2. Prepare candidate pool
    prepared = award_service.prepare_candidate_pool(
        award_cycle_id=cycle.id,
        candidates=[
            {"student_user_id": 1001, "cpi": 8.8, "discipline": "CSE"},
            {"student_user_id": 1002, "cpi": 8.5, "discipline": "ECE"},
        ],
        actor=convener,
    )
    assert prepared.status == "pool_prepared"
    assert prepared.candidates.count() == 2

    # 3. Committee records evaluations
    evaluated = award_service.record_committee_evaluations(
        award_cycle_id=cycle.id,
        evaluations=[
            {"student_user_id": 1001, "score": 92.5, "is_shortlisted": True, "recommendation_status": "recommended"},
            {"student_user_id": 1002, "score": 88.0, "is_shortlisted": False, "recommendation_status": "not_recommended"},
        ],
        actor=committee,
    )
    assert evaluated.status == "result_recorded"

    # 4. Cannot publish before institutional approval is recorded (AFR-SPACS-046)
    with pytest.raises(ConflictError) as exc:
        award_service.publish_award_results(award_cycle_id=cycle.id, actor=convener)
    assert "Required approval must be recorded first" in str(exc.value)

    # 5. Record approval (BW-SPACS-09)
    approved_cycle = award_service.record_final_approval(
        award_cycle_id=cycle.id,
        approval_reference="Director Approval Memo 12",
        approving_authority="Director",
        approved_candidate_ids=[1001],
        actor=convener,
    )
    assert approved_cycle.status == "ready_for_publication"

    # 6. Publish results (UC-SPACS-020)
    published = award_service.publish_award_results(award_cycle_id=cycle.id, actor=convener)
    assert published.status == "published"
    assert published.published_at is not None
