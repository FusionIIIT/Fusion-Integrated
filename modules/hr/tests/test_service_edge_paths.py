"""Behavioral tests for HR service validation and alternate workflow paths."""

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.utils import timezone

from conftest import make_session
from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from fusion_auth.principal import Principal
from modules.hr.domain import state_machine as sm
from modules.hr.models import (
    Appraisal,
    AppraisalWindow,
    AuditEvent,
    Claim,
    ClaimIntegrationStatus,
    EmployeeRecord,
    HRNotification,
    LeaveBalance,
    LeaveLedgerEntry,
    LeaveRequest,
    WorkflowRoute,
)
from modules.hr.services import appraisals, authz, claims, configuration, employees, leaves

pytestmark = pytest.mark.django_db


def actor(user_id=7, *permissions):
    return Principal.from_session(
        make_session(
            user_id=user_id,
            kind="staff",
            modules=("hr",),
            permissions=permissions,
        )
    )


def employee(user_id=1001, *, status="active", category="staff", **fields):
    return EmployeeRecord.objects.create(
        user_id=user_id,
        employee_category=category,
        employment_status=status,
        department="Research",
        designation="Officer",
        created_by_user_id=7,
        updated_by_user_id=7,
        **fields,
    )


def claim_row(*, user_id=1001, status="pending_verification", route=None, current=None):
    return Claim.objects.create(
        employee_user_id=user_id,
        employee_category="staff",
        request_type="ltc_reimbursement",
        purpose="Family visit",
        form_data={"destination": "Delhi"},
        status=status,
        route_snapshot=route or [],
        current_authority_user_id=current,
    )


def leave_row(employee_record, *, route=None, status="pending_authority", authority=88, step=0):
    return LeaveRequest.objects.create(
        employee=employee_record,
        leave_type="casual",
        duration_days=Decimal("1.00"),
        justification="Family",
        status=status,
        route_snapshot=route if route is not None else [{"approver_user_id": authority}],
        authority_step=step,
        current_authority_user_id=authority,
        submitted_by_user_id=employee_record.user_id,
    )


def install_directory(monkeypatch, people, active=None):
    monkeypatch.setattr(
        employees.directory,
        "get_users",
        lambda user_ids: {uid: people[uid] for uid in user_ids if uid in people},
    )
    monkeypatch.setattr(
        employees.directory, "held_employee_ids", lambda: set(people if active is None else active)
    )
    monkeypatch.setattr(
        configuration.directory,
        "get_users",
        lambda user_ids: {uid: people[uid] for uid in user_ids if uid in people},
    )
    monkeypatch.setattr(
        configuration.directory,
        "held_employee_ids",
        lambda: set(people if active is None else active),
    )
    monkeypatch.setattr(
        appraisals.directory,
        "get_users",
        lambda user_ids: {uid: people[uid] for uid in user_ids if uid in people},
    )
    monkeypatch.setattr(
        appraisals.directory,
        "held_employee_ids",
        lambda: set(people if active is None else active),
    )


@pytest.mark.parametrize(
    ("employee_status", "expected_code"),
    [(None, "employee_record_required"), ("separated", "employee_record_required")],
)
def test_claim_submission_requires_active_employee_record(employee_status, expected_code):
    if employee_status:
        employee(status=employee_status)
    with pytest.raises(ConflictError) as error:
        claims.submit_claim(
            actor=actor(1001, "hr.claim.create"),
            request_type="ltc_reimbursement",
            form_data={"destination": "Delhi"},
        )
    assert error.value.code == expected_code


def test_claim_submission_rejects_unknown_request_type():
    employee()
    with pytest.raises(ConflictError) as error:
        claims.submit_claim(
            actor=actor(1001, "hr.claim.create"), request_type="other", form_data={"x": 1}
        )
    assert error.value.code == "invalid_claim_type"


@pytest.mark.parametrize(
    ("request_type", "kwargs", "expected_code"),
    [
        ("cpda_advance", {"purpose": "", "amount": Decimal("0")}, "cpda_fields_required"),
        ("ltc_advance", {}, "ltc_form_required"),
        (
            "ltc_advance",
            {"form_data": {"destination": "Delhi"}, "amount": Decimal("0")},
            "invalid_claim_amount",
        ),
    ],
)
def test_claim_submission_rejects_type_specific_missing_or_invalid_fields(
    request_type, kwargs, expected_code
):
    employee()
    with pytest.raises(ConflictError) as error:
        claims.submit_claim(
            actor=actor(1001, "hr.claim.create"), request_type=request_type, **kwargs
        )
    assert error.value.code == expected_code


