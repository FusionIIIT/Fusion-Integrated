"""Builder-owned HTTP journeys exercising HR-EIS use cases and workflow outcomes."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.hreis.models import (
    AppraisalDetail,
    AuditEvent,
    EmployeeServiceRecord,
    HRPolicyVersion,
    HRRequest,
    HRRequestTransition,
    LeaveLedgerEntry,
    Notification,
    OutboxEvent,
)

pytestmark = pytest.mark.django_db
API = "/api/v1/hreis"


def actor_client(stub_iam, *, user_id, role, permissions, kind="faculty", users=None):
    stub_iam(
        make_session(
            user_id=user_id,
            active_role=role,
            roles=(role,),
            kind=kind,
            permissions=permissions,
            modules=("hreis",),
        ),
        users=users or {},
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token synthetic-test-token")
    return client


def service_record():
    return EmployeeServiceRecord.objects.create(
        user_id=10,
        appointment_details={"date": "2026-01-01"},
        department="CSE",
        designation_snapshot="Professor",
        service_history=[],
    )


def policy(family, *, authorities=("HOD (CSE)", "Registrar"), extra=None):
    now = timezone.now()
    parameters = {
        "routes": [
            {
                "employee_kind": "faculty",
                "department": "CSE",
                "authorities": list(authorities),
            }
        ],
    }
    parameters.update(extra or {})
    return HRPolicyVersion.objects.create(
        family=family,
        version=1,
        effective_from=now - timedelta(days=1),
        effective_until=now + timedelta(days=1),
        parameters=parameters,
        approved_by_user_id=99,
        approved_designation="hradmin",
    )


def send(client, path, payload, key):
    return client.post(
        API + path,
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
    )


def test_hr_uc_003_004_005_cw_hr_01_leave_approval_with_ledger_and_audit(stub_iam):
    # HR-UC-003, HR-UC-004, HR-UC-005, BR-HR-010, CW-HR-01, BW-HR-03.
    service_record()
    p = policy(
        "leave",
        extra={"eligibility": {"faculty": {"Casual": True}}},
    )
    LeaveLedgerEntry.objects.create(
        user_id=10,
        leave_type="Casual",
        quantity=Decimal("5"),
        event_key="opening-balance",
        policy_version=p,
    )
    employee = actor_client(
        stub_iam, user_id=10, role="faculty",
        permissions=("hreis.leave.create", "hreis.request.view", "hreis.notification.view"),
    )
    submitted = send(
        employee,
        "/requests/leave/",
        {"leave_type": "Casual", "duration": "2", "justification": "Family"},
        "journey-leave-submit",
    )
    assert submitted.status_code == 201, submitted.content
    request_id = submitted.json()["id"]
    assert submitted.json()["state"] == "pending_authority"
    assert submitted.json()["route_total_steps"] == 2
    assert LeaveLedgerEntry.objects.count() == 1

    wrong = actor_client(
        stub_iam, user_id=202, role="Registrar", kind="staff",
        permissions=("hreis.leave.approve",),
    )
    premature = send(
        wrong, f"/requests/{request_id}/decision/",
        {"event": "approve"}, "journey-premature",
    )
    assert premature.status_code == 404
    first = actor_client(
        stub_iam, user_id=201, role="HOD (CSE)",
        permissions=("hreis.leave.approve", "hreis.request.view"),
    )
    forwarded = send(
        first, f"/requests/{request_id}/decision/",
        {"event": "forward"}, "journey-leave-forward",
    )
    assert forwarded.status_code == 200, forwarded.content
    assert forwarded.json()["route_step"] == 1
    assert forwarded.json()["route_total_steps"] == 2
    decision = send(
        actor_client(
            stub_iam, user_id=202, role="Registrar", kind="staff",
            permissions=("hreis.leave.approve",),
        ),
        f"/requests/{request_id}/decision/",
        {"event": "approve"}, "journey-leave-approve",
    )
    assert decision.status_code == 200, decision.content
    assert decision.json()["state"] == "approved"
    assert sum(LeaveLedgerEntry.objects.filter(user_id=10).values_list("quantity", flat=True)) == Decimal("3")
    assert HRRequestTransition.objects.filter(request_id=request_id).count() == 3
    assert OutboxEvent.objects.filter(
        payload__request_id=request_id, event_type="hreis.notification"
    ).count() == 3
    assert AuditEvent.objects.filter(resource_id=request_id, resource_kind="hr_request").count() == 3

    owner = actor_client(
        stub_iam, user_id=10, role="faculty",
        permissions=("hreis.request.view", "hreis.notification.view"),
    )
    request_list = owner.get(API + "/requests/")
    assert request_list.status_code == 200
    assert [(r["id"], r["state"]) for r in request_list.json()["results"]] == [(request_id, "approved")]
    detail = owner.get(API + f"/requests/{request_id}/")
    assert detail.status_code == 200
    assert [event["event"] for event in detail.json()["history"]] == ["submit", "forward", "approve"]
    assert detail.json()["history"][-1]["acting_designation"] == "Registrar"
    foreign = actor_client(
        stub_iam, user_id=20, role="faculty", permissions=("hreis.request.view",),
    )
    assert foreign.get(API + f"/requests/{request_id}/").status_code == 404
    owner = actor_client(
        stub_iam, user_id=10, role="faculty", permissions=("hreis.notification.view",),
    )
    notes = owner.get(API + "/notifications/")
    assert notes.status_code == 200
    # HR-AFR-078: submission, forwarding and approval each generated an
    # owner notification, not merely a status change in the database.
    assert len(notes.json()["results"]) == 3


def test_hr_uc_004_bw_hr_02_rejection_has_no_ledger_debit(stub_iam):
    # HR-UC-004 Alternative A1, BW-HR-02, BR-HR-011.
    service_record()
    p = policy(
        "leave",
        authorities=("Registrar",),
        extra={"eligibility": {"faculty": {"Casual": True}}},
    )
    LeaveLedgerEntry.objects.create(
        user_id=10,
        leave_type="Casual",
        quantity=Decimal("3"),
        event_key="balance-reject",
        policy_version=p,
    )
    user = actor_client(
        stub_iam, user_id=10, role="faculty",
        permissions=("hreis.leave.create",),
    )
    submitted = send(
        user, "/requests/leave/",
        {"leave_type": "Casual", "duration": "1", "justification": "Urgent"},
        "journey-reject-submit",
    )
    assert submitted.status_code == 201, submitted.content
    request_id = submitted.json()["id"]
    approver = actor_client(
        stub_iam, user_id=202, role="Registrar", kind="staff",
        permissions=("hreis.leave.approve",),
    )
    blank = send(
        approver, f"/requests/{request_id}/decision/",
        {"event": "reject", "reason": ""}, "journey-reject-empty",
    )
    assert blank.status_code == 400
    rejected = send(
        approver, f"/requests/{request_id}/decision/",
        {"event": "reject", "reason": "Incomplete documentation"}, "journey-reject-final",
    )
    assert rejected.status_code == 200, rejected.content
    assert rejected.json()["state"] == "rejected"
    replay = send(
        approver, f"/requests/{request_id}/decision/",
        {"event": "approve"}, "journey-reject-reapproval",
    )
    assert replay.status_code == 404
    assert LeaveLedgerEntry.objects.count() == 1
    assert sum(LeaveLedgerEntry.objects.values_list("quantity", flat=True)) == Decimal("3")


@pytest.mark.parametrize(
    "family,subtype,payload",
    [
        ("ltc", "advance", {"prescribed_form_reference": "official-ltc-form"}),
        ("ltc", "reimbursement", {"prescribed_form_reference": "official-ltc-reimbursement-form"}),
        ("cpda", "advance", {
            "purpose": "Professional training",
            "amount": "450.00",
            "document_references": ["training-agenda", "registration-confirmation"],
        }),
        (
            "cpda",
            "reimbursement",
            {
                "purpose": "Conference attendance",
                "amount": "1500.00",
                "document_references": ["travel-receipt", "registration-receipt"],
            },
        ),
    ],
)
def test_hr_uc_009_010_011_013_014_015_claim_verified_then_approved(
    stub_iam, user_ref, family, subtype, payload
):
    # HR-CFR-009, HR-CFR-010, HR-UC-009, HR-UC-010, HR-UC-011,
    # HR-UC-013, HR-UC-014, HR-UC-015, CW-HR-03, CW-HR-04,
    # HR-AFR-050, HR-AFR-051, HR-AFR-052, HR-AFR-053, HR-AFR-054,
    # HR-AFR-060, HR-AFR-061, HR-AFR-062, HR-AFR-063, HR-AFR-064,
    # HR-AFR-065, HR-AFR-066, BR-HR-016, BR-HR-017, BR-HR-018,
    # BR-HR-020, BR-HR-021: each subtype verifies and enters approval.
    # No financial settlement is fabricated by the approval action.
    service_record()
    policy(family, authorities=("Registrar",))
    users = {10: user_ref(10, "Employee Ten", kind="faculty")}
    submitter = actor_client(
        stub_iam, user_id=10, role="faculty",
        permissions=("hreis.claim.create", "hreis.request.view"),
        users=users,
    )
    created = send(
        submitter, "/requests/claims/",
        {"family": family, "subtype": subtype, **payload},
        f"journey-{family}-submit",
    )
    assert created.status_code == 201, created.content
    request_id = created.json()["id"]
    assert created.json()["state"] == "awaiting_hr_verification"
    assert created.json()["claim_summary"]["hr_verified"] is False
    reviewer = actor_client(
        stub_iam, user_id=99, role="hradmin", kind="staff",
        permissions=("hreis.claim.review",), users=users,
    )
    verified = send(
        reviewer, f"/requests/{request_id}/verify-claim/",
        {
            "document_review_reference": "review-confirmation-1",
            "eligibility_basis": "Institutional eligibility review",
        },
        f"journey-{family}-verify",
    )
    assert verified.status_code == 200, verified.content
    assert verified.json()["state"] == "pending_authority"
    assert verified.json()["claim_summary"]["hr_verified"] is True
    decided = send(
        actor_client(
            stub_iam, user_id=202, role="Registrar", kind="staff",
            permissions=("hreis.claim.approve",), users=users,
        ),
        f"/requests/{request_id}/decision/",
        {"event": "approve"}, f"journey-{family}-approve",
    )
    assert decided.status_code == 200, decided.content
    assert decided.json()["state"] == "approved"
    claim = HRRequest.objects.get(pk=request_id).claim
    assert claim.hr_verified_by_user_id == 99
    assert claim.financial_verified_by_user_id is None
    assert HRRequestTransition.objects.filter(request_id=request_id).count() == 3


def test_hr_uc_006_007_008_cw_hr_02_appraisal_review_is_assigned_and_archived(
    stub_iam, user_ref
):
    # HR-CFR-008, HR-UC-006, HR-UC-007, HR-UC-008,
    # HR-AFR-044, HR-AFR-045, HR-AFR-046, HR-AFR-047,
    # HR-AFR-048, HR-AFR-049, BR-HR-013, BR-HR-014, BR-HR-015,
    # CW-HR-02: reviewer assignment, scoped decision, immutable archive.
    service_record()
    now = timezone.now()
    policy(
        "appraisal",
        extra={
            "submission_window": {
                "start": (now - timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=1)).isoformat(),
            },
        },
    )
    users = {
        10: user_ref(10, "Employee Ten", kind="faculty"),
        201: user_ref(201, "Designated Reviewer", kind="faculty"),
        203: user_ref(203, "Unassigned Reviewer", kind="faculty"),
    }
    owner = actor_client(
        stub_iam, user_id=10, role="faculty",
        permissions=("hreis.appraisal.create", "hreis.service_record.view"),
        users=users,
    )
    created = send(
        owner, "/requests/appraisals/",
        {"period_key": "FY2026", "submitted_form": {"summary": "Teaching and research"}},
        "journey-appraisal-submit",
    )
    assert created.status_code == 201, created.content
    request_id = created.json()["id"]
    assert created.json()["state"] == "submitted"
    assert created.json()["appraisal_summary"]["submitted_form"] == {
        "summary": "Teaching and research"
    }
    admin = actor_client(
        stub_iam, user_id=99, role="hradmin", kind="staff",
        permissions=("hreis.appraisal.assign",), users=users,
    )
    assigned = send(
        admin, f"/requests/{request_id}/assign-reviewers/",
        {"reviewer_user_ids": [201]}, "journey-appraisal-assign",
    )
    assert assigned.status_code == 200, assigned.content
    assert assigned.json()["state"] == "pending_review"

    unassigned = actor_client(
        stub_iam, user_id=203, role="HOD (CSE)",
        permissions=("hreis.appraisal.approve", "hreis.request.view"), users=users,
    )
    queue = unassigned.get(API + "/requests/")
    assert queue.status_code == 200
    assert not queue.json()["results"]
    assert unassigned.get(API + f"/requests/{request_id}/").status_code == 404
    forbidden = send(
        unassigned, f"/requests/{request_id}/appraisal-decision/",
        {"event": "forward"}, "journey-unassigned-reviewer",
    )
    assert forbidden.status_code == 404

    actual = actor_client(
        stub_iam, user_id=201, role="HOD (CSE)",
        permissions=("hreis.appraisal.approve", "hreis.request.view"), users=users,
    )
    scoped_rows = actual.get(API + "/requests/").json()["results"]
    assert [r["id"] for r in scoped_rows] == [request_id]
    assert scoped_rows[0]["appraisal_summary"]["submitted_form"] == {
        "summary": "Teaching and research"
    }
    detail = actual.get(API + f"/requests/{request_id}/")
    assert detail.status_code == 200
    assert detail.json()["appraisal_summary"]["reviewer_user_ids"] == [201]
    forwarded = send(
        actual, f"/requests/{request_id}/appraisal-decision/",
        {"event": "forward"}, "journey-appraisal-forward",
    )
    assert forwarded.status_code == 200, forwarded.content
    assert forwarded.json()["state"] == "pending_next_appraisal_authority"
    final = send(
        actor_client(
            stub_iam, user_id=202, role="Registrar", kind="staff",
            permissions=("hreis.appraisal.approve",), users=users,
        ),
        f"/requests/{request_id}/appraisal-decision/",
        {"event": "finalize"}, "journey-appraisal-final",
    )
    assert final.status_code == 200, final.content
    assert final.json()["state"] == "finalized"
    assert AppraisalDetail.objects.get(request_id=request_id).finalized_at is not None
    owner = actor_client(
        stub_iam, user_id=10, role="faculty",
        permissions=("hreis.service_record.view",),
        users=users,
    )
    record = owner.get(API + "/service-records/me/")
    assert record.status_code == 200
    archive = record.json()["service_history"][-1]
    assert archive["kind"] == "appraisal"
    assert archive["request_id"] == request_id
    assert archive["period_key"] == "FY2026"


def test_hr_uc_001_002_service_record_empty_edit_and_missing_self_are_refused(
    stub_iam, user_ref
):
    # HR-UC-001/002, BR-HR-003/005/006, HR-AFR-028.
    record = service_record()
    missing_owner = actor_client(
        stub_iam, user_id=20, role="faculty",
        permissions=("hreis.service_record.view",),
    )
    assert missing_owner.get(API + "/service-records/me/").status_code == 404
    assert missing_owner.get(API + f"/service-records/{record.pk}/").status_code == 404
    administrator = actor_client(
        stub_iam, user_id=99, role="hradmin", kind="staff",
        permissions=("hreis.service_record.update", "hreis.service_record.view"),
        users={10: user_ref(10, "Employee Ten", kind="faculty")},
    )
    assert administrator.get(API + f"/service-records/{record.pk}/").status_code == 200
    assert administrator.get(API + "/service-records/99999/").status_code == 404
    no_changes = administrator.patch(
        API + f"/service-records/{record.pk}/",
        {"expected_revision": 0},
        format="json",
        HTTP_IDEMPOTENCY_KEY="journey-empty-update",
    )
    assert no_changes.status_code == 400
    record.refresh_from_db()
    assert record.revision == 0
    assert not AuditEvent.objects.exists()
    assert not Notification.objects.exists()

def test_hr_uc_006_appraisal_closed_window_and_invalid_form_never_create_request(stub_iam):
    # HR-UC-006, BR-HR-012: submissions outside the configured window are refused.
    service_record()
    now = timezone.now()
    policy(
        "appraisal",
        extra={
            "submission_window": {
                "start": (now - timedelta(days=3)).isoformat(),
                "end": (now - timedelta(days=1)).isoformat(),
            }
        },
    )
    c = actor_client(
        stub_iam, user_id=10, role="faculty",
        permissions=("hreis.appraisal.create",),
    )
    invalid_shape = send(c, "/requests/appraisals/", [], "journey-appraisal-invalid-shape")
    assert invalid_shape.status_code == 400
    closed = send(
        c, "/requests/appraisals/",
        {"period_key": "FY2026", "submitted_form": {"summary": "Teaching"}},
        "journey-appraisal-closed-window",
    )
    assert closed.status_code == 409
    assert not HRRequest.objects.exists()
    assert not AuditEvent.objects.exists()


def test_hr_uc_003_employee_without_record_cannot_submit_leave(stub_iam):
    # HR-UC-003 precondition: a person with no HR-EIS service record cannot create a request.
    c = actor_client(
        stub_iam, user_id=10, role="faculty",
        permissions=("hreis.leave.create",),
    )
    response = send(
        c, "/requests/leave/",
        {"leave_type": "Casual", "duration": "1", "justification": "Family"},
        "journey-leave-no-record",
    )
    assert response.status_code == 404
    assert not HRRequest.objects.exists()


def test_hr_afr_024_service_record_includes_verified_leave_balances(stub_iam):
    # HR-AFR-024, HR-CFR-006/007: ledger-derived balances are read-only.
    service_record()
    p = policy("leave", extra={"eligibility": {"faculty": {"Casual": True}}})
    LeaveLedgerEntry.objects.create(
        user_id=10, leave_type="Casual", quantity=Decimal("5"),
        policy_version=p, event_key="opening-casual",
    )
    LeaveLedgerEntry.objects.create(
        user_id=10, leave_type="Casual", quantity=Decimal("-2"),
        policy_version=p, event_key="debit-casual",
    )
    LeaveLedgerEntry.objects.create(
        user_id=10, leave_type="Medical", quantity=Decimal("1.5"),
        policy_version=p, event_key="opening-medical",
    )
    LeaveLedgerEntry.objects.create(
        user_id=20, leave_type="Casual", quantity=Decimal("50"),
        policy_version=p, event_key="foreign-balance",
    )
    owner = actor_client(
        stub_iam, user_id=10, role="faculty",
        permissions=("hreis.service_record.view",),
    )
    response = owner.get(API + "/service-records/me/")
    assert response.status_code == 200, response.content
    balances = response.json()["leave_balances"]
    assert Decimal(balances["Casual"]) == Decimal("3")
    assert Decimal(balances["Medical"]) == Decimal("1.5")
    assert Decimal(balances["Casual"]) != Decimal("50")


@pytest.mark.parametrize("family", ["ltc", "cpda"])
def test_claim_rejection_and_single_forward_follow_frozen_route(stub_iam, user_ref, family):
    # BW-HR-08, BW-HR-09, BW-HR-12, BW-HR-13,
    # HR-AFR-058, BR-HR-018, BR-HR-021, BR-HR-023:
    # after HR verification, rejection closes the claim without finance,
    # while exactly one forward reaches the final configured authority.
    service_record()
    policy(family, authorities=("HOD (CSE)", "Registrar"))
    users = {10: user_ref(10, "Employee Ten", kind="faculty")}
    claim_fields = (
        {"family": "ltc", "subtype": "advance",
         "prescribed_form_reference": "registered-ltc-form"}
        if family == "ltc"
        else {"family": "cpda", "subtype": "advance",
              "purpose": "Academic training", "amount": "350.00",
              "document_references": ["verified-agenda"]}
    )

    def submitted_and_hr_verified(suffix):
        employee = actor_client(
            stub_iam, user_id=10, role="faculty",
            permissions=("hreis.claim.create",), users=users,
        )
        result = send(
            employee, "/requests/claims/", claim_fields, f"{family}-{suffix}-submit",
        )
        assert result.status_code == 201, result.content
        request_id = result.json()["id"]
        hradmin = actor_client(
            stub_iam, user_id=99, role="hradmin", kind="staff",
            permissions=("hreis.claim.review",), users=users,
        )
        checked = send(
            hradmin, f"/requests/{request_id}/verify-claim/",
            {
                "document_review_reference": f"reviewed-{suffix}",
                "eligibility_basis": "Human HR eligibility verification",
            },
            f"{family}-{suffix}-hr",
        )
        assert checked.status_code == 200, checked.content
        assert checked.json()["state"] == "pending_authority"
        return request_id

    rejected_id = submitted_and_hr_verified("reject")
    hod = actor_client(
        stub_iam, user_id=201, role="HOD (CSE)",
        permissions=("hreis.claim.approve",),
    )
    rejected = send(
        hod, f"/requests/{rejected_id}/decision/",
        {"event": "reject", "reason": "Insufficient signed evidence"},
        f"{family}-reject-decision",
    )
    assert rejected.status_code == 200, rejected.content
    assert rejected.json()["state"] == "rejected"
    assert HRRequestTransition.objects.filter(request_id=rejected_id).count() == 3
    assert HRRequest.objects.get(pk=rejected_id).claim.financial_verified_by_user_id is None
    assert AuditEvent.objects.filter(
        resource_kind="hr_request", resource_id=rejected_id
    ).count() == 3
    # A terminal rejection cannot be reapproved by a later route authority.
    registrar = actor_client(
        stub_iam, user_id=202, role="Registrar", kind="staff",
        permissions=("hreis.claim.approve",),
    )
    assert send(
        registrar, f"/requests/{rejected_id}/decision/",
        {"event": "approve"}, f"{family}-reject-bypass",
    ).status_code == 404

    forward_id = submitted_and_hr_verified("forward")
    hod = actor_client(
        stub_iam, user_id=201, role="HOD (CSE)",
        permissions=("hreis.claim.approve",),
    )
    forwarded = send(
        hod, f"/requests/{forward_id}/decision/",
        {"event": "forward"}, f"{family}-forward-step",
    )
    assert forwarded.status_code == 200, forwarded.content
    assert forwarded.json()["state"] == "pending_authority"
    assert forwarded.json()["route_step"] == 1
    assert forwarded.json()["route_total_steps"] == 2
    registrar = actor_client(
        stub_iam, user_id=202, role="Registrar", kind="staff",
        permissions=("hreis.claim.approve",),
    )
    final = send(
        registrar, f"/requests/{forward_id}/decision/",
        {"event": "approve"}, f"{family}-forward-final",
    )
    assert final.status_code == 200, final.content
    assert final.json()["state"] == "approved"
    assert HRRequestTransition.objects.filter(request_id=forward_id).count() == 4
    assert HRRequest.objects.get(pk=forward_id).claim.financial_verified_by_user_id is None
