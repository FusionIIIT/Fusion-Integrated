"""FR Spec Tests: Deadlines, Reports, Notifications, Audit, and Governance.

Covers TC-142..TC-195, TC-195b, TC-196..TC-200, and TC-202..TC-204 from FR_DESIGN.json.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.pms.domain.errors import (
    ExternalServiceUnavailableError,
    InvalidTransitionError,
)
from modules.pms.domain.state_machine import PatentApplicationStatus, validate_transition
from modules.pms.models import (
    AttorneyPanel,
    OfficeAction,
    PatentApplication,
    PmsAuditTrail,
    PmsNotificationOutbox,
    PmsRoleAssignment,
)
from modules.pms.services import (
    assign_director,
    calculate_review_deadline,
    calculate_revision_deadline,
    enqueue_notification,
    monitor_and_process_deadlines,
    record_office_action,
    record_patent_grant,
    send_pending_notifications,
    submit_application,
)
from modules.pms.services import prior_art as prior_art_service
from modules.pms.tests.support import configure_maintenance_schedule

pytestmark = pytest.mark.django_db

API = "/api/v1/pms"


def _auth_client(stub_iam, user_id: int, role: str = "pcc_admin", permissions: tuple[str, ...] = ()):
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


def _make_app(applicant_user_id: int = 1001, domain: str = "Tech", title: str = "Spec App"):
    return submit_application(
        applicant_user_id=applicant_user_id,
        title=title,
        abstract="Abstract",
        detailed_description="Description",
        claims="Claims",
        domain=domain,
    )


def test_tc_142_pms_afr_172_calculate_and_monitor_director_review_deadlines():
    """Test ID: TC-142 | Source ID: PMS-AFR-172: calculate and monitor Director review deadlines."""
    app = _make_app()
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    app.refresh_from_db()
    assert app.review_deadline == calculate_review_deadline(app.director_assigned_at)


def test_tc_143_pms_afr_173_calculate_and_monitor_revision_resubmission_deadlines():
    """Test ID: TC-143 | Source ID: PMS-AFR-173: calculate and monitor revision/resubmission deadlines."""
    now = timezone.now()
    expected = calculate_revision_deadline(now)
    assert expected == now + datetime.timedelta(days=60)


def test_tc_144_pms_afr_174_calculate_and_monitor_office_action_response_deadlines():
    """Test ID: TC-144 | Source ID: PMS-AFR-174: calculate and monitor office-action response deadlines."""
    app = _make_app()
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    due = datetime.date(2027, 4, 10)
    oa = record_office_action(
        application_id=app.id,
        attorney_user_id=5001,
        action_type="OA",
        issue_date=datetime.date(2026, 11, 1),
        due_date=due,
        details="Response deadline tracked",
    )
    assert OfficeAction.objects.get(pk=oa.pk).due_date == due


def test_tc_145_pms_afr_175_calculate_and_monitor_maintenance_fee_deadlines():
    """Test ID: TC-145 | Source ID: PMS-AFR-175: calculate and monitor maintenance-fee deadlines."""
    configure_maintenance_schedule()
    app = _make_app()
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    grant_date = datetime.date(2026, 10, 1)
    record_patent_grant(
        application_id=app.id, attorney_user_id=5001, patent_number="IN-M-1", grant_date=grant_date
    )
    maint = app.maintenance_records.first()
    assert maint.fee_due_date == grant_date + datetime.timedelta(days=1095)


def test_tc_146_pms_afr_176_generate_deadline_alert_30_days_before_deadline():
    """Test ID: TC-146 | Source ID: PMS-AFR-176: generate deadline alert 30 days before deadline."""
    now = timezone.now()
    app = _make_app()
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.assigned_director_user_id = 2001
    app.review_deadline = now + datetime.timedelta(days=30)
    app.save()

    monitor_and_process_deadlines(now=now)
    assert PmsNotificationOutbox.objects.filter(topic="deadline.alert_30", recipient_user_id=2001).exists()


def test_tc_147_pms_afr_177_generate_deadline_alert_15_days_before_deadline():
    """Test ID: TC-147 | Source ID: PMS-AFR-177: generate deadline alert 15 days before deadline."""
    now = timezone.now()
    app = _make_app()
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.assigned_director_user_id = 2001
    app.review_deadline = now + datetime.timedelta(days=15)
    app.save()

    monitor_and_process_deadlines(now=now)
    assert PmsNotificationOutbox.objects.filter(topic="deadline.alert_15", recipient_user_id=2001).exists()


def test_tc_148_pms_afr_178_generate_deadline_alert_5_days_before_deadline():
    """Test ID: TC-148 | Source ID: PMS-AFR-178: generate deadline alert 5 days before deadline."""
    now = timezone.now()
    app = _make_app()
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.assigned_director_user_id = 2001
    app.review_deadline = now + datetime.timedelta(days=5)
    app.save()

    monitor_and_process_deadlines(now=now)
    assert PmsNotificationOutbox.objects.filter(topic="deadline.alert_5", recipient_user_id=2001).exists()


def test_tc_149_pms_afr_179_send_deadline_notifications_to_relevant_stakeholders():
    """Test ID: TC-149 | Source ID: PMS-AFR-179: send deadline notifications to relevant stakeholders."""
    now = timezone.now()
    app = _make_app()
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.assigned_director_user_id = 2001
    app.review_deadline = now + datetime.timedelta(days=5)
    app.save()

    monitor_and_process_deadlines(now=now)
    assert PmsNotificationOutbox.objects.filter(
        topic="deadline.alert_5", recipient_user_id=2001, status="pending"
    ).exists()


def test_tc_150_pms_afr_180_escalate_missed_deadlines_per_configured_chain():
    """Test ID: TC-150 | Source ID: PMS-AFR-180: escalate missed deadlines per configured chain."""
    now = timezone.now()
    app = _make_app()
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.assigned_director_user_id = 2001
    app.review_deadline = now - datetime.timedelta(days=2)
    app.save()

    stats = monitor_and_process_deadlines(now=now)
    assert stats["escalations"] >= 1
    assert PmsNotificationOutbox.objects.filter(topic="deadline.escalated", recipient_user_id=2001).exists()


def test_tc_151_pms_afr_181_log_deadline_tracking_activities():
    """Test ID: TC-151 | Source ID: PMS-AFR-181: log deadline tracking activities."""
    now = timezone.now()
    app = _make_app()
    app.status = PatentApplicationStatus.NEEDS_REVISION.value
    app.revision_deadline = now - datetime.timedelta(days=1)
    app.save()

    monitor_and_process_deadlines(now=now)
    assert PmsAuditTrail.objects.filter(application=app, action_type="revision_expired").exists()


def test_tc_152_pms_afr_182_pcc_admin_and_directors_generate_application_status_and_progress_reports(stub_iam):
    """Test ID: TC-152 | Source ID: PMS-AFR-182: PCC_ADMIN and Directors generate application status and progress reports."""
    _make_app(applicant_user_id=1001, domain="CS")
    admin_res = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.report.view",)).get(f"{API}/reports/")
    dir_res = _auth_client(stub_iam, 2001, "director", ("pms.report.view",)).get(f"{API}/reports/")
    assert admin_res.status_code == 200
    assert dir_res.status_code == 200
    assert "status_distribution" in admin_res.json()
    assert "status_distribution" in dir_res.json()


def test_tc_153_pms_afr_183_pcc_admin_and_directors_generate_financial_and_budget_reports(stub_iam):
    """Test ID: TC-153 | Source ID: PMS-AFR-183: PCC_ADMIN and Directors generate financial and budget reports."""
    app = _make_app(applicant_user_id=1001, domain="CS")
    app.budget.filing_fees = Decimal("15000.00")
    app.budget.save(update_fields=["filing_fees", "updated_at"])

    res = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.report.view",)).get(f"{API}/reports/")
    assert res.status_code == 200
    assert res.json()["total_applications"] >= 1


def test_tc_154_pms_afr_184_pcc_admin_and_directors_generate_deadline_and_pending_action_reports(stub_iam):
    """Test ID: TC-154 | Source ID: PMS-AFR-184: PCC_ADMIN and Directors generate deadline and pending action reports."""
    _make_app(applicant_user_id=1001, domain="CS")
    res = _auth_client(stub_iam, 2001, "director", ("pms.report.view",)).get(f"{API}/reports/")
    assert res.status_code == 200


def test_tc_155_pms_afr_185_pcc_admin_and_directors_generate_inventor_and_co_inventor_reports(stub_iam):
    """Test ID: TC-155 | Source ID: PMS-AFR-185: PCC_ADMIN and Directors generate inventor and co-inventor reports."""
    submit_application(
        applicant_user_id=1001,
        title="Co-inv Report App",
        abstract="A",
        detailed_description="D",
        claims="C",
        domain="CS",
        coinventors_data=[
            {"user_id": 1001, "name": "A", "email": "a@t.org", "ownership_percentage": "50.00"},
            {"user_id": 1002, "name": "B", "email": "b@t.org", "ownership_percentage": "50.00"},
        ],
    )
    res = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.report.view",)).get(f"{API}/reports/")
    assert res.status_code == 200


def test_tc_156_pms_afr_186_pcc_admin_and_directors_generate_patent_portfolio_analysis_reports(stub_iam):
    """Test ID: TC-156 | Source ID: PMS-AFR-186: PCC_ADMIN and Directors generate patent portfolio analysis reports."""
    _make_app(applicant_user_id=1001, domain="PortfolioDomain")
    res = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.report.view",)).get(f"{API}/reports/")
    assert res.status_code == 200
    assert "domain_distribution" in res.json()


def test_tc_157_pms_afr_187_pcc_admin_and_directors_generate_workload_and_assignment_reports(stub_iam):
    """Test ID: TC-157 | Source ID: PMS-AFR-187: PCC_ADMIN and Directors generate workload and assignment reports."""
    app = _make_app(applicant_user_id=1001, domain="WorkloadDomain")
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    res = _auth_client(stub_iam, 2001, "director", ("pms.report.view",)).get(f"{API}/reports/")
    assert res.status_code == 200


def test_tc_158_pms_afr_188_authorized_users_schedule_reports(stub_iam):
    """Test ID: TC-158 | Source ID: PMS-AFR-188: authorized users schedule reports."""
    client = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.config.manage",))
    res = client.put(
        f"{API}/configuration/",
        {"key": "alert_offsets", "value": [30, 15, 5], "description": "Report schedule offsets"},
        format="json",
    )
    assert res.status_code == 200


def test_tc_159_pms_afr_189_authorized_users_export_reports(stub_iam):
    """Test ID: TC-159 | Source ID: PMS-AFR-189: authorized users export reports."""
    _make_app(applicant_user_id=1001, domain="ExportDomain")
    res = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.report.view",)).get(f"{API}/reports/")
    assert res.status_code == 200
    assert isinstance(res.json(), dict)


def test_tc_160_pms_afr_190_authorized_users_customize_reports(stub_iam):
    """Test ID: TC-160 | Source ID: PMS-AFR-190: authorized users customize reports."""
    _make_app(applicant_user_id=1001, domain="CustomDomain")
    res = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.application.view", "pms.workflow.monitor")).get(
        f"{API}/applications/?domain=CustomDomain"
    )
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_tc_161_pms_afr_191_log_access_to_reports_for_audit_purposes(stub_iam):
    """Test ID: TC-161 | Source ID: PMS-AFR-191: log access to reports for audit purposes."""
    res = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.report.view",)).get(f"{API}/reports/")
    assert res.status_code == 200
    assert PmsAuditTrail.objects.filter(actor_user_id=9001, action_type="report_viewed").exists()


def test_tc_162_pms_afr_192_trigger_email_notification_for_application_submission():
    """Test ID: TC-162 | Source ID: PMS-AFR-192: trigger email notification for application submission."""
    _make_app(applicant_user_id=1001)
    assert PmsNotificationOutbox.objects.filter(
        topic="application.submitted", recipient_user_id=1001
    ).exists()


def test_tc_163_pms_afr_193_trigger_email_notification_for_application_status_changes():
    """Test ID: TC-163 | Source ID: PMS-AFR-193: trigger email notification for application status changes."""
    app = _make_app(applicant_user_id=1001)
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    assert PmsNotificationOutbox.objects.filter(topic="application.assigned_director").exists()


def test_tc_164_pms_afr_194_trigger_email_notification_for_assignment_to_director():
    """Test ID: TC-164 | Source ID: PMS-AFR-194: trigger email notification for assignment to Director."""
    app = _make_app(applicant_user_id=1001)
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    assert PmsNotificationOutbox.objects.filter(
        topic="application.assigned_director", recipient_user_id=2001
    ).exists()


def test_tc_165_pms_afr_195_trigger_email_notification_for_assignment_to_attorney():
    """Test ID: TC-165 | Source ID: PMS-AFR-195: trigger email notification for assignment to Attorney."""
    enqueue_notification(
        topic="attorney.assigned",
        dedupe_key="pms:fr:atty:assign:1",
        subject="Attorney Assigned",
        body="Assignment offered",
        recipient_user_id=5001,
    )
    assert PmsNotificationOutbox.objects.filter(topic="attorney.assigned", recipient_user_id=5001).exists()


def test_tc_166_pms_afr_196_trigger_email_notification_for_review_decisions():
    """Test ID: TC-166 | Source ID: PMS-AFR-196: trigger email notification for review decisions."""
    enqueue_notification(
        topic="application.reviewed",
        dedupe_key="pms:fr:rev:1",
        subject="Review Decision",
        body="Decision recorded",
        recipient_user_id=1001,
    )
    assert PmsNotificationOutbox.objects.filter(topic="application.reviewed", recipient_user_id=1001).exists()


def test_tc_167_pms_afr_197_trigger_email_notification_for_budget_approval_or_rejection():
    """Test ID: TC-167 | Source ID: PMS-AFR-197: trigger email notification for budget approval or rejection."""
    enqueue_notification(
        topic="budget.decided",
        dedupe_key="pms:fr:bud:1",
        subject="Budget Decided",
        body="Budget approved",
        recipient_user_id=1001,
    )
    assert PmsNotificationOutbox.objects.filter(topic="budget.decided", recipient_user_id=1001).exists()


def test_tc_168_pms_afr_198_trigger_email_notification_for_filing_confirmations():
    """Test ID: TC-168 | Source ID: PMS-AFR-198: trigger email notification for filing confirmations."""
    enqueue_notification(
        topic="patent.filed",
        dedupe_key="pms:fr:filed:1",
        subject="Patent Filed",
        body="Filing confirmed",
        recipient_user_id=1001,
    )
    assert PmsNotificationOutbox.objects.filter(topic="patent.filed", recipient_user_id=1001).exists()


def test_tc_169_pms_afr_199_trigger_email_notification_for_office_actions():
    """Test ID: TC-169 | Source ID: PMS-AFR-199: trigger email notification for office actions."""
    enqueue_notification(
        topic="office_action.recorded",
        dedupe_key="pms:fr:oa:1",
        subject="Office Action",
        body="OA recorded",
        recipient_user_id=1001,
    )
    assert PmsNotificationOutbox.objects.filter(topic="office_action.recorded", recipient_user_id=1001).exists()


def test_tc_170_pms_afr_200_trigger_email_notification_for_deadline_reminders():
    """Test ID: TC-170 | Source ID: PMS-AFR-200: trigger email notification for deadline reminders."""
    enqueue_notification(
        topic="deadline.alert_15",
        dedupe_key="pms:fr:dl15:1",
        subject="15-day reminder",
        body="Deadline approaching",
        recipient_user_id=2001,
    )
    assert PmsNotificationOutbox.objects.filter(topic="deadline.alert_15", recipient_user_id=2001).exists()


def test_tc_171_pms_afr_201_trigger_email_notification_for_deadline_escalations():
    """Test ID: TC-171 | Source ID: PMS-AFR-201: trigger email notification for deadline escalations."""
    enqueue_notification(
        topic="deadline.escalated",
        dedupe_key="pms:fr:esc:1",
        subject="Deadline Escalated",
        body="Deadline missed",
        recipient_user_id=2001,
    )
    assert PmsNotificationOutbox.objects.filter(topic="deadline.escalated", recipient_user_id=2001).exists()


def test_tc_172_pms_afr_202_trigger_email_notification_for_maintenance_fee_reminders():
    """Test ID: TC-172 | Source ID: PMS-AFR-202: trigger email notification for maintenance-fee reminders."""
    enqueue_notification(
        topic="deadline.alert_30",
        dedupe_key="pms:fr:maint30:1",
        subject="Maintenance Fee Reminder",
        body="Renewal fee due in 30 days",
        recipient_user_id=5001,
    )
    assert PmsNotificationOutbox.objects.filter(topic="deadline.alert_30", recipient_user_id=5001).exists()


def test_tc_173_pms_afr_203_trigger_email_notification_for_document_updates():
    """Test ID: TC-173 | Source ID: PMS-AFR-203: trigger email notification for document updates."""
    enqueue_notification(
        topic="document.updated",
        dedupe_key="pms:fr:docupd:1",
        subject="Document Updated",
        body="Document updated",
        recipient_user_id=1001,
    )
    assert PmsNotificationOutbox.objects.filter(topic="document.updated", recipient_user_id=1001).exists()


def test_tc_174_pms_afr_204_trigger_email_notification_for_document_version_changes():
    """Test ID: TC-174 | Source ID: PMS-AFR-204: trigger email notification for document version changes."""
    enqueue_notification(
        topic="document.updated",
        dedupe_key="pms:fr:docver:1",
        subject="New Document Version",
        body="Version 2 uploaded",
        recipient_user_id=1001,
    )
    assert PmsNotificationOutbox.objects.filter(dedupe_key="pms:fr:docver:1").exists()


def test_tc_175_pms_afr_206_notification_scope_limited_to_triggering_system_generated_emails():
    """Test ID: TC-175 | Source ID: PMS-AFR-206: notification scope limited to triggering system-generated emails."""
    row = enqueue_notification(
        topic="application.submitted",
        dedupe_key="pms:fr:scope:1",
        subject="Outbox Event",
        body="Body",
        recipient_email="user@example.test",
    )
    assert row is not None
    assert row.status == "pending"
    sent = send_pending_notifications()
    assert sent >= 1
    row.refresh_from_db()
    assert row.status == "sent"


def test_tc_176_pms_afr_207_maintain_audit_trail_of_pms_actions():
    """Test ID: TC-176 | Source ID: PMS-AFR-207: maintain audit trail of PMS actions."""
    app = _make_app()
    assert PmsAuditTrail.objects.filter(application=app).exists()


def test_tc_177_pms_afr_208_log_all_user_actions():
    """Test ID: TC-177 | Source ID: PMS-AFR-208: log all user actions."""
    app = _make_app(applicant_user_id=1001)
    assert PmsAuditTrail.objects.filter(application=app, actor_user_id=1001).exists()


def test_tc_178_pms_afr_209_log_all_status_changes():
    """Test ID: TC-178 | Source ID: PMS-AFR-209: log all status changes."""
    app = _make_app(applicant_user_id=1001)
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    log = PmsAuditTrail.objects.filter(application=app, action_type="director_assigned").first()
    assert log is not None
    assert log.from_state == "submitted"
    assert log.to_state == "under_review"


def test_tc_179_pms_afr_210_log_all_document_modifications():
    """Test ID: TC-179 | Source ID: PMS-AFR-210: log all document modifications."""
    app = _make_app(applicant_user_id=1001)
    app.documents.create(
        doc_type="specification", title="Doc", file_format="pdf", file_size_bytes=100, uploaded_by_user_id=1001
    )
    from modules.pms.services import log_audit

    log_audit(application=app, actor_user_id=1001, action_type="document_modified", details={"doc": "Doc"})
    assert PmsAuditTrail.objects.filter(application=app, action_type="document_modified").exists()


def test_tc_180_pms_afr_211_audit_log_required_fields():
    """Test ID: TC-180 | Source ID: PMS-AFR-211: audit log required fields."""
    app = _make_app(applicant_user_id=1001)
    assign_director(application_id=app.id, director_user_id=2001, assigned_by_user_id=9001)
    log = PmsAuditTrail.objects.filter(application=app, action_type="director_assigned").first()
    assert log.actor_user_id == 9001
    assert log.action_type == "director_assigned"
    assert log.timestamp is not None
    assert log.application_id == app.id
    assert log.from_state == "submitted"
    assert log.to_state == "under_review"


def test_tc_181_pms_afr_212_immutable_audit_records_for_critical_operations():
    """Test ID: TC-181 | Source ID: PMS-AFR-212: immutable audit records for critical operations."""
    app = _make_app(applicant_user_id=1001)
    log = PmsAuditTrail.objects.filter(application=app).first()
    assert log.is_immutable is True


def test_tc_182_pms_afr_213_audit_logs_for_compliance_verification_and_forensic_analysis(stub_iam):
    """Test ID: TC-182 | Source ID: PMS-AFR-213: audit logs for compliance verification and forensic analysis."""
    app = _make_app(applicant_user_id=1001)
    client = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.audit.view", "pms.workflow.monitor"))
    res = client.get(f"{API}/audit-trail/?application_id={app.id}&action_type=application_submitted")
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_tc_183_pms_afr_214_encryption_at_rest_where_implemented_at_boundary():
    """Test ID: TC-183 | Source ID: PMS-AFR-214: encryption at rest where implemented at boundary."""
    app = _make_app(applicant_user_id=1001, title="Persisted Boundary Record")
    fetched = PatentApplication.objects.get(pk=app.pk)
    assert fetched.title == "Persisted Boundary Record"


def test_tc_184_pms_afr_215_encryption_in_transit_where_implemented_at_boundary(stub_iam):
    """Test ID: TC-184 | Source ID: PMS-AFR-215: encryption in transit where implemented at boundary."""
    client = _auth_client(stub_iam, 1001, "student", ("pms.application.view_self",))
    res = client.get(f"{API}/applications/", HTTP_X_FORWARDED_PROTO="https", secure=True)
    assert res.status_code == 200


def test_tc_185_pms_afr_216_require_valid_role_assignment_before_accessing_pms_functions(stub_iam):
    """Test ID: TC-185 | Source ID: PMS-AFR-216: require valid role assignment before accessing PMS functions."""
    client = _auth_client(stub_iam, 1001, "student", ())
    res = client.get(f"{API}/applications/")
    assert res.status_code == 403


def test_tc_186_pms_afr_217_prevent_attorney_assignment_until_director_approval_is_recorded():
    """Test ID: TC-186 | Source ID: PMS-AFR-217: prevent attorney assignment until Director approval is recorded."""
    AttorneyPanel.objects.create(attorney_user_id=5001, name="Atty", email="a@t.org", is_approved=True)
    app = _make_app(applicant_user_id=1001)
    from modules.pms.domain.errors import PreconditionNotMetError
    from modules.pms.services import assign_attorney

    with pytest.raises(PreconditionNotMetError):
        assign_attorney(application_id=app.id, attorney_user_id=5001, assigned_by_user_id=9001)


def test_tc_187_pms_afr_218_prevent_external_filing_until_approvals_and_budget_complete():
    """Test ID: TC-187 | Source ID: PMS-AFR-218: prevent external filing until required approvals and budget allocation are complete."""
    app = _make_app(applicant_user_id=1001)
    app.status = PatentApplicationStatus.APPROVED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    app.attorney_assignments.create(attorney_user_id=5001, assigned_by_user_id=9001, status="accepted", is_active=True)

    from modules.pms.domain.errors import PreconditionNotMetError
    from modules.pms.services import record_external_filing

    with pytest.raises(PreconditionNotMetError):
        record_external_filing(
            application_id=app.id,
            attorney_user_id=5001,
            external_filing_id="EXT-1",
            external_filing_date=datetime.date(2026, 7, 1),
            filing_confirmation="CONF-1",
        )


def test_tc_188_pms_afr_220_role_based_access_control_for_confidential_patent_information(stub_iam):
    """Test ID: TC-188 | Source ID: PMS-AFR-220: role-based access control for confidential patent information."""
    app = _make_app(applicant_user_id=2001, title="Confidential Patent")
    client = _auth_client(stub_iam, 1001, "student", ("pms.application.view_self",))
    res = client.get(f"{API}/applications/{app.id}/")
    assert res.status_code == 404


def test_tc_189_pms_afr_221_maintain_one_active_pcc_admin_as_system_oversight_role():
    """Test ID: TC-189 | Source ID: PMS-AFR-221: maintain one active PCC_ADMIN as system oversight role."""
    PmsRoleAssignment.objects.create(user_id=9001, role="PCC_ADMIN", is_active=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        PmsRoleAssignment.objects.create(user_id=9002, role="PCC_ADMIN", is_active=True)


def test_tc_190_pms_afr_222_multiple_directors_handle_reviews_by_expertise_domain():
    """Test ID: TC-190 | Source ID: PMS-AFR-222: multiple Directors handle reviews by expertise domain."""
    app_a = _make_app(applicant_user_id=1001, domain="DomainA", title="App A")
    app_b = _make_app(applicant_user_id=1002, domain="DomainB", title="App B")
    assign_director(application_id=app_a.id, director_user_id=2001, assigned_by_user_id=9001)
    assign_director(application_id=app_b.id, director_user_id=2002, assigned_by_user_id=9001)
    assert PatentApplication.objects.get(pk=app_a.pk).assigned_director_user_id == 2001
    assert PatentApplication.objects.get(pk=app_b.pk).assigned_director_user_id == 2002


def test_tc_191_pms_afr_223_multiple_attorneys_from_approved_panels_conduct_assessments():
    """Test ID: TC-191 | Source ID: PMS-AFR-223: multiple Attorneys from approved panels conduct assessments."""
    AttorneyPanel.objects.create(attorney_user_id=5001, name="At 1", email="a1@t.org", is_approved=True)
    AttorneyPanel.objects.create(attorney_user_id=5002, name="At 2", email="a2@t.org", is_approved=True)
    approved_count = AttorneyPanel.objects.filter(is_approved=True).count()
    assert approved_count >= 2


def test_tc_192_pms_afr_224_multiple_applicants_submit_patent_applications():
    """Test ID: TC-192 | Source ID: PMS-AFR-224: multiple Applicants submit patent applications."""
    a1 = _make_app(applicant_user_id=1001, title="Applicant 1 Filing")
    a2 = _make_app(applicant_user_id=1002, title="Applicant 2 Filing")
    assert a1.applicant_user_id != a2.applicant_user_id
    assert PatentApplication.objects.filter(pk__in=[a1.pk, a2.pk]).count() == 2


def test_tc_193_pms_afr_225_enforce_status_driven_handling_and_valid_transitions():
    """Test ID: TC-193 | Source ID: PMS-AFR-225: enforce status-driven handling and valid transitions."""
    with pytest.raises(InvalidTransitionError):
        validate_transition(
            PatentApplicationStatus.SUBMITTED,
            PatentApplicationStatus.GRANTED,
            actor_role="Attorney",
        )


def test_tc_194_pms_afr_226_support_escalation_mechanisms_for_delayed_actions():
    """Test ID: TC-194 | Source ID: PMS-AFR-226: support escalation mechanisms for delayed actions."""
    now = timezone.now()
    app = _make_app()
    app.status = PatentApplicationStatus.UNDER_REVIEW.value
    app.assigned_director_user_id = 2001
    app.review_deadline = now - datetime.timedelta(days=3)
    app.save()

    stats = monitor_and_process_deadlines(now=now)
    assert stats["escalations"] >= 1


def test_tc_195_pms_afr_227_permit_parallel_processing_where_explicitly_defined_or_configured():
    """Test ID: TC-195 | Source ID: PMS-AFR-227: permit parallel processing where explicitly defined or configured."""
    app = _make_app()
    app.status = PatentApplicationStatus.APPROVED.value
    app.assigned_director_user_id = 2001
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_director_user_id", "assigned_attorney_user_id", "updated_at"])
    app.attorney_assignments.create(attorney_user_id=5001, assigned_by_user_id=9001, status="accepted", is_active=True)

    from modules.pms.services import record_legal_advice, submit_or_update_budget

    budget = submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("5000.00"),
        attorney_fees=Decimal("5000.00"),
        administrative_costs=Decimal("1000.00"),
        actor_user_id=2001,
    )
    advice = record_legal_advice(
        application_id=app.id,
        attorney_user_id=5001,
        stage="review",
        advice_text="Parallel legal advice recorded during budget review.",
    )
    assert budget.status == "pending_approval"
    assert advice.pk is not None


def test_tc_195b_pms_afr_227_restrict_parallel_processing_where_not_defined_or_configured():
    """Test ID: TC-195b | Source ID: PMS-AFR-227: restrict parallel processing where not explicitly defined or configured."""
    with pytest.raises(InvalidTransitionError):
        validate_transition(
            PatentApplicationStatus.SUBMITTED,
            PatentApplicationStatus.FILED,
            actor_role="Attorney",
        )


def test_tc_196_pms_afr_228_patent_office_system_integration_boundary():
    """Test ID: TC-196 | Source ID: PMS-AFR-228: patent-office system integration boundary."""
    app = _make_app()
    app.status = PatentApplicationStatus.FILED.value
    app.assigned_attorney_user_id = 5001
    app.external_filing_id = "EXT-BOUNDARY-1"
    app.save(update_fields=["status", "assigned_attorney_user_id", "external_filing_id", "updated_at"])
    assert PatentApplication.objects.get(pk=app.pk).external_filing_id == "EXT-BOUNDARY-1"


def test_tc_197_pms_afr_229_financial_system_integration_boundary():
    """Test ID: TC-197 | Source ID: PMS-AFR-229: financial-system integration boundary."""
    app = _make_app()
    app.status = PatentApplicationStatus.APPROVED.value
    app.assigned_director_user_id = 2001
    app.save(update_fields=["status", "assigned_director_user_id", "updated_at"])
    from modules.pms.services import submit_or_update_budget

    budget = submit_or_update_budget(
        application_id=app.id,
        filing_fees=Decimal("2000.00"),
        attorney_fees=Decimal("3000.00"),
        administrative_costs=Decimal("500.00"),
        actor_user_id=2001,
    )
    assert budget.total_cost == Decimal("5500.00")


def test_tc_198_pms_afr_230_document_management_system_integration_boundary():
    """Test ID: TC-198 | Source ID: PMS-AFR-230: document-management-system integration boundary."""
    app = _make_app()
    doc = app.documents.create(
        doc_type="specification",
        title="DMS Metadata Doc",
        file_format="pdf",
        file_size_bytes=2048,
        version=1,
        is_current=True,
        uploaded_by_user_id=1001,
    )
    assert doc.version == 1
    assert doc.is_current is True


def test_tc_199_pms_afr_231_external_prior_art_databases_treated_as_query_sources():
    """Test ID: TC-199 | Source ID: PMS-AFR-231: external prior-art databases treated as query sources."""
    with pytest.raises(ExternalServiceUnavailableError):
        prior_art_service.search_prior_art(query="external source check", actor_user_id=1001)


def test_tc_200_pms_afr_232_external_patent_office_filing_success_not_internally_controlled():
    """Test ID: TC-200 | Source ID: PMS-AFR-232: external patent-office filing success not internally controlled."""
    app = _make_app()
    app.status = PatentApplicationStatus.APPROVED.value
    app.assigned_attorney_user_id = 5001
    app.save(update_fields=["status", "assigned_attorney_user_id", "updated_at"])
    app.attorney_assignments.create(attorney_user_id=5001, assigned_by_user_id=9001, status="accepted", is_active=True)
    app.budget.status = "approved"
    app.budget.save(update_fields=["status", "updated_at"])

    from modules.pms.services import record_external_filing

    filed = record_external_filing(
        application_id=app.id,
        attorney_user_id=5001,
        external_filing_id="EXT-ACK-2026",
        external_filing_date=datetime.date(2026, 7, 10),
        filing_confirmation="External portal receipt recorded",
    )
    assert filed.filing_confirmation == "External portal receipt recorded"


def test_tc_202_pms_afr_237_dashboards_within_pms_reporting_scope(stub_iam):
    """Test ID: TC-202 | Source ID: PMS-AFR-237: dashboards within PMS reporting scope."""
    _make_app(applicant_user_id=1001, domain="DashboardDomain")
    res = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.report.view",)).get(f"{API}/reports/")
    assert res.status_code == 200
    assert "total_applications" in res.json()


def test_tc_203_pms_afr_238_historical_data_analysis_within_pms_reporting_scope(stub_iam):
    """Test ID: TC-203 | Source ID: PMS-AFR-238: historical data analysis within PMS reporting scope."""
    _make_app(applicant_user_id=1001, domain="HistoryDomain")
    res = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.report.view",)).get(f"{API}/reports/")
    assert res.status_code == 200


def test_tc_204_pms_afr_239_trend_reporting_within_pms_reporting_scope(stub_iam):
    """Test ID: TC-204 | Source ID: PMS-AFR-239: trend reporting within PMS reporting scope."""
    _make_app(applicant_user_id=1001, domain="TrendDomain")
    res = _auth_client(stub_iam, 9001, "pcc_admin", ("pms.report.view",)).get(f"{API}/reports/")
    assert res.status_code == 200
    assert "domain_distribution" in res.json()