def test_claim_submission_rejects_non_drive_supporting_link():
    employee()
    with pytest.raises(ConflictError) as error:
        claims.submit_claim(
            actor=actor(1001, "hr.claim.create"),
            request_type="cpda_advance",
            purpose="Equipment",
            amount=Decimal("100"),
            supporting_document_links=["https://evil.example/doc"],
        )
    assert error.value.code == "url_not_drive"


@pytest.mark.parametrize(
    ("request_type", "kwargs", "expected_documents"),
    [
        ("ltc_reimbursement", {"form_data": {"destination": "Delhi"}}, []),
        (
            "cpda_reimbursement",
            {
                "purpose": "Research material",
                "amount": Decimal("125.50"),
                "supporting_document_links": [
                    "https://drive.google.com/file/d/abcdefghij123/view?usp=sharing"
                ],
            },
            [
                {
                    "file_id": "abcdefghij123",
                    "url": "https://drive.google.com/file/d/abcdefghij123/view",
                }
            ],
        ),
    ],
)
def test_claim_submission_records_valid_ltc_and_cpda_payloads(
    request_type, kwargs, expected_documents
):
    employee()
    result = claims.submit_claim(
        actor=actor(1001, "hr.claim.create"), request_type=request_type, **kwargs
    )
    assert result.status == sm.PENDING_VERIFICATION
    assert result.supporting_documents == expected_documents
    assert AuditEvent.objects.filter(entity_type="claim", entity_id=result.pk).exists()
    assert HRNotification.objects.filter(topic="claim.submitted").exists()


def test_claim_verification_rejection_persists_note_without_routing():
    row = claim_row()
    result = claims.verify_claim(
        actor=actor(7, "hr.claim.verify"), claim_id=row.pk, verified=False, note="Needs receipts"
    )
    result.refresh_from_db()
    assert result.status == sm.PENDING_VERIFICATION
    assert result.verification_details["note"] == "Needs receipts"
    assert not HRNotification.objects.filter(topic="claim.awaiting_authority").exists()


def test_claim_verification_requires_pending_claim_and_route(monkeypatch):
    approved = claim_row(status=sm.APPROVED)
    with pytest.raises(ConflictError) as wrong_state:
        claims.verify_claim(actor=actor(7, "hr.claim.verify"), claim_id=approved.pk, verified=True)
    assert wrong_state.value.code == "invalid_transition"

    pending = claim_row()
    with pytest.raises(ConflictError) as missing_route:
        claims.verify_claim(actor=actor(7, "hr.claim.verify"), claim_id=pending.pk, verified=True)
    assert missing_route.value.code == "workflow_not_configured"

    WorkflowRoute.objects.create(
        employee_category="staff",
        request_type="ltc_reimbursement",
        steps=[{}],
        updated_by_user_id=7,
    )
    with pytest.raises(ConflictError) as invalid_step:
        claims.verify_claim(actor=actor(7, "hr.claim.verify"), claim_id=pending.pk, verified=True)
    assert invalid_step.value.code == "invalid_workflow_route"


def test_claim_verification_rejects_route_without_first_authority(monkeypatch):
    row = claim_row()
    monkeypatch.setattr(
        claims.configuration,
        "configured_route",
        lambda **kwargs: SimpleNamespace(steps=[]),
    )
    with pytest.raises(ConflictError) as error:
        claims.verify_claim(actor=actor(7, "hr.claim.verify"), claim_id=row.pk, verified=True)
    assert error.value.code == "invalid_workflow_route"


def test_claim_verification_routes_validated_claim_and_notifies_authority():
    row = claim_row()
    WorkflowRoute.objects.create(
        employee_category="staff",
        request_type="ltc_reimbursement",
        steps=[{"approver_user_id": 88, "authority_label": "HOD"}],
        updated_by_user_id=7,
    )
    result = claims.verify_claim(
        actor=actor(7, "hr.claim.verify"), claim_id=row.pk, verified=True, note="Complete"
    )
    assert result.status == sm.PENDING_AUTHORITY
    assert result.current_authority_user_id == 88
    assert HRNotification.objects.filter(topic="claim.awaiting_authority").exists()


def test_claim_decision_reports_missing_and_invalid_claims():
    with pytest.raises(NotFoundError):
        claims.decide_claim(actor=actor(88, "hr.claim.approve"), claim_id=999, action="approve")
    row = claim_row(status=sm.PENDING_AUTHORITY, route=[{"approver_user_id": 88}], current=88)
    with pytest.raises(ConflictError) as bad_action:
        claims.decide_claim(actor=actor(88, "hr.claim.approve"), claim_id=row.pk, action="cancel")
    assert bad_action.value.code == "invalid_transition"


def test_corrupted_claim_route_step_is_rejected_before_routing():
    from modules.hr.services.claims import _route_step

    with pytest.raises(ConflictError) as error:
        _route_step([], 0)
    assert error.value.code == "invalid_workflow_route"


