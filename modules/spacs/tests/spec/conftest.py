"""Common fixtures for Assignment #8 specification-driven tests."""
from datetime import timedelta
import pytest
from django.utils import timezone

from modules.spacs.models import SchemeCatalogue, SchemePolicyVersion


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
def student2():
    return FakePrincipal(
        user_id=1002,
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
            "spacs.award.view",
            "spacs.award.manage",
            "spacs.award.approve",
            "spacs.award.publish",
            "spacs.audit.view",
            "spacs.export.view",
        ),
    )


@pytest.fixture
def committee_member():
    return FakePrincipal(
        user_id=4001,
        roles=("award_committee_member",),
        permissions=(
            "spacs.award.view",
            "spacs.award.review",
        ),
    )


@pytest.fixture
def scheme_mcm(db):
    return SchemeCatalogue.objects.create(
        code="MCM_A8",
        name="Merit-cum-Means Scholarship A8",
        scheme_type="scholarship",
        status="published",
    )


@pytest.fixture
def policy_mcm(db, scheme_mcm):
    now = timezone.now()
    return SchemePolicyVersion.objects.create(
        scheme=scheme_mcm,
        version_number=1,
        title="MCM Policy v1",
        description="MCM standard rules",
        eligibility_criteria={
            "min_cpi": 6.5,
            "max_parental_income": 600000.0,
            "max_active_backlogs": 0,
        },
        required_documents=[
            {"type": "income_certificate", "title": "Income Certificate", "required": True},
            {"type": "grade_card", "title": "Grade Card", "required": True},
        ],
        candidate_source_method="application",
        is_renewable=True,
        renewal_rules={
            "min_cpi": 6.5,
            "max_active_backlogs": 0,
            "max_consecutive_renewals": 3,
            "prefill_fields": ["parental_income"],
        },
        policy_approval_reference="BOG/2026/RES-44",
        policy_approved_by="Senate Academic Committee",
        effective_from=now.date(),
        application_window_start=now - timedelta(days=5),
        application_window_end=now + timedelta(days=25),
        renewal_window_start=now - timedelta(days=5),
        renewal_window_end=now + timedelta(days=25),
        sla_verification_days=7,
        sla_decision_days=14,
        status="published",
    )


@pytest.fixture
def award_scheme(db):
    return SchemeCatalogue.objects.create(
        code="DGM_A8",
        name="Directors Gold Medal A8",
        scheme_type="convocation_award",
        status="published",
    )


@pytest.fixture
def award_policy(db, award_scheme):
    now = timezone.now()
    return SchemePolicyVersion.objects.create(
        scheme=award_scheme,
        version_number=1,
        title="DGM Policy v1",
        eligibility_criteria={"min_cpi": 8.5},
        candidate_source_method="nomination",
        is_renewable=False,
        policy_approval_reference="SENATE/2026/AWARDS-01",
        policy_approved_by="Senate",
        effective_from=now.date(),
        status="published",
    )
