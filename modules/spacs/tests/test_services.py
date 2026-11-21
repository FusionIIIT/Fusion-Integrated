"""Service layer tests for SPACS (Django test DB)."""

from datetime import date, timedelta
import pytest
from django.utils import timezone

from modules.spacs.models import (
    SpacsApplication,
    SpacsCatalogueEntry,
    SpacsDocument,
    SpacsAuditLog,
)
from modules.spacs.services import (
    applications as app_svc,
    audit as audit_svc,
    awards as award_svc,
    catalogue as cat_svc,
    decisions as dec_svc,
    renewals as rnw_svc,
    tasks as task_svc,
    verification as ver_svc,
)
from modules.spacs.domain.errors import AuditProtectionError, EligibilityError


@pytest.mark.django_db
def test_full_scholarship_lifecycle():
    now = timezone.now()
    # 1. Create and publish catalogue entry
    entry = cat_svc.create_catalogue_entry(
        scheme_code="SCH-MERIT-TEST",
        name="Institute Merit Scholarship",
        scheme_type="scholarship",
        min_cpi=7.5,
        max_family_income=600000.0,
        required_documents=["income_cert"],
        application_window_start=now - timedelta(days=5),
        application_window_end=now + timedelta(days=20),
        renewal_allowed=True,
        renewal_window_start=now - timedelta(days=5),
        renewal_window_end=now + timedelta(days=20),
        created_by_user_id=1,
    )
    cat_svc.publish_catalogue_version(
        scheme_code=entry.scheme_code,
        policy_approval_ref="SENATE-2026-RES-45",
        effective_from=date.today(),
        actor_user_id=1,
    )

    # 2. Student starts draft and uploads document
    student_id = 42
    app = app_svc.create_draft_application(
        scheme_code="SCH-MERIT-TEST",
        applicant_user_id=student_id,
        application_data={"applicant_name": "Bob", "account_no": "12345678"},
    )
    app_svc.upload_document(
        application_id=app.application_id,
        acting_user_id=student_id,
        document_type="income_cert",
        file_path="/uploads/docs/income_42.pdf",
    )

    # 3. Student submits application
    submitted_app = app_svc.submit_application(
        application_id=app.application_id,
        acting_user_id=student_id,
        student_cpi=8.2,
        student_family_income=450000.0,
    )
    assert submitted_app.state == "submitted"

    # 4. Assistant opens and requests correction
    asst_id = 10
    asst_roles = ["spacs_assistant"]
    ver_svc.open_verification_task(submitted_app.application_id, asst_id, asst_roles)
    corr_app = ver_svc.request_correction(
        submitted_app.application_id, asst_id, asst_roles, reason="Please update account details"
    )
    assert corr_app.state == "correction_required"

    # 5. Student corrects and resubmits
    app_svc.modify_application_in_correction(
        corr_app.application_id, student_id, {"account_no": "99998888"}
    )
    resub_app = app_svc.resubmit_application(corr_app.application_id, student_id)
    assert resub_app.state == "resubmitted"

    # 6. Assistant verifies
    ver_svc.open_verification_task(resub_app.application_id, asst_id, asst_roles)
    ver_svc.record_verification_findings(
        resub_app.application_id, asst_id, asst_roles, findings="All verified and authentic"
    )
    verified_app = ver_svc.mark_verified(resub_app.application_id, asst_id, asst_roles)
    assert verified_app.state == "verified"

    # 7. Convener approves
    convener_id = 1
    convener_roles = ["spacs_convener"]
    dec_svc.open_convener_decision(verified_app.application_id, convener_id, convener_roles)
    approved_app = dec_svc.approve_application(
        verified_app.application_id, convener_id, convener_roles, reason="Approved on merit"
    )
    assert approved_app.state == "approved"

    # 8. Test renewal
    rnw_app = rnw_svc.initiate_renewal(approved_app.application_id, student_id)
    assert rnw_app.is_renewal is True
    # upload fresh doc
    app_svc.upload_document(rnw_app.application_id, student_id, "income_cert", "/uploads/fresh.pdf")
    sub_rnw = rnw_svc.submit_renewal(rnw_app.application_id, student_id, current_cpi=8.4, current_family_income=460000.0)
    assert sub_rnw.state == "renewal_submitted"


@pytest.mark.django_db
def test_audit_log_immutability():
    log = audit_svc.log_action("test_event", "application", "SPACS-001", 1, {"note": "test"})
    with pytest.raises(AuditProtectionError):
        log.delete()

    with pytest.raises(AuditProtectionError):
        log.actor_user_id = 999
        log.save()
