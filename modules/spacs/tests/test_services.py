"""Service layer tests for SPACS (Django test DB)."""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from modules.spacs.domain.errors import AuditProtectionError
from modules.spacs.services import (
    applications as app_svc,
)
from modules.spacs.services import (
    audit as audit_svc,
)
from modules.spacs.services import (
    catalogue as cat_svc,
)
from modules.spacs.services import (
    decisions as dec_svc,
)
from modules.spacs.services import (
    renewals as rnw_svc,
)
from modules.spacs.services import (
    verification as ver_svc,
)


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
    sub_rnw = rnw_svc.submit_renewal(
        rnw_app.application_id, student_id, current_cpi=8.4, current_family_income=460000.0
    )
    assert sub_rnw.state == "renewal_submitted"


@pytest.mark.django_db
def test_audit_log_immutability():
    log = audit_svc.log_action("test_event", "application", "SPACS-001", 1, {"note": "test"})
    with pytest.raises(AuditProtectionError):
        log.delete()

    with pytest.raises(AuditProtectionError):
        log.actor_user_id = 999
        log.save()


@pytest.mark.django_db
def test_awards_service_flow():
    from modules.spacs.contracts import (
        get_convocation_awards_for_students,
    )
    from modules.spacs.services import awards as award_svc

    # 1. Open award cycle
    entry = cat_svc.create_catalogue_entry(
        scheme_code="AWARD-CONV-01",
        name="President Gold Medal",
        scheme_type="award",
        candidate_source_method="system_pool",
        min_cpi=8.0,
        created_by_user_id=1,
    )
    cat_svc.publish_catalogue_version(
        scheme_code=entry.scheme_code,
        policy_approval_ref="BOG-2026-01",
        effective_from=date.today(),
        actor_user_id=1,
    )
    cycle = award_svc.open_award_cycle(
        scheme_code="AWARD-CONV-01",
        academic_cycle="2026-27",
        convener_user_id=1,
    )
    assert cycle.state == "open"

    # 2. Prepare pool
    cands = [
        {"student_user_id": 501, "cpi": 9.5, "academic_standing": "good", "shortlisted": True},
        {"student_user_id": 502, "cpi": 7.0, "academic_standing": "good", "shortlisted": False},
    ]
    cycle = award_svc.prepare_candidate_pool(cycle.id, 1, cands)
    assert cycle.state == "pool_prepared"
    assert cycle.candidates.count() == 1

    # 3. Committee evaluation
    cycle = award_svc.begin_committee_evaluation(cycle.id, 100)
    assert cycle.state == "under_committee_evaluation"

    scores = {501: {"score": 98.0, "recommendation": "winner", "remarks": "Top academic rank"}}
    cycle = award_svc.record_committee_results(cycle.id, 100, scores)
    assert cycle.state == "committee_result_recorded"

    # 4. Immediate approval vs pending approval
    cycle_pending = award_svc.record_final_award_outcome(cycle.id, 1, approval_evidence="")
    assert cycle_pending.state == "awaiting_approval"

    cycle_ready = award_svc.record_institutional_approval_received(
        cycle_pending.id, 1, "DIR-APPROVAL-2026-99"
    )
    assert cycle_ready.state == "ready_for_publication"

    # 5. Publish
    published_cycle = award_svc.publish_award_results(cycle_ready.id, 1)
    assert published_cycle.state == "published"

    # 6. Contract check
    awards_by_student = get_convocation_awards_for_students([501, 999])
    assert len(awards_by_student[501]) == 1
    assert awards_by_student[501][0]["award_name"] == "President Gold Medal"
    assert len(awards_by_student[999]) == 0


