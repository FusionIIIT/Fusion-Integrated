"""Tests for the R1-08 design and the two review decisions.

Covers the append-only budget ledger, effective-dated policy, the missed-renewal alert,
and one-time consent tokens for external co-inventors.
"""
from __future__ import annotations

import re
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import ConflictError
from modules.patents.domain import permissions as p
from modules.patents.domain import state_machine as sm
from modules.patents.models import (
    CoInventor,
    CoInventorConsentToken,
    PatentApplication,
    PatentBudgetLedger,
    PatentPolicy,
)
from modules.patents.models.budget import AppendOnlyViolation
from modules.patents.models.policy import PolicyImmutable
from modules.patents.services import applications as app_service
from modules.patents.services import budget as budget_service
from modules.patents.services import consent as consent_service
from modules.patents.services.policy import supersede_policy
from modules.patents.tasks import pms_sweep_deadlines


def applicant(user_id=101):
    return make_principal(
        user_id=user_id, kind="student", roles=("student",), active_role="student",
        modules=("patents",),
        permissions=(p.P_APPLICATION_VIEW_SELF, p.P_APPLICATION_CREATE, p.P_APPLICATION_UPDATE),
    )


def director(user_id=201):
    return make_principal(
        user_id=user_id, kind="faculty", roles=("Director",), active_role="Director",
        modules=("patents",),
        permissions=(p.P_APPLICATION_VIEW, p.P_BUDGET_APPROVE, p.P_BUDGET_VIEW),
    )


def new_application(actor) -> PatentApplication:
    return app_service.create_application(
        actor=actor, title="Titled", abstract="Abs", description="Desc", claims="Claims",
        domain_category="Computer Science", jurisdiction="IN",
    )


# --- Append-only budget ledger -------------------------------------------------------


@pytest.mark.django_db
def test_ledger_rows_cannot_be_updated_or_deleted():
    app = new_application(applicant())
    req = budget_service.record_budget_entry(applicant(), app.id, "FILING", "1000.00", "filing")
    req.status = "APPROVED"
    with pytest.raises(AppendOnlyViolation):
        req.save()
    with pytest.raises(AppendOnlyViolation):
        req.delete()


@pytest.mark.django_db
def test_decision_is_a_new_row_and_cannot_be_decided_twice():
    app = new_application(applicant())
    req = budget_service.record_budget_entry(applicant(), app.id, "FILING", "1000.00", "filing")
    decision = budget_service.decide_budget(director(), req.id, "APPROVE")
    assert decision.id != req.id
    assert decision.entry_kind == "APPROVAL"
    assert decision.replaces_entry_id == req.id
    req.refresh_from_db()
    assert req.status == "PENDING"  # the request row itself is untouched

    with pytest.raises(ConflictError):
        budget_service.decide_budget(director(), req.id, "REJECT")


@pytest.mark.django_db
def test_approved_total_is_derived_and_reversal_reduces_it():
    app = new_application(applicant())
    req = budget_service.record_budget_entry(applicant(), app.id, "FILING", "1500.00", "filing")
    approval = budget_service.decide_budget(director(), req.id, "APPROVE")
    assert budget_service.approved_total(app.id) == Decimal("1500.00")

    reversal = budget_service.reverse_budget_entry(director(), approval.id, notes="entered twice")
    assert reversal.entry_kind == "REVERSAL"
    assert budget_service.approved_total(app.id) == Decimal("0.00")
    assert PatentBudgetLedger.objects.filter(pk=approval.pk, status="APPROVED").exists()

    with pytest.raises(ConflictError):
        budget_service.reverse_budget_entry(director(), approval.id)


@pytest.mark.django_db
def test_over_threshold_escalates_then_higher_authority_decides():
    supersede_policy(
        director_review_days=15, revision_resubmission_days=60,
        cost_escalation_threshold=Decimal("20000.00"), withdrawal_eligible_states=[],
    )
    app = new_application(applicant())
    req = budget_service.record_budget_entry(applicant(), app.id, "FILING", "25000.00", "filing")
    escalated = budget_service.decide_budget(director(), req.id, "APPROVE")
    assert escalated.entry_kind == "ESCALATION"
    assert escalated.status == "ESCALATED"

    final = budget_service.decide_budget(director(), req.id, "APPROVE")
    assert final.entry_kind == "APPROVAL"
    assert final.status == "APPROVED"


