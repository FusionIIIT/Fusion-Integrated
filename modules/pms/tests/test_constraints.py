"""Invariants that must hold even if the service layer is bypassed: the database enforces them."""
from datetime import date
from decimal import Decimal

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.utils import timezone

from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    AppendOnlyError,
    Application,
    Assessment,
    AttorneyAssignment,
    AuditEntry,
    Budget,
    DirectorProfile,
    Document,
    DocumentVersion,
    Filing,
    Inventor,
    MaintenanceCycle,
    PmsPolicy,
    ReviewCycle,
)

pytestmark = pytest.mark.django_db


def _app(**kw):
    defaults = {"applicant_user_id": 1, "status": sm.SUBMITTED, "reference": "",
                "title": "T"}
    defaults.update(kw)
    if defaults["status"] != sm.DRAFT and not defaults["reference"]:
        defaults["reference"] = f"PMS-2026-{Application.objects.count() + 1:05d}"
    return Application.objects.create(**defaults)


def _refused(make):
    with pytest.raises(IntegrityError), transaction.atomic():
        make()


# PMS-AFR-044
def test_a_submitted_application_needs_a_reference_pms_afr_044():
    _refused(lambda: Application.objects.create(applicant_user_id=1, status=sm.SUBMITTED))


# PMS-AFR-044
def test_references_are_unique_pms_afr_044():
    _app(reference="PMS-2026-00001")
    _refused(lambda: _app(reference="PMS-2026-00001"))


# PMS-AFR-225
def test_unknown_status_refused_pms_afr_225():
    _refused(lambda: _app(status="approved_by_magic"))


def test_granted_needs_grant_details():
    _refused(lambda: _app(status=sm.GRANTED))


# BR-PMS-074
def test_inventor_share_range_br_pms_074():
    app = _app()
    _refused(lambda: Inventor.objects.create(application=app, name="A",
                                             share_percent=Decimal("0")))
    _refused(lambda: Inventor.objects.create(application=app, name="A",
                                             share_percent=Decimal("100.01")))


def test_one_open_review_cycle_per_application():
    app = _app()
    kw = {"application": app, "director_user_id": 5, "assigned_on": date(2026, 1, 1),
          "due_on": date(2026, 1, 22)}
    ReviewCycle.objects.create(cycle_no=1, **kw)
    _refused(lambda: ReviewCycle.objects.create(cycle_no=2, **kw))


# BR-PMS-040
def test_one_live_attorney_assignment_per_application_br_pms_040():
    app = _app(status=sm.APPROVED)
    AttorneyAssignment.objects.create(application=app, attorney_user_id=9,
                                      assigned_by_user_id=2)
    _refused(lambda: AttorneyAssignment.objects.create(application=app, attorney_user_id=10,
                                                       assigned_by_user_id=2))


# BR-PMS-041
def test_exception_assignment_needs_a_reason_br_pms_041():
    app = _app(status=sm.APPROVED)
    _refused(lambda: AttorneyAssignment.objects.create(
        application=app, attorney_user_id=9, assigned_by_user_id=2, is_exception=True))


def _budget(app, status=sm.PROPOSED, total="300"):
    return Budget.objects.create(application=app, proposed_by_user_id=9, filing_fee=100,
                                 attorney_fee=100, admin_cost=100, total=Decimal(total),
                                 status=status)


# BR-PMS-048 BR-PMS-049 BR-PMS-050
def test_budget_total_is_the_sum_br_pms_048_049_050():
    _refused(lambda: _budget(_app(status=sm.ATTORNEY_ASSIGNED), total="301"))


def test_one_open_and_one_approved_budget_per_application():
    app = _app(status=sm.ATTORNEY_ASSIGNED)
    _budget(app)
    _refused(lambda: _budget(app, status=sm.ESCALATED))
    _budget(app, status=sm.BUDGET_APPROVED)
    _refused(lambda: _budget(app, status=sm.EXTERNAL_APPROVED))