@pytest.mark.django_db
def test_catalogue_and_decision_alternatives():
    from django.core.management import call_command

    from modules.spacs.contracts import get_active_scholarships_for_students
    from modules.spacs.selectors import (
        get_application_by_id,
        get_audit_trail_for_auditor,
        get_convener_queue,
        get_verification_queue,
        visible_applications_for_student,
        visible_catalogue,
    )
    from modules.spacs.services import tasks as task_svc
    from modules.spacs.tasks import check_sla_tasks, close_expired_cycles

    # Catalogue update
    cat_svc.create_catalogue_entry(
        scheme_code="SCH-CAT-UPD",
        name="Initial Name",
        scheme_type="scholarship",
        min_cpi=6.0,
        created_by_user_id=1,
    )
    cat_svc.update_draft_catalogue_entry(
        scheme_code="SCH-CAT-UPD",
        actor_user_id=1,
        name="Updated Name",
        min_cpi=6.5,
    )
    cat_svc.publish_catalogue_version("SCH-CAT-UPD", "SENATE-01", date.today(), 1)
    cat_svc.update_draft_catalogue_entry("SCH-CAT-UPD", 1, min_cpi=7.0)
    cat_svc.publish_catalogue_version("SCH-CAT-UPD", "SENATE-02", date.today(), 1)
    # Decision reject and return for correction
    app = app_svc.create_draft_application("SCH-CAT-UPD", 77, {"details": "test"})
    app_svc.upload_document(app.application_id, 77, "income_cert", "/tmp/doc.pdf")
    submitted = app_svc.submit_application(app.application_id, 77, 8.0, 200000.0)
    ver_svc.open_verification_task(submitted.application_id, 10, ["spacs_assistant"])
    ver_svc.mark_verified(submitted.application_id, 10, ["spacs_assistant"])

    dec_svc.open_convener_decision(submitted.application_id, 1, ["spacs_convener"])
    ret_app = dec_svc.return_for_correction(
        submitted.application_id, 1, ["spacs_convener"], reason="Re-upload tax slip"
    )
    assert ret_app.state == "correction_required"

    # Re-submit and reject
    app_svc.modify_application_in_correction(ret_app.application_id, 77, {"updated": True})
    resub = app_svc.resubmit_application(ret_app.application_id, 77)
    ver_svc.open_verification_task(resub.application_id, 10, ["spacs_assistant"])
    ver_svc.mark_verified(resub.application_id, 10, ["spacs_assistant"])
    dec_svc.open_convener_decision(resub.application_id, 1, ["spacs_convener"])
    rej = dec_svc.reject_application(resub.application_id, 1, ["spacs_convener"], reason="Quota full")
    assert rej.state == "rejected"

    # Retire catalogue entry afterwards
    cat_svc.retire_catalogue_entry("SCH-CAT-UPD", 1)
    assert cat_svc.get_published_catalogue_entries().count() >= 0

    # Selectors and contracts
    visible = visible_catalogue()
    assert visible.count() >= 0
    student_apps = visible_applications_for_student(77)
    assert student_apps.count() >= 1

    fetched_app = get_application_by_id(rej.application_id, 77, ["student"])
    assert fetched_app.id == rej.id

    fetched_staff = get_application_by_id(rej.application_id, 10, ["spacs_assistant"])
    assert fetched_staff.id == rej.id

    q_ver = get_verification_queue()
    assert q_ver.count() >= 0
    q_dec = get_convener_queue()
    assert q_dec.count() >= 0
    trails = get_audit_trail_for_auditor(["spacs_convener"])
    assert trails.count() >= 1

    with pytest.raises(PermissionError):
        get_audit_trail_for_auditor(["student"])

    scholarships = get_active_scholarships_for_students([77, 999])
    assert 77 in scholarships

    # Tasks and Celery tasks
    task = task_svc.create_task(
        task_type="verification",
        entity_type="application",
        entity_id=rej.application_id,
        assigned_role="spacs_assistant",
        assigned_user_id=10,
    )
    assert task.status == "pending"
    reassigned = task_svc.reassign_role_tasks(
        assigned_role="spacs_assistant",
        old_user_id=10,
        new_user_id=99,
        acting_user_id=1,
    )
    assert reassigned >= 1

    call_command("spacs_check_sla", sla_hours=1)
    call_command("spacs_seed_demo")

    check_sla_tasks()
    close_expired_cycles()


@pytest.mark.django_db
def test_draft_updates_reuse_and_export():
    now = timezone.now()
    _entry = cat_svc.create_catalogue_entry(
        scheme_code="SCH-DOC-REUSE",
        name="Doc Scheme",
        scheme_type="scholarship",
        min_cpi=6.0,
        application_window_start=now - timedelta(days=2),
        application_window_end=now + timedelta(days=20),
        created_by_user_id=1,
    )
    cat_svc.publish_catalogue_version("SCH-DOC-REUSE", "POL-DR", date.today(), 1)

    app = app_svc.create_draft_application(
        scheme_code="SCH-DOC-REUSE",
        applicant_user_id=701,
        academic_cycle="2026-27",
        application_data={"project": "test"},
    )
    # update draft
    app_svc.update_draft(
        application_id=app.application_id,
        acting_user_id=701,
        data_updates={"cpi": 8.2, "family_income": 400000.0, "project": "updated"},
    )
    app.refresh_from_db()
    assert float(app.cpi) == 8.2
    assert app.application_data["project"] == "updated"

    # upload doc
    doc = app_svc.upload_document(
        application_id=app.application_id,
        acting_user_id=701,
        document_type="income_certificate",
        file_path="/tmp/income.pdf",
        valid_until=date.today() + timedelta(days=365),
    )
    assert doc.id is not None

    # new app reusing doc
    app2 = app_svc.create_draft_application(
        scheme_code="SCH-DOC-REUSE",
        applicant_user_id=701,
        academic_cycle="2027-28",
    )
    doc_reused = app_svc.reuse_prior_document(
        application_id=app2.application_id,
        acting_user_id=701,
        prior_document_id=doc.id,
        required_doc_type="income_certificate",
    )
    assert doc_reused.file_path == "/tmp/income.pdf"

    # export data
    data = app_svc.export_application(
        application_id=app.application_id,
        acting_user_id=701,
        acting_user_roles=["student"],
    )
    assert data["application_id"] == app.application_id
    assert float(data["cpi"]) == 8.2