# --- Effective-dated policy ----------------------------------------------------------


@pytest.mark.django_db
def test_policy_content_cannot_be_edited_in_place():
    policy = supersede_policy(
        director_review_days=15, revision_resubmission_days=60, withdrawal_eligible_states=[],
    )
    policy.revision_resubmission_days = 90
    with pytest.raises(PolicyImmutable):
        policy.save()
    with pytest.raises(PolicyImmutable):
        policy.delete()


@pytest.mark.django_db
def test_supersede_keeps_history_and_ends_the_old_row():
    old = supersede_policy(
        director_review_days=15, revision_resubmission_days=60, withdrawal_eligible_states=[],
    )
    new = supersede_policy(
        director_review_days=15, revision_resubmission_days=45, withdrawal_eligible_states=[],
    )
    old.refresh_from_db()
    assert old.is_active is False
    assert old.effective_to is not None
    assert old.superseded_by_id == new.id
    assert old.revision_resubmission_days == 60  # content unchanged
    assert PatentPolicy.objects.filter(is_active=True).get().id == new.id


@pytest.mark.django_db
def test_seed_policy_force_supersedes_rather_than_editing():
    call_command("pms_seed_policy")
    first = PatentPolicy.objects.get(is_active=True)
    call_command("pms_seed_policy", "--force", "--threshold", "50000.00")
    first.refresh_from_db()
    assert first.is_active is False
    assert first.superseded_by is not None
    assert PatentPolicy.objects.get(is_active=True).cost_escalation_threshold == Decimal("50000.00")


# --- Missed renewal alert (no automatic status change) -------------------------------


@pytest.mark.django_db
def test_missed_renewal_raises_alert_and_changes_no_status():
    app = new_application(applicant())
    PatentApplication.objects.filter(pk=app.pk).update(
        status=sm.GRANTED, renewal_due_date=timezone.now().date() - timedelta(days=3),
    )
    result = pms_sweep_deadlines()
    assert result["overdue_renewals"] == 1
    app.refresh_from_db()
    assert app.status == sm.GRANTED


@pytest.mark.django_db
def test_recorded_renewal_decision_clears_the_alert():
    app = new_application(applicant())
    PatentApplication.objects.filter(pk=app.pk).update(
        status=sm.GRANTED, renewal_due_date=timezone.now().date() - timedelta(days=3),
        renewal_decided_at=timezone.now(),
    )
    assert pms_sweep_deadlines()["overdue_renewals"] == 0


# --- External co-inventor consent tokens ----------------------------------------------


def _external_co_inventor(app):
    return CoInventor.objects.create(
        application=app, user_id=None, name="Ext Person", email="ext@example.org",
        share_percentage=Decimal("50.00"),
    )


def _token_from_email() -> str:
    body = mail.outbox[-1].body
    match = re.search(r"within 14 days: (\S+)", body)
    assert match, body
    return match.group(1)


@pytest.mark.django_db
def test_consent_token_is_emailed_and_confirms_once():
    app = new_application(applicant())
    ci = _external_co_inventor(app)
    consent_service.issue_consent_token(applicant(), app.id, ci.id)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["ext@example.org"]
    raw = _token_from_email()
    assert CoInventorConsentToken.objects.get(co_inventor=ci).token_hash != raw

    consent_service.confirm_consent_token(raw)
    ci.refresh_from_db()
    assert ci.consent_granted is True
    with pytest.raises(ConflictError):
        consent_service.confirm_consent_token(raw)


@pytest.mark.django_db
def test_expired_consent_token_is_refused():
    app = new_application(applicant())
    ci = _external_co_inventor(app)
    consent_service.issue_consent_token(applicant(), app.id, ci.id)
    raw = _token_from_email()
    CoInventorConsentToken.objects.filter(co_inventor=ci).update(
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    with pytest.raises(ConflictError):
        consent_service.confirm_consent_token(raw)


@pytest.mark.django_db
def test_consent_token_cannot_be_issued_for_institute_account():
    app = new_application(applicant())
    internal = CoInventor.objects.create(
        application=app, user_id=555, name="Staff", email="staff@example.org",
        share_percentage=Decimal("50.00"),
    )
    with pytest.raises(ConflictError):
        consent_service.issue_consent_token(applicant(), app.id, internal.id)
    assert len(mail.outbox) == 0
