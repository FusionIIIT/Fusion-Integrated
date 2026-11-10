import pytest

from modules.iaa.domain.rules import Role
from modules.iaa.models import (
    ApprovalRoute,
    AuditEntry,
    Department,
    FinancialRequest,
    Notification,
    RoleAssignment,
)
from modules.iaa.tests.conftest import (
    ADMIN,
    AUDITOR,
    BASIC,
    DEAN,
    FINANCE,
    HOD,
    OTHER,
    action,
    draft,
    submitted,
    validated,
)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "path", ["requests", "anomalies", "observations", "reports", "notifications"]
)
def test_system_admin_has_no_operational_access(world, client_as, path):
    submitted(client_as)
    assert client_as(ADMIN).get(f"/api/v1/iaa/{path}").status_code == 403


@pytest.mark.parametrize("uid", [BASIC, FINANCE, HOD, AUDITOR])
def test_operational_roles_cannot_configure(world, client_as, uid):
    c = client_as(uid)
    assert c.get("/api/v1/iaa/config/roles").status_code == 403
    assert c.post("/api/v1/iaa/config/roles", {}, format="json").status_code == 403


@pytest.mark.parametrize(
    "perms,modules",
    [((), ("institute_accounts_audits",)), (("institute_accounts_audits.workspace.access",), ())],
)
def test_both_fusion_gates_are_required(world, client_as, perms, modules):
    assert (
        client_as(BASIC, permissions=perms, modules=modules).get("/api/v1/iaa/session").status_code
        == 403
    )


def test_multi_role_user_must_explicitly_choose_and_switch_is_logged(world, client_as):
    RoleAssignment.objects.create(user_id=BASIC, role=Role.HOD, department="CSE")
    c = client_as(BASIC)
    del c._credentials["HTTP_X_IAA_ROLE"]
    assert c.get("/api/v1/iaa/requests").status_code == 403
    assert c.post("/api/v1/iaa/session", {"role": Role.HOD}, format="json").status_code == 200
    assert AuditEntry.objects.filter(
        actor_id=BASIC, action="switch_role", active_role=Role.HOD
    ).exists()
    assert c.post("/api/v1/iaa/session", {"role": Role.ADMIN}, format="json").status_code == 403


def test_role_header_cannot_forge_privilege(world, client_as):
    c = client_as(BASIC)
    c._credentials["HTTP_X_IAA_ROLE"] = Role.ADMIN
    assert c.get("/api/v1/iaa/config/roles").status_code == 403


def test_foreign_request_is_absent_on_all_creator_actions(world, client_as):
    pk = submitted(client_as)
    c = client_as(OTHER)
    assert c.get(f"/api/v1/iaa/requests/{pk}").status_code == 404
    assert c.get("/api/v1/iaa/requests").json()["results"] == []
    for name, body in [("submit", {}), ("respond", {"response": "stolen"})]:
        assert action(c, pk, name, **body).status_code == 404
    assert c.patch(f"/api/v1/iaa/requests/{pk}", {"amount": "20"}, format="json").status_code == 404


def test_unassigned_authority_cannot_decide(world, client_as):
    pk = validated(client_as)
    assert (
        action(client_as(DEAN), pk, "decide", approve=True, remarks="Out of turn").status_code
        == 404
    )
    assert action(client_as(HOD), pk, "decide", approve=True, remarks="").status_code == 400


def test_revocation_blocks_future_actions_without_rewriting_history(world, client_as):
    pk = validated(client_as)
    action(client_as(HOD), pk, "decide", approve=True, remarks="Valid approval")
    entry = AuditEntry.objects.get(actor_id=HOD, action="approve")
    RoleAssignment.objects.filter(user_id=HOD).update(active=False)
    assert client_as(HOD).get(f"/api/v1/iaa/requests/{pk}").status_code == 403
    entry.refresh_from_db()
    assert entry.active_role == Role.HOD


def test_scoped_auditor_cannot_see_other_department_or_its_notifications(world, client_as):
    pk = submitted(client_as)
    RoleAssignment.objects.filter(user_id=AUDITOR).update(department="ECE")
    Notification.objects.create(
        user_id=AUDITOR,
        role=Role.AUDITOR,
        request_id=pk,
        event="test",
        message="A sensitive notification",
    )
    c = client_as(AUDITOR)
    assert c.get(f"/api/v1/iaa/requests/{pk}").status_code == 404
    assert c.get("/api/v1/iaa/reports").json()["requests"] == 0
    assert c.get("/api/v1/iaa/notifications").json()["results"] == []