@pytest.mark.parametrize(
    ("status", "financially_correct", "details", "expected_code"),
    [
        (sm.PENDING_AUTHORITY, True, {}, "invalid_transition"),
        (sm.APPROVED, False, {"voucher": "V1"}, "financial_verification_required"),
    ],
)
def test_claim_processing_requires_approved_and_financially_correct_claim(
    status, financially_correct, details, expected_code
):
    row = claim_row(status=status)
    with pytest.raises(ConflictError) as error:
        claims.process_claim(
            actor=actor(5, "hr.claim.manage"),
            claim_id=row.pk,
            financially_correct=financially_correct,
            details=details,
        )
    assert error.value.code == expected_code


def test_claim_processing_requires_details_and_records_financial_result():
    row = claim_row(status=sm.APPROVED)
    with pytest.raises(ConflictError) as missing_details:
        claims.process_claim(
            actor=actor(5, "hr.claim.manage"), claim_id=row.pk, financially_correct=True, details={}
        )
    assert missing_details.value.code == "processing_details_required"

    result = claims.process_claim(
        actor=actor(5, "hr.claim.manage"),
        claim_id=row.pk,
        financially_correct=True,
        details={"voucher": "V-100"},
    )
    assert result.status == sm.FINANCIAL_PROCESSING_RECORDED
    assert result.processed_by_user_id == 5


@pytest.mark.parametrize(
    ("status", "system", "external_status", "expected_code"),
    [
        (sm.PENDING_VERIFICATION, "finance", "Received", "invalid_transition"),
        (sm.APPROVED, "unknown", "Received", "invalid_integration_status"),
        (sm.APPROVED, "finance", "  ", "invalid_integration_status"),
    ],
)
def test_claim_external_status_rejects_unapproved_or_invalid_status(
    status, system, external_status, expected_code
):
    row = claim_row(status=status)
    with pytest.raises(ConflictError) as error:
        claims.record_integration_status(
            actor=actor(5, "hr.claim.manage"),
            claim_id=row.pk,
            system=system,
            external_status=external_status,
        )
    assert error.value.code == expected_code


def test_claim_external_status_records_supported_finance_result():
    row = claim_row(status=sm.APPROVED)
    result = claims.record_integration_status(
        actor=actor(5, "hr.claim.manage"),
        claim_id=row.pk,
        system="finance",
        external_status=" Paid ",
        external_reference=" INV-7 ",
    )
    assert result.external_status == "Paid"
    assert result.external_reference == "INV-7"
    assert ClaimIntegrationStatus.objects.filter(claim=row).count() == 1


@pytest.mark.parametrize("no_actor", [True, False])
def test_authz_requires_actor_and_at_least_one_permission(no_actor):
    principal = None if no_actor else actor(7)
    with pytest.raises(PermissionDeniedError):
        authz.require(principal, "hr.claim.view", "hr.claim.approve")


def test_employee_creation_checks_directory_and_management_permissions(monkeypatch):
    no_appointment = actor(7, "hr.employee.create")
    with pytest.raises(PermissionDeniedError):
        employees.create_employee_record(
            actor=no_appointment,
            user_id=1001,
            department="Research",
            designation="Officer",
            appointment_type="Permanent",
        )

    install_directory(monkeypatch, {})
    with pytest.raises(NotFoundError):
        employees.create_employee_record(
            actor=actor(7, "hr.employee.create"),
            user_id=1001,
            department="Research",
            designation="Officer",
        )


@pytest.mark.parametrize(
    ("person", "active", "expected"),
    [
        (None, {1001}, "not_found"),
        (SimpleNamespace(kind="student"), {1001}, "not_found"),
        (SimpleNamespace(kind="staff"), set(), "not_found"),
    ],
)
def test_employee_creation_requires_active_staff_identity(monkeypatch, person, active, expected):
    people = {} if person is None else {1001: person}
    install_directory(monkeypatch, people, active)
    with pytest.raises(NotFoundError):
        employees.create_employee_record(
            actor=actor(7, "hr.employee.create"),
            user_id=1001,
            department="Research",
            designation="Officer",
        )


def test_employee_creation_rejects_duplicate_and_unknown_fields(monkeypatch):
    install_directory(
        monkeypatch,
        {1001: SimpleNamespace(kind="staff"), 1002: SimpleNamespace(kind="staff")},
    )
    employee()
    with pytest.raises(ConflictError) as duplicate:
        employees.create_employee_record(
            actor=actor(7, "hr.employee.create"),
            user_id=1001,
            department="Research",
            designation="Officer",
        )
    assert duplicate.value.code == "employee_record_exists"
    with pytest.raises(ValueError, match="Unsupported employee record fields"):
        employees.create_employee_record(
            actor=actor(7, "hr.employee.create"),
            user_id=1002,
            department="Research",
            designation="Officer",
            mystery_field="ignored",
        )