# BR-PMS-046
def test_final_assessment_needs_a_recommendation_br_pms_046():
    _refused(lambda: Assessment.objects.create(application=_app(), attorney_user_id=9,
                                               status="final", finalized_at=timezone.now()))


# BR-PMS-056
def test_international_filing_needs_justification_br_pms_056():
    app = _app(status=sm.FILED)
    _refused(lambda: Filing.objects.create(
        application=app, jurisdiction="EP", office_name="EPO", external_filing_id="EP1",
        filing_date=date(2026, 1, 1), confirmation_reference="c", format_validation="x",
        filed_by_user_id=9))


# BR-PMS-142
def test_filing_needs_a_confirmation_br_pms_142():
    _refused(lambda: Filing.objects.create(
        application=_app(status=sm.FILED), jurisdiction="IN", office_name="IPO",
        external_filing_id="IN1", filing_date=date(2026, 1, 1), confirmation_reference="",
        format_validation="x", filed_by_user_id=9))


# BR-PMS-082
def test_one_current_version_and_unique_numbers_br_pms_082():
    doc = Document.objects.create(application=_app(), kind="claims", title="Claims",
                                  sensitivity="restricted", created_by_user_id=1)
    kw = {"original_name": "c.pdf", "size_bytes": 10, "sha256": "x" * 64,
          "scanner": "test", "uploaded_by_user_id": 1}
    DocumentVersion.objects.create(document=doc, number=1, storage_key="a", **kw)
    _refused(lambda: DocumentVersion.objects.create(document=doc, number=1, storage_key="b",
                                                    is_current=False, **kw))
    _refused(lambda: DocumentVersion.objects.create(document=doc, number=2, storage_key="c",
                                                    **kw))


# BR-PMS-015
def test_version_size_must_be_under_50_mb_br_pms_015():
    doc = Document.objects.create(application=_app(), kind="claims", title="Claims",
                                  sensitivity="restricted", created_by_user_id=1)
    _refused(lambda: DocumentVersion.objects.create(
        document=doc, number=1, storage_key="z", original_name="c.pdf",
        size_bytes=50 * 1024 * 1024, sha256="x", scanner="t", uploaded_by_user_id=1))


# PMS-AFR-222
def test_one_active_director_profile_per_person_pms_afr_222():
    DirectorProfile.objects.create(user_id=5, valid_from=timezone.now(), added_by_user_id=2)
    _refused(lambda: DirectorProfile.objects.create(user_id=5, valid_from=timezone.now(),
                                                    added_by_user_id=2))


# BR-PMS-061
def test_one_live_maintenance_cycle_br_pms_061():
    app = _app(status=sm.GRANTED, grant_date=date(2026, 1, 1), patent_number="P1")
    MaintenanceCycle.objects.create(application=app, seq=1, due_on=date(2027, 1, 1),
                                    source="manual")
    _refused(lambda: MaintenanceCycle.objects.create(application=app, seq=2,
                                                     due_on=date(2028, 1, 1),
                                                     source="manual"))


# BR-PMS-122
def test_audit_rows_cannot_be_changed_in_python_br_pms_122():
    entry = AuditEntry.objects.create(action="x")
    with pytest.raises(AppendOnlyError):
        entry.save()
    with pytest.raises(AppendOnlyError):
        entry.delete()


# BR-PMS-122 PMS-AFR-212
def test_audit_rows_cannot_be_changed_in_the_database_br_pms_122():
    entry = AuditEntry.objects.create(action="x")
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditEntry.objects.filter(pk=entry.pk).update(action="y")
    with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as cur:
        cur.execute("DELETE FROM pms_auditentry WHERE id = %s", [entry.pk])
    assert AuditEntry.objects.get(pk=entry.pk).action == "x"


def test_policy_versions_are_never_edited_step_2_8():
    policy = PmsPolicy.objects.create(version=1, effective_from=timezone.now(), payload={},
                                      published_by_user_id=2)
    with pytest.raises(AppendOnlyError):
        policy.save()
