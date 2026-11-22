"""HTTP-level role gates, explicit fields and 404 row isolation."""

import pytest
from rest_framework.test import APIClient

from modules.hreis.models import EmployeeServiceRecord
from modules.hreis.tests.actors import make_session

pytestmark = pytest.mark.django_db


def _client(
    stub_iam,
    *,
    user_id=10,
    active_role="faculty",
    kind="faculty",
    permissions=(),
    modules=("hreis",),
    users=None,
):
    stub_iam(
        make_session(
            user_id=user_id,
            kind=kind,
            active_role=active_role,
            roles=(active_role,),
            permissions=permissions,
            modules=modules,
        ),
        users=users or {},
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token synthetic-test-token")
    return client


@pytest.fixture
def record():
    return EmployeeServiceRecord.objects.create(
        user_id=10,
        appointment_details={"date": "2026-01-01"},
        department="CSE",
        designation_snapshot="Professor",
    )


def test_employee_only_reads_own_record_over_http(stub_iam, record):
    # HR-AFR-003, HR-AFR-099, HR-AFR-100, BR-HR-004:
    # the authenticated employee sees only the own official service record.
    EmployeeServiceRecord.objects.create(
        user_id=20,
        appointment_details={},
        department="ME",
        designation_snapshot="Professor",
    )
    c = _client(stub_iam, permissions=("hreis.service_record.view",))
    own = c.get("/api/v1/hreis/service-records/me/")
    assert own.status_code == 200
    assert own.json()["user_id"] == 10
    rows = c.get("/api/v1/hreis/service-records/").json()["results"]
    assert [r["user_id"] for r in rows] == [10]
    foreign = c.get("/api/v1/hreis/service-records/2/")
    missing = c.get("/api/v1/hreis/service-records/99999/")
    assert foreign.status_code == missing.status_code == 404


def test_both_module_grant_and_permission_required(stub_iam, record):
    # HR-AFR-001, HR-AFR-094, HR-AFR-100, BR-HR-002:
    # both independent transport authorization checks must succeed.
    c = _client(stub_iam, modules=(), permissions=("hreis.service_record.view",))
    assert c.get("/api/v1/hreis/service-records/me/").status_code == 403
    c = _client(stub_iam, permissions=())
    assert c.get("/api/v1/hreis/service-records/me/").status_code == 403


@pytest.mark.parametrize("field,value", [("employee_kind", []), ("department", {})])
def test_policy_route_non_scalar_scope_is_400_without_writes(stub_iam, field, value):
    # HR-UC-017: malformed workflow settings must be refused atomically.
    from datetime import timedelta

    from django.utils import timezone

    from modules.hreis.models import AuditEvent, HRPolicyVersion

    client = _client(
        stub_iam,
        user_id=99,
        active_role="hradmin",
        kind="staff",
        permissions=("hreis.policy.manage",),
    )
    route = {"employee_kind": "staff", "department": "CSE", "authorities": ["Registrar"]}
    route[field] = value
    response = client.post(
        "/api/v1/hreis/policies/",
        {
            "family": "leave",
            "version": 1,
            "effective_from": (timezone.now() - timedelta(hours=1)).isoformat(),
            "parameters": {"routes": [route]},
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY=f"bad-scope-{field}",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_routes"
    assert not HRPolicyVersion.objects.exists()
    assert not AuditEvent.objects.exists()


@pytest.mark.parametrize("version,status", [(2147483647, 201), (2147483648, 400), (10**100, 400)])
def test_policy_version_storage_boundaries_are_validated_before_database_write(
    stub_iam, version, status
):
    # HR-UC-017: a valid API body must never overflow the PostgreSQL integer field.
    from datetime import timedelta

    from django.utils import timezone

    from modules.hreis.models import AuditEvent, HRPolicyVersion

    client = _client(
        stub_iam,
        user_id=99,
        active_role="hradmin",
        kind="staff",
        permissions=("hreis.policy.manage",),
    )
    response = client.post(
        "/api/v1/hreis/policies/",
        {
            "family": "leave",
            "version": version,
            "effective_from": (timezone.now() - timedelta(hours=1)).isoformat(),
            "parameters": {
                "routes": [
                    {
                        "employee_kind": "staff",
                        "department": "CSE",
                        "authorities": ["Registrar"],
                    }
                ]
            },
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="policy-storage-boundary",
    )
    assert response.status_code == status
    assert HRPolicyVersion.objects.count() == AuditEvent.objects.count() == int(status == 201)


@pytest.mark.parametrize(
    "module,permission,status", [(False, True, 403), (True, False, 403), (True, True, 200)]
)
@pytest.mark.parametrize("endpoint", ["audit/", "compliance/requests/"])
def test_audit_and_compliance_require_both_independent_transport_gates(
    stub_iam, module, permission, status, endpoint
):
    # HR-UC-018 / BR-HR-030: even a matching HR role does not replace either grant.
    client = _client(
        stub_iam,
        user_id=99,
        active_role="hradmin",
        kind="staff",
        modules=("hreis",) if module else (),
        permissions=("hreis.audit.view",) if permission else (),
    )
    assert client.get("/api/v1/hreis/" + endpoint).status_code == status


def test_policy_without_optional_end_date_is_created_open_ended(stub_iam):
    # HR-UC-017: an optional end date may be omitted by an API client.
    from datetime import timedelta

    from django.utils import timezone

    client = _client(
        stub_iam,
        user_id=99,
        active_role="hradmin",
        kind="staff",
        permissions=("hreis.policy.manage",),
    )
    response = client.post(
        "/api/v1/hreis/policies/",
        {
            "family": "leave",
            "version": 1,
            "effective_from": (timezone.now() - timedelta(hours=1)).isoformat(),
            "parameters": {
                "routes": [
                    {
                        "employee_kind": "staff",
                        "department": "CSE",
                        "authorities": ["Registrar"],
                    }
                ]
            },
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="optional-policy-end",
    )
    assert response.status_code == 201
    assert response.json()["effective_until"] is None


def test_hr_admin_creates_and_updates_through_audited_services(
    stub_iam,
    user_ref,
):
    # HR-AFR-010, HR-AFR-019, HR-AFR-020, HR-AFR-021,
    # HR-AFR-022, HR-AFR-023, HR-AFR-027, BR-HR-004,
    # BR-HR-005: official record create/update is audited.
    c = _client(
        stub_iam,
        user_id=99,
        active_role="hradmin",
        kind="staff",
        permissions=(
            "hreis.service_record.view",
            "hreis.service_record.create",
            "hreis.service_record.update",
            "hreis.audit.view",
        ),
        users={10: user_ref(10, "Employee Ten", kind="faculty")},
    )
    create = c.post(
        "/api/v1/hreis/service-records/",
        {
            "user_id": 10,
            "appointment_details": {"joined": "2026-01-01"},
            "department": "CSE",
            "designation_snapshot": "Professor",
            "service_history": [],
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="http-create-1",
    )
    assert create.status_code == 201, create.content
    pk = create.json()["id"]
    patch = c.patch(
        f"/api/v1/hreis/service-records/{pk}/",
        {"expected_revision": 1, "department": "Design"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="http-update-1",
    )
    assert patch.status_code == 200, patch.content
    assert patch.json()["revision"] == 2
    audit = c.get("/api/v1/hreis/audit/")
    assert audit.status_code == 200
    assert [x["action"] for x in audit.json()["results"]] == ["update", "create"]


def test_api_rejects_identity_injection_and_unexpected_fields(stub_iam, record):
    # HR-AFR-101, HR-AFR-103, HR-AFR-107, BR-HR-005, BR-HR-006:
    # privileged transport must not accept ownership replacement.
    c = _client(
        stub_iam,
        user_id=99,
        active_role="hradmin",
        kind="staff",
        permissions=("hreis.service_record.update",),
    )
    response = c.patch(
        f"/api/v1/hreis/service-records/{record.pk}/",
        {"expected_revision": 0, "user_id": 99},
        format="json",
        HTTP_IDEMPOTENCY_KEY="bad-payload",
    )
    assert response.status_code == 400
    record.refresh_from_db()
    assert record.user_id == 10


def test_current_role_cannot_be_bypassed_by_holding_hradmin_in_another_role(
    stub_iam,
    user_ref,
):
    c = _client(
        stub_iam,
        user_id=99,
        active_role="staff",
        kind="staff",
        permissions=("hreis.service_record.create",),
        users={10: user_ref(10, "Employee Ten", kind="faculty")},
    )
    response = c.post(
        "/api/v1/hreis/service-records/",
        {
            "user_id": 10,
            "appointment_details": {},
            "department": "CSE",
            "designation_snapshot": "Professor",
            "service_history": [],
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="role-bypass",
    )
    assert response.status_code == 403
    assert not EmployeeServiceRecord.objects.exists()


def test_requests_and_notifications_not_public(stub_iam):
    # HR-AFR-100, HR-AFR-101, BR-HR-002: role permission is mandatory.
    c = _client(stub_iam, permissions=())
    assert c.get("/api/v1/hreis/requests/").status_code == 403
    assert c.get("/api/v1/hreis/notifications/").status_code == 403


def test_scoped_request_detail_and_read_notification_http(stub_iam, record):
    # HR-CFR-002, HR-AFR-004, HR-AFR-099, HR-UC-005,
    # HR-UC-019, BR-HR-030: identity isolation and idempotent read.
    from modules.hreis.models import AuditEvent, HRRequest, Notification

    own = HRRequest.objects.create(user_id=10, family="leave", state="pending_authority")
    private = HRRequest.objects.create(user_id=20, family="appraisal", state="submitted")
    notice = Notification.objects.create(
        recipient_user_id=10,
        request=own,
        event_key="notice-private",
        title="Your HR action",
        message="Please review.",
    )
    private_notice = Notification.objects.create(
        recipient_user_id=20,
        event_key="notice-other",
        title="Private event",
        message="Do not disclose.",
    )
    employee = _client(
        stub_iam,
        permissions=("hreis.request.view", "hreis.notification.view", "hreis.service_record.view"),
    )
    own_detail = employee.get(f"/api/v1/hreis/requests/{own.pk}/")
    assert own_detail.status_code == 200
    assert own_detail.json()["user_id"] == 10
    assert employee.get(f"/api/v1/hreis/requests/{private.pk}/").status_code == 404
    assert employee.get("/api/v1/hreis/requests/99999/").status_code == 404
    assert (
        employee.post(f"/api/v1/hreis/notifications/{private_notice.pk}/read/").status_code == 404
    )

    first = employee.post(f"/api/v1/hreis/notifications/{notice.pk}/read/")
    assert first.status_code == 200
    assert first.json()["read_at"] is not None
    second = employee.post(f"/api/v1/hreis/notifications/{notice.pk}/read/")
    assert second.status_code == 200
    assert second.json()["read_at"] == first.json()["read_at"]
    assert AuditEvent.objects.filter(action="notification_read").count() == 1

    balances = employee.get("/api/v1/hreis/leave/balances/")
    assert balances.status_code == 200
    assert balances.json()["user_id"] == 10
    assert balances.json()["leave_balances"] == {}


def test_decision_endpoint_has_transport_level_family_approval_gate(stub_iam):
    # BR-HR-002: possessing module access is never enough to decide a request.
    c = _client(
        stub_iam,
        permissions=("hreis.request.view",),
    )
    response = c.post(
        "/api/v1/hreis/requests/99/decision/",
        {"event": "approve"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="missing-family-approval",
    )
    assert response.status_code == 403


def test_claim_only_approver_can_enter_assigned_queue_without_leave_permission(stub_iam):
    # BR-HR-002: the approval queue is not tied to leave-only rights.
    from modules.hreis.models import ApprovalRouteStep, HRRequest

    assigned = HRRequest.objects.create(
        user_id=10,
        family="ltc",
        state="pending_authority",
        route_step=0,
    )
    ApprovalRouteStep.objects.create(
        request=assigned,
        position=0,
        designation="Registrar",
        policy_version_label="ltc:1",
    )
    registrar = _client(
        stub_iam,
        user_id=201,
        active_role="Registrar",
        kind="staff",
        permissions=(
            "hreis.approval.view",
            "hreis.request.view",
            "hreis.claim.approve",
        ),
    )
    response = registrar.get("/api/v1/hreis/requests/approvals/")
    assert response.status_code == 200, response.content
    assert [row["id"] for row in response.json()["results"]] == [assigned.pk]
    employee = _client(
        stub_iam,
        user_id=10,
        active_role="faculty",
        permissions=("hreis.request.view",),
    )
    assert employee.get("/api/v1/hreis/requests/approvals/").status_code == 403


def test_hr_compliance_statuses_include_historical_leave_without_private_forms(stub_iam):
    # HR-CFR-004 / HR-AFR-014: HR sees audit statuses, not claim or medical contents.
    from modules.hreis.models import HRRequest

    leave = HRRequest.objects.create(
        user_id=10,
        family="leave",
        subtype="Medical",
        state="approved",
        payload={"justification": "confidential medical information"},
    )
    claim = HRRequest.objects.create(
        user_id=20,
        family="cpda",
        subtype="advance",
        state="financial_processing_recorded",
        payload={"document_references": ["private-invoice-987"]},
    )
    hr = _client(
        stub_iam,
        user_id=99,
        active_role="hradmin",
        kind="staff",
        permissions=("hreis.audit.view",),
    )
    response = hr.get("/api/v1/hreis/compliance/requests/")
    assert response.status_code == 200, response.content
    rows = response.json()["results"]
    assert {row["id"] for row in rows} == {leave.pk, claim.pk}
    assert {row["state"] for row in rows} == {"approved", "financial_processing_recorded"}
    assert all(
        set(row) == {"id", "user_id", "family", "state", "created_at", "submitted_at"}
        for row in rows
    )
    assert "confidential medical information" not in response.content.decode()
    assert "private-invoice-987" not in response.content.decode()
    assert "Medical" not in response.content.decode()

    employee = _client(
        stub_iam,
        user_id=10,
        active_role="faculty",
        permissions=("hreis.request.view",),
    )
    assert employee.get("/api/v1/hreis/compliance/requests/").status_code == 403
    forged = _client(
        stub_iam,
        user_id=10,
        active_role="faculty",
        permissions=("hreis.audit.view",),
    )
    assert forged.get("/api/v1/hreis/compliance/requests/").json()["results"] == []


def test_hr_compliance_detail_is_redacted_and_role_scoped(stub_iam):
    # HR-AFR-014/089: historical review must not reveal medical notes or
    # claim file references to unassigned roles or through a general request endpoint.
    from modules.hreis.models import HRRequest

    medical = HRRequest.objects.create(
        user_id=10,
        family="leave",
        subtype="Medical",
        state="rejected",
        payload={"justification": "private medical evidence"},
    )
    hr = _client(
        stub_iam,
        user_id=99,
        active_role="hradmin",
        kind="staff",
        permissions=("hreis.audit.view",),
    )
    summary = hr.get(f"/api/v1/hreis/compliance/requests/{medical.pk}/")
    assert summary.status_code == 200, summary.content
    assert set(summary.json()) == {"id", "user_id", "family", "state", "created_at", "submitted_at"}
    assert summary.json()["state"] == "rejected"
    assert "private medical evidence" not in summary.content.decode()
    assert hr.get(f"/api/v1/hreis/requests/{medical.pk}/").status_code == 403
    assert hr.get("/api/v1/hreis/compliance/requests/99999/").status_code == 404

    faculty = _client(
        stub_iam,
        user_id=20,
        active_role="faculty",
        permissions=("hreis.audit.view",),
    )
    assert faculty.get(f"/api/v1/hreis/compliance/requests/{medical.pk}/").status_code == 404


def test_hr_mutations_rate_limit_authenticated_actor_but_not_gets(stub_iam, monkeypatch):
    # BR-HR-030: a real role with IAM module grant cannot flood the HR-EIS
    # write API; the 429 comes from the shared actor-identity throttle key.
    from django.core.cache.backends.locmem import LocMemCache

    from core.api.throttling import PrincipalScopedThrottle

    monkeypatch.setitem(PrincipalScopedThrottle.THROTTLE_RATES, "hreis_write", "2/min")
    monkeypatch.setattr(
        PrincipalScopedThrottle,
        "cache",
        LocMemCache("a9-throttle-test", {}),
    )
    actor = _client(
        stub_iam,
        user_id=10,
        active_role="faculty",
        permissions=("hreis.leave.create", "hreis.request.view"),
    )
    for i in range(2):
        response = actor.post(
            "/api/v1/hreis/requests/leave/",
            {},
            format="json",
            HTTP_IDEMPOTENCY_KEY=f"throttle-malformed-{i}",
        )
        assert response.status_code == 400
    exhausted = actor.post(
        "/api/v1/hreis/requests/leave/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY="throttle-malformed-third",
    )
    assert exhausted.status_code == 429
    for _ in range(3):
        assert actor.get("/api/v1/hreis/requests/").status_code == 200