def test_employee_create_and_update_audit_valid_changes(monkeypatch):
    install_directory(monkeypatch, {1001: SimpleNamespace(kind="staff")})
    created = employees.create_employee_record(
        actor=actor(7, "hr.employee.create"),
        user_id=1001,
        department="Research",
        designation="Officer",
    )
    updated = employees.update_employee_record(
        actor=actor(7, "hr.employee.update"),
        user_id=1001,
        changes={"department": "Physics"},
    )
    assert created.user_id == updated.user_id == 1001
    assert updated.department == "Physics"
    assert AuditEvent.objects.filter(entity_type="employee", entity_id=created.pk).count() == 2


@pytest.mark.parametrize("changes", [{}, {"other": "value"}])
def test_employee_update_rejects_empty_or_unknown_fields(changes):
    employee()
    with pytest.raises(ConflictError) as error:
        employees.update_employee_record(
            actor=actor(7, "hr.employee.update"), user_id=1001, changes=changes
        )
    assert error.value.code == "invalid_employee_update"


def test_employee_update_requires_existing_record_and_employment_permission():
    with pytest.raises(NotFoundError):
        employees.update_employee_record(
            actor=actor(7, "hr.employee.update"), user_id=1001, changes={"department": "Physics"}
        )
    employee()
    with pytest.raises(PermissionDeniedError):
        employees.update_employee_record(
            actor=actor(7, "hr.employee.update"),
            user_id=1001,
            changes={"appointment_type": "Permanent"},
        )


def test_employee_update_preserves_appraisal_archive_while_editing_other_history():
    archive = {
        "record_type": "appraisal_archive",
        "appraisal_id": 3,
        "period": "2025",
        "finalized_at": "2025-12-01T00:00:00+00:00",
    }
    row = employee(
        user_id=1001,
        service_history=[archive, {"record_type": "note", "value": "old"}],
    )
    updated = employees.update_employee_record(
        actor=actor(7, "hr.employee.update"),
        user_id=1001,
        changes={"service_history": [archive, {"record_type": "note", "value": "updated"}]},
    )
    assert updated.pk == row.pk
    assert updated.service_history[0] == archive
    assert updated.service_history[1]["value"] == "updated"


def test_employee_service_record_access_returns_or_reports_missing():
    from modules.hr.services.employees import employee_record as get_employee_record

    employee()
    assert get_employee_record(user_id=1001, principal=actor(1001, "hr.employee.view_self")).pk
    with pytest.raises(NotFoundError):
        get_employee_record(user_id=9999, principal=actor(9999, "hr.employee.view_self"))


def test_appraisal_submission_validates_employee_window_and_form():
    with pytest.raises(ConflictError) as missing_employee:
        appraisals.submit_appraisal(
            actor=actor(1001, "hr.appraisal.create"), period="2026", form_data={"summary": "x"}
        )
    assert missing_employee.value.code == "employee_record_required"
    employee()
    with pytest.raises(ConflictError) as closed_window:
        appraisals.submit_appraisal(
            actor=actor(1001, "hr.appraisal.create"), period="2026", form_data={"summary": "x"}
        )
    assert closed_window.value.code == "appraisal_window_closed"
    AppraisalWindow.objects.create(
        period="2026",
        opens_at=timezone.now() - timedelta(days=1),
        closes_at=timezone.now() + timedelta(days=1),
        updated_by_user_id=7,
    )
    with pytest.raises(ConflictError) as empty_form:
        appraisals.submit_appraisal(
            actor=actor(1001, "hr.appraisal.create"), period="2026", form_data={}
        )
    assert empty_form.value.code == "appraisal_data_required"


def test_appraisal_submission_saves_and_prevents_duplicate_period():
    employee()
    AppraisalWindow.objects.create(
        period="2026",
        opens_at=timezone.now() - timedelta(days=1),
        closes_at=timezone.now() + timedelta(days=1),
        updated_by_user_id=7,
    )
    result = appraisals.submit_appraisal(
        actor=actor(1001, "hr.appraisal.create"),
        period="2026",
        form_data={"accomplishment": "published"},
    )
    assert result.status == sm.SUBMITTED
    assert HRNotification.objects.filter(topic="appraisal.submitted").exists()
    with pytest.raises(ConflictError) as duplicate:
        appraisals.submit_appraisal(
            actor=actor(1001, "hr.appraisal.create"), period="2026", form_data={"summary": "x"}
        )
    assert duplicate.value.code == "appraisal_already_submitted"


