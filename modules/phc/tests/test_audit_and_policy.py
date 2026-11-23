"""Append-only records (PHC-BR-09), frozen claims (PHC-BR-14) and the window policy (PHC-BR-06)."""
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError
from modules.phc import registry
from modules.phc.models import AuditRecord, ReimbursementClaim, ReimbursementPolicy
from modules.phc.services import reimbursements
from modules.phc.tests.factories import EMPLOYEE_ID, visit_for

pytestmark = pytest.mark.django_db


def _claim():
    visit = visit_for(EMPLOYEE_ID)
    return ReimbursementClaim.objects.create(
        user_id=EMPLOYEE_ID, prescription=visit.prescriptions.get(),
        expense_date=timezone.localdate(), amount="100.00", submitted_at=timezone.now())


# CFR-PHC-012, AFR-PHC-037, PHC-BR-09
def test_audit_rows_refuse_update_and_delete_in_python_and_sql():
    row = AuditRecord.objects.create(actor_user_id=1, resource_type="x", resource_id=1,
                                     action="create")
    row.action = "tampered"
    with pytest.raises(ValueError):
        row.save()
    with pytest.raises(ValueError):
        row.delete()
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditRecord.objects.filter(pk=row.pk).update(action="tampered")
    with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as cur:
        cur.execute("DELETE FROM phc_audit_record WHERE id = %s", [row.pk])
    assert AuditRecord.objects.get(pk=row.pk).action == "create"


# AFR-PHC-038
def test_submitted_claim_cannot_be_edited_or_deleted_afr_phc_038():
    claim = _claim()
    claim.amount = "999.00"
    with pytest.raises(ValueError):
        claim.save()
    with pytest.raises(ValueError):
        claim.delete()
    with pytest.raises(DatabaseError), transaction.atomic():
        ReimbursementClaim.objects.filter(pk=claim.pk).update(amount="999.00")
    ReimbursementClaim.objects.filter(pk=claim.pk).update(status="pending_sanction")
    stored = ReimbursementClaim.objects.get(pk=claim.pk)
    assert (str(stored.amount), stored.status) == ("100.00", "pending_sanction")


# PHC-BR-06
def test_latest_effective_policy_applies_and_versions_are_never_edited_phc_br_06():
    today = timezone.localdate()
    reimbursements.configure_policy(window_days=30, includes_last_day=True,
                                    effective_from=today - timedelta(days=10))
    reimbursements.configure_policy(window_days=60, includes_last_day=False,
                                    effective_from=today)
    reimbursements.configure_policy(window_days=90, includes_last_day=True,
                                    effective_from=today + timedelta(days=5))
    assert reimbursements.active_policy(today).window_days == 60
    with pytest.raises(ConflictError):
        reimbursements.configure_policy(window_days=10, includes_last_day=True,
                                        effective_from=today)
    with pytest.raises(DomainError):
        reimbursements.configure_policy(window_days=0, includes_last_day=True,
                                        effective_from=today + timedelta(days=9))
    row = ReimbursementPolicy.objects.get(window_days=60)
    row.window_days = 1
    with pytest.raises(ValueError):
        row.save()


def test_readiness_names_the_missing_window_then_clears():
    assert registry.readiness() and "PHC-BR-06" in registry.readiness()[0]
    out = StringIO()
    with pytest.raises(CommandError):
        call_command("phc_readiness", stdout=out)
    assert "phc_configure_window" in out.getvalue()
    call_command("phc_configure_window", "--days", "30", "--includes-last-day", "yes",
                 stdout=StringIO())
    assert registry.readiness() == []
    out = StringIO()
    call_command("phc_readiness", stdout=out)
    assert "ready" in out.getvalue()


def test_configure_command_refuses_a_duplicate_version():
    call_command("phc_configure_window", "--days", "30", "--includes-last-day", "no",
                 stdout=StringIO())
    with pytest.raises(CommandError):
        call_command("phc_configure_window", "--days", "15", "--includes-last-day", "no",
                     stdout=StringIO())