def test_creator_cannot_submit_for_unassigned_department(world, client_as):
    assert draft(client_as(BASIC), department="ECE").status_code == 403
    assert not FinancialRequest.objects.exists()


@pytest.mark.parametrize(
    "url", ["http://example.org/x", "javascript:alert(1)", "file:///etc/passwd"]
)
def test_evidence_requires_https_and_is_never_fetched(world, client_as, url):
    assert draft(client_as(BASIC), documents=[url]).status_code == 400


def test_no_operational_delete_endpoint(world, client_as):
    pk = submitted(client_as)
    assert client_as(BASIC).delete(f"/api/v1/iaa/requests/{pk}").status_code == 405


def test_role_assignment_configuration_is_audited(world, client_as):
    c = client_as(ADMIN)
    r = c.post(
        "/api/v1/iaa/config/roles",
        {"user_id": OTHER, "role": Role.AUDITOR, "department": "CSE", "active": True},
        format="json",
    )
    assert r.status_code == 201, r.json()
    assert AuditEntry.objects.filter(
        actor_id=ADMIN, active_role=Role.ADMIN, action="configure_roles"
    ).exists()


def test_unknown_identity_and_non_authority_routes_are_rejected(world, client_as):
    c = client_as(ADMIN)
    assert (
        c.post(
            "/api/v1/iaa/config/roles", {"user_id": 99999, "role": Role.BASIC}, format="json"
        ).status_code
        == 400
    )
    assert (
        c.post(
            "/api/v1/iaa/config/routes",
            {
                "name": "Invalid",
                "kind": "expense",
                "steps": [{"user_id": ADMIN, "role": Role.ADMIN, "timeout_hours": 24}],
            },
            format="json",
        ).status_code
        == 400
    )


def test_missing_finance_routing_is_preserved_and_recoverable(world, client_as):
    Department.objects.all().delete()
    pk = submitted(client_as)
    req = FinancialRequest.objects.get(pk=pk)
    assert req.status == "submitted" and req.recovery_note and req.finance_user_id is None
    Department.objects.create(code="CSE", finance_user_id=FINANCE)
    c = client_as(ADMIN)
    response = c.post(f"/api/v1/iaa/recovery/{pk}", {}, format="json")
    assert response.status_code == 200 and response.json() == {"status": "routing_recovered"}
    assert action(client_as(FINANCE), pk, "validate", remarks="Recovered").status_code == 200


def test_ambiguous_route_does_not_validate_or_reserve(world, client_as):
    original = ApprovalRoute.objects.get(kind="expense")
    original.pk = None
    original.name = "Duplicate match"
    original.save()
    pk = submitted(client_as)
    response = action(client_as(FINANCE), pk, "validate", remarks="Review")
    assert response.status_code == 409 and response.json()["error"]["code"] == "route_ambiguous"
    assert FinancialRequest.objects.get(pk=pk).reservation == 0


def test_basic_user_cannot_export_and_admin_cannot_operationally_approve(world, client_as):
    pk = validated(client_as)
    assert client_as(BASIC).get("/api/v1/iaa/reports?export=csv").status_code == 403
    assert action(client_as(ADMIN), pk, "decide", approve=True, remarks="Bypass").status_code == 403


@pytest.mark.parametrize("change", [{"active": False}, {"role": Role.BASIC}])
def test_last_administrator_cannot_be_removed_or_demoted(world, client_as, change):
    assignment = RoleAssignment.objects.get(user_id=ADMIN)
    response = client_as(ADMIN).post(
        "/api/v1/iaa/config/roles",
        {
            "id": assignment.pk,
            "user_id": ADMIN,
            "role": Role.ADMIN,
            "department": "",
            "active": True,
            **change,
        },
        format="json",
    )
    assert response.status_code == 409
    assignment.refresh_from_db()
    assert assignment.active and assignment.role == Role.ADMIN


def test_configuration_history_retains_values_not_only_field_names(world, client_as):
    response = client_as(ADMIN).post(
        "/api/v1/iaa/config/roles",
        {
            "user_id": OTHER,
            "role": Role.AUDITOR,
            "department": "CSE",
            "active": True,
        },
        format="json",
    )
    assert response.status_code == 201
    entry = AuditEntry.objects.get(action="configure_roles")
    assert entry.details["before"] is None
    assert entry.details["after"]["role"] == Role.AUDITOR