def test_appraisal_assignment_rejects_invalid_route_and_identity(monkeypatch):
    row = Appraisal.objects.create(employee_user_id=1001, period="2026", form_data={"x": 1})
    with pytest.raises(NotFoundError):
        appraisals.assign_reviewers(
            actor=actor(7, "hr.appraisal.assign"), appraisal_id=999, reviewer_user_ids=[88]
        )
    with pytest.raises(ConflictError) as empty:
        appraisals.assign_reviewers(
            actor=actor(7, "hr.appraisal.assign"), appraisal_id=row.pk, reviewer_user_ids=[]
        )
    assert empty.value.code == "reviewers_required"
    with pytest.raises(ConflictError) as invalid_id:
        appraisals.assign_reviewers(
            actor=actor(7, "hr.appraisal.assign"), appraisal_id=row.pk, reviewer_user_ids=[0]
        )
    assert invalid_id.value.code == "reviewers_required"
    with pytest.raises(ConflictError) as duplicate:
        appraisals.assign_reviewers(
            actor=actor(7, "hr.appraisal.assign"), appraisal_id=row.pk, reviewer_user_ids=[88, 88]
        )
    assert duplicate.value.code == "duplicate_appraisal_reviewer"

    install_directory(monkeypatch, {88: SimpleNamespace(kind="student")})
    with pytest.raises(ConflictError) as wrong_kind:
        appraisals.assign_reviewers(
            actor=actor(7, "hr.appraisal.assign"), appraisal_id=row.pk, reviewer_user_ids=[88]
        )
    assert wrong_kind.value.code == "invalid_appraisal_reviewer"


def test_appraisal_assignment_only_allowed_before_review_begins():
    row = Appraisal.objects.create(
        employee_user_id=1001,
        period="2026",
        form_data={"x": 1},
        status=sm.PENDING_REVIEW,
    )
    with pytest.raises(ConflictError) as error:
        appraisals.assign_reviewers(
            actor=actor(7, "hr.appraisal.assign"), appraisal_id=row.pk, reviewer_user_ids=[88]
        )
    assert error.value.code == "invalid_transition"


def test_appraisal_review_rejects_missing_invalid_route_and_wrong_reviewer():
    with pytest.raises(NotFoundError):
        appraisals.review_appraisal(
            actor=actor(88, "hr.appraisal.review"), appraisal_id=999, action="forward"
        )
    row = Appraisal.objects.create(
        employee_user_id=1001, period="2026", form_data={"x": 1}, reviewer_user_ids=[]
    )
    with pytest.raises(ConflictError) as invalid_route:
        appraisals.review_appraisal(
            actor=actor(88, "hr.appraisal.review"), appraisal_id=row.pk, action="forward"
        )
    assert invalid_route.value.code == "invalid_appraisal_route"
    row.reviewer_user_ids = [88]
    row.current_reviewer_index = 0
    row.current_reviewer_user_id = 88
    row.status = sm.PENDING_REVIEW
    row.save()
    with pytest.raises(NotFoundError):
        appraisals.review_appraisal(
            actor=actor(99, "hr.appraisal.review"), appraisal_id=row.pk, action="finalize"
        )


@pytest.mark.parametrize(
    ("reviewer_ids", "action", "expected"),
    [([88], "forward", "workflow_order"), ([88], "cancel", "invalid_transition")],
)
def test_appraisal_review_maps_bad_transition_to_api_conflict(reviewer_ids, action, expected):
    row = Appraisal.objects.create(
        employee_user_id=1001,
        period="2026",
        form_data={"x": 1},
        status=sm.PENDING_REVIEW,
        reviewer_user_ids=reviewer_ids,
        current_reviewer_index=0,
        current_reviewer_user_id=88,
    )
    with pytest.raises(ConflictError) as error:
        appraisals.review_appraisal(
            actor=actor(88, "hr.appraisal.review"), appraisal_id=row.pk, action=action
        )
    assert error.value.code == expected


def test_appraisal_finalization_requires_employee_record_and_forward_notifies_next():
    row = Appraisal.objects.create(
        employee_user_id=1001,
        period="2026",
        form_data={"x": 1},
        status=sm.PENDING_REVIEW,
        reviewer_user_ids=[88],
        current_reviewer_user_id=88,
    )
    with pytest.raises(ConflictError) as missing_employee:
        appraisals.review_appraisal(
            actor=actor(88, "hr.appraisal.review"), appraisal_id=row.pk, action="finalize"
        )
    assert missing_employee.value.code == "employee_record_required"

    employee(user_id=1002)
    route_row = Appraisal.objects.create(
        employee_user_id=1002,
        period="2026",
        form_data={"x": 1},
        status=sm.PENDING_REVIEW,
        reviewer_user_ids=[88, 99],
        current_reviewer_user_id=88,
    )
    result = appraisals.review_appraisal(
        actor=actor(88, "hr.appraisal.review"),
        appraisal_id=route_row.pk,
        action="forward",
    )
    assert result.status == sm.APPRAISAL_PENDING_NEXT
    assert result.current_reviewer_user_id == 99
    assert HRNotification.objects.filter(topic="appraisal.forwarded").exists()


def test_workflow_configuration_validation_and_upsert(monkeypatch):
    with pytest.raises(ConflictError) as invalid_type:
        configuration.save_workflow_route(
            actor=actor(7, "hr.workflow.manage"),
            employee_category="other",
            request_type="bad",
            steps=[{"approver_user_id": 88, "authority_label": "HOD"}],
        )
    assert invalid_type.value.code == "invalid_workflow_route"
    with pytest.raises(ConflictError) as invalid_delay:
        configuration.save_workflow_route(
            actor=actor(7, "hr.workflow.manage"),
            employee_category="staff",
            request_type="cpda_advance",
            steps=[{"approver_user_id": 88, "authority_label": "HOD"}],
            reminder_after_hours=0,
        )
    assert invalid_delay.value.code == "invalid_reminder_delay"
    install_directory(monkeypatch, {88: SimpleNamespace(kind="staff")})
    for steps, code in [
        ([], "workflow_route_empty"),
        (["not an object"], "invalid_workflow_route"),
        ([{}], "invalid_workflow_route"),
        ([{"approver_user_id": 0, "authority_label": "HOD"}], "invalid_workflow_route"),
        ([{"approver_user_id": 88, "authority_label": "  "}], "invalid_workflow_route"),
        (
            [
                {"approver_user_id": 88, "authority_label": "HOD"},
                {"approver_user_id": 88, "authority_label": "Registrar"},
            ],
            "duplicate_workflow_approver",
        ),
    ]:
        with pytest.raises(ConflictError) as error:
            configuration.save_workflow_route(
                actor=actor(7, "hr.workflow.manage"),
                employee_category="staff",
                request_type="cpda_advance",
                steps=steps,
            )
        assert error.value.code == code

    valid_steps = [{"approver_user_id": 88, "authority_label": "H" * 90}]
    first = configuration.save_workflow_route(
        actor=actor(7, "hr.workflow.manage"),
        employee_category="staff",
        request_type="cpda_advance",
        steps=valid_steps,
        reminder_after_hours=3,
    )
    assert len(first.steps[0]["authority_label"]) == 80
    first.steps = []
    first.save(update_fields=["steps"])
    with pytest.raises(NotFoundError):
        configuration.configured_route(employee_category="staff", request_type="cpda_advance")
    second = configuration.save_workflow_route(
        actor=actor(7, "hr.workflow.manage"),
        employee_category="staff",
        request_type="cpda_advance",
        steps=[{"approver_user_id": 88, "authority_label": "HOD"}],
    )
    assert first.pk == second.pk
    assert (
        configuration.configured_route(
            employee_category="staff", request_type="cpda_advance"
        ).steps[0]["authority_label"]
        == "HOD"
    )


def test_appraisal_window_configuration_validates_and_updates():
    now = timezone.now()
    with pytest.raises(ConflictError) as invalid:
        configuration.save_appraisal_window(
            actor=actor(7, "hr.workflow.manage"), period=" ", opens_at=now, closes_at=now
        )
    assert invalid.value.code == "invalid_appraisal_window"
    first = configuration.save_appraisal_window(
        actor=actor(7, "hr.workflow.manage"),
        period="  2026  ",
        opens_at=now,
        closes_at=now + timedelta(days=30),
    )
    updated = configuration.save_appraisal_window(
        actor=actor(7, "hr.workflow.manage"),
        period="2026",
        opens_at=now,
        closes_at=now + timedelta(days=60),
        is_active=False,
    )
    assert first.pk == updated.pk
    assert not updated.is_active


def test_notification_deduplication_and_required_fields():
    from modules.hr.services.notifications import enqueue

    with pytest.raises(ValueError):
        enqueue(recipient_user_id=0, topic="notice", dedupe_key="x", subject="s", body="b")
    saved = enqueue(
        recipient_user_id=1001,
        topic="notice",
        dedupe_key="one",
        subject="s",
        body="b",
    )
    assert saved is not None
    assert (
        enqueue(
            recipient_user_id=1001,
            topic="notice",
            dedupe_key="one",
            subject="s",
            body="b",
        )
        is None
    )


def test_notice_publication_deduplicates_recipients_and_audits(monkeypatch):
    from modules.hr.services import notifications

    employee()
    monkeypatch.setattr(
        notifications.directory,
        "get_users",
        lambda ids: {uid: SimpleNamespace(kind="staff") for uid in ids},
    )
    rows = notifications.publish_notice(
        actor=actor(7, "hr.notification.manage"),
        recipient_user_ids=[1001, 1001],
        subject="Holiday schedule",
        body="Please review the schedule.",
    )
    assert len(rows) == 1
    assert rows[0].recipient_user_id == 1001
    assert AuditEvent.objects.filter(action="notice.published").count() == 1


@pytest.mark.parametrize("user_ids", [[], [0]])
def test_notice_publication_rejects_empty_or_invalid_recipients(user_ids):
    from modules.hr.services import notifications

    with pytest.raises(ConflictError) as error:
        notifications.publish_notice(
            actor=actor(7, "hr.notification.manage"),
            recipient_user_ids=user_ids,
            subject="Notice",
            body="Body",
        )
    assert error.value.code == "notice_recipients_required"


def test_notice_publication_requires_employee_identity_and_record(monkeypatch):
    from modules.hr.services import notifications

    monkeypatch.setattr(
        notifications.directory,
        "get_users",
        lambda ids: {uid: SimpleNamespace(kind="student") for uid in ids},
    )
    with pytest.raises(ConflictError) as error:
        notifications.publish_notice(
            actor=actor(7, "hr.notification.manage"),
            recipient_user_ids=[1001],
            subject="Notice",
            body="Body",
        )
    assert error.value.code == "invalid_notice_recipient"


def test_notice_publication_rolls_back_when_enqueue_dedupes_to_none(monkeypatch):
    from modules.hr.services import notifications

    employee()
    monkeypatch.setattr(
        notifications.directory,
        "get_users",
        lambda ids: {uid: SimpleNamespace(kind="staff") for uid in ids},
    )
    monkeypatch.setattr(notifications, "enqueue", lambda **kwargs: None)
    with pytest.raises(ConflictError) as error:
        notifications.publish_notice(
            actor=actor(7, "hr.notification.manage"),
            recipient_user_ids=[1001],
            subject="Notice",
            body="Body",
        )
    assert error.value.code == "notice_publish_failed"
    assert not AuditEvent.objects.filter(action="notice.published").exists()


@pytest.mark.parametrize(
    ("leave_type", "amount"),
    [("unlisted", Decimal("2")), ("casual", Decimal("-0.01"))],
)
def test_leave_balance_configuration_rejects_unsupported_or_negative_values(leave_type, amount):
    with pytest.raises(ConflictError) as error:
        leaves.set_leave_balance(
            actor=actor(7, "hr.leave_balance.manage"),
            employee_user_id=1001,
            leave_type=leave_type,
            available_days=amount,
            is_eligible=True,
        )
    assert error.value.code == "invalid_leave_balance"


def test_leave_balance_configuration_requires_employee_and_handles_noop_and_adjustment():
    with pytest.raises(NotFoundError):
        leaves.set_leave_balance(
            actor=actor(7, "hr.leave_balance.manage"),
            employee_user_id=1001,
            leave_type="casual",
            available_days=Decimal("4"),
            is_eligible=True,
        )
    record = employee()
    balance = leaves.set_leave_balance(
        actor=actor(7, "hr.leave_balance.manage"),
        employee_user_id=record.user_id,
        leave_type="casual",
        available_days=Decimal("4"),
        is_eligible=True,
    )
    initial_entries = LeaveLedgerEntry.objects.filter(balance=balance).count()
    unchanged = leaves.set_leave_balance(
        actor=actor(8, "hr.leave_balance.manage"),
        employee_user_id=record.user_id,
        leave_type="casual",
        available_days=Decimal("4"),
        is_eligible=True,
    )
    assert unchanged.pk == balance.pk
    assert LeaveLedgerEntry.objects.filter(balance=balance).count() == initial_entries
    adjusted = leaves.set_leave_balance(
        actor=actor(8, "hr.leave_balance.manage"),
        employee_user_id=record.user_id,
        leave_type="casual",
        available_days=Decimal("4"),
        is_eligible=False,
    )
    assert not adjusted.is_eligible
    assert LeaveLedgerEntry.objects.filter(balance=balance).count() == initial_entries + 1
    assert AuditEvent.objects.filter(action="leave.balance_adjusted").exists()


def test_leave_balance_configuration_converts_unique_race_to_conflict(monkeypatch):
    from modules.hr.services import leaves as leave_service

    employee()

    def conflicting_create(**kwargs):
        from django.db import IntegrityError

        raise IntegrityError("unique constraint race")

    monkeypatch.setattr(LeaveBalance.objects, "create", conflicting_create)
    with pytest.raises(ConflictError) as error:
        leave_service.set_leave_balance(
            actor=actor(7, "hr.leave_balance.manage"),
            employee_user_id=1001,
            leave_type="casual",
            available_days=Decimal("4"),
            is_eligible=True,
        )
    assert error.value.code == "leave_balance_conflict"


@pytest.mark.parametrize(
    ("leave_type", "duration", "justification", "expected"),
    [
        ("other", Decimal("1"), "Family", "unsupported_leave_type"),
        ("casual", Decimal("0"), "Family", "leave_fields_required"),
        ("casual", Decimal("1"), "   ", "leave_fields_required"),
    ],
)
def test_leave_submission_validates_type_duration_and_justification(
    leave_type, duration, justification, expected
):
    with pytest.raises(ConflictError) as error:
        leaves.submit_leave_request(
            actor=actor(1001, "hr.leave.create"),
            leave_type=leave_type,
            duration_days=duration,
            justification=justification,
        )
    assert error.value.code == expected


def test_leave_submission_requires_employee_service_record():
    with pytest.raises(ConflictError) as error:
        leaves.submit_leave_request(
            actor=actor(1001, "hr.leave.create"),
            leave_type="casual",
            duration_days=Decimal("1"),
            justification="Family",
        )
    assert error.value.code == "employee_record_required"


def test_leave_submission_requires_balance_and_supported_route():
    record = employee()
    args = {
        "actor": actor(1001, "hr.leave.create"),
        "leave_type": "casual",
        "duration_days": Decimal("1"),
        "justification": "Family",
    }
    with pytest.raises(ConflictError) as no_balance:
        leaves.submit_leave_request(**args)
    assert no_balance.value.code == "leave_balance_unavailable"
    LeaveBalance.objects.create(
        employee=record,
        leave_type="casual",
        available_days=Decimal("4"),
        is_eligible=True,
        updated_by_user_id=7,
    )
    with pytest.raises(ConflictError) as no_route:
        leaves.submit_leave_request(**args)
    assert no_route.value.code == "leave_route_unavailable"
    WorkflowRoute.objects.create(
        employee_category="staff",
        request_type="leave_casual",
        steps=[{"approver_user_id": 88}] * 3,
        updated_by_user_id=7,
    )
    with pytest.raises(ConflictError) as invalid_route:
        leaves.submit_leave_request(**args)
    assert invalid_route.value.code == "leave_route_unavailable"


def test_leave_decision_rejects_missing_wrong_actor_and_unknown_transition():
    with pytest.raises(NotFoundError):
        leaves.decide_leave_request(
            actor=actor(88, "hr.leave.approve"), request_id=999, action="approve"
        )
    record = employee()
    request = leave_row(record)
    for user_id in (77, 1001):
        with pytest.raises(NotFoundError):
            leaves.decide_leave_request(
                actor=actor(user_id, "hr.leave.approve"), request_id=request.pk, action="approve"
            )
    with pytest.raises(ConflictError) as invalid_action:
        leaves.decide_leave_request(
            actor=actor(88, "hr.leave.approve"), request_id=request.pk, action="withdraw"
        )
    assert invalid_action.value.code == "invalid_transition"


@pytest.mark.parametrize(
    ("balance_exists", "eligible", "days", "expected"),
    [
        (False, True, Decimal("4"), "leave_not_eligible"),
        (True, False, Decimal("4"), "leave_not_eligible"),
        (True, True, Decimal("0.5"), "leave_balance_insufficient"),
    ],
)
def test_leave_approval_revalidates_balance_and_eligibility(
    balance_exists, eligible, days, expected
):
    record = employee()
    request = leave_row(record)
    if balance_exists:
        LeaveBalance.objects.create(
            employee=record,
            leave_type="casual",
            available_days=days,
            is_eligible=eligible,
            updated_by_user_id=7,
        )
    with pytest.raises(ConflictError) as error:
        leaves.decide_leave_request(
            actor=actor(88, "hr.leave.approve"), request_id=request.pk, action="approve"
        )
    assert error.value.code == expected
    request.refresh_from_db()
    assert request.status == "pending_authority"


def test_leave_balance_and_ledger_models_keep_audit_records_immutable():
    record = employee()
    balance = LeaveBalance.objects.create(
        employee=record,
        leave_type="casual",
        available_days=Decimal("4"),
        is_eligible=True,
        updated_by_user_id=7,
    )
    entry = LeaveLedgerEntry.objects.create(
        balance=balance,
        entry_type="balance_configured",
        amount_delta=Decimal("4"),
        actor_user_id=7,
    )
    assert str(entry) == f"balance_configured {entry.amount_delta} for balance {balance.pk}"
    with pytest.raises(TypeError):
        entry.save()
    with pytest.raises(TypeError):
        LeaveLedgerEntry.objects.filter(pk=entry.pk).delete()

    event = AuditEvent.objects.create(
        entity_type="employee", entity_id=record.pk, actor_user_id=7, action="created"
    )
    with pytest.raises(TypeError):
        event.save()
    with pytest.raises(TypeError):
        event.delete()
    with pytest.raises(TypeError):
        AuditEvent.objects.filter(pk=event.pk).update(action="changed")
    with pytest.raises(TypeError):
        AuditEvent.objects.filter(pk=event.pk).delete()
