# Privilege escalation, dual gates, CSRF, role-switch, hostile input, and permission-drift tests (Step 5.1, 5.5).
import re
from pathlib import Path

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from core.api import csrf
from modules.psm import registry
from modules.psm.services.policy import seed_default_policy

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, uid=3001, role="faculty", modules=("psm",), permissions=(), roles=None):
    stub_iam(
        make_session(
            user_id=uid,
            kind="faculty",
            active_role=role,
            roles=tuple(roles or (role,)),
            modules=modules,
            permissions=permissions,
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token tok")
    return c


def test_unauthenticated_request_is_401(stub_iam):
    stub_iam(None)
    assert APIClient().get("/api/v1/psm/indents").status_code == 401


def test_both_gates_enforced_separately(stub_iam):
    # Has permission but no module grant -> 403.
    c_no_mod = _client(stub_iam, modules=(), permissions=("psm.indent.view",))
    assert c_no_mod.get("/api/v1/psm/indents").status_code == 403
    # Has module grant but no permission -> 403.
    c_no_perm = _client(stub_iam, modules=("psm",), permissions=())
    assert c_no_perm.get("/api/v1/psm/indents").status_code == 403


def test_cookie_write_without_csrf_header_answers_403(stub_iam):
    # Step 7.7: cookie-authenticated write without X-CSRF-Token must answer 403.
    seed_default_policy()
    stub_iam(
        make_session(
            user_id=3001,
            kind="faculty",
            active_role="faculty",
            roles=("faculty",),
            modules=("psm",),
            permissions=tuple(registry.ROLE_GRANTS["faculty"]),
        )
    )
    c = APIClient()
    c.cookies["fusion_session"] = "sess-cookie-val"
    payload = {
        "department": "CSE",
        "item_description": "Cable",
        "quantity": 1,
        "estimated_cost": "500.00",
        "justification": "Lab",
    }
    assert c.post("/api/v1/psm/indents", payload, format="json").status_code == 403
    token = csrf.token_for("sess-cookie-val")
    r_ok = c.post("/api/v1/psm/indents", payload, format="json", HTTP_X_CSRF_TOKEN=token)
    assert r_ok.status_code == 201


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/api/v1/psm/vendors", {"name": "Evil Vendor"}),
        (
            "post",
            "/api/v1/psm/tenders",
            {
                "indent_id": 1,
                "title": "T",
                "scope": "S",
                "evaluation_criteria": "C",
                "submission_deadline": "2030-01-01T00:00:00Z",
            },
        ),
        (
            "post",
            "/api/v1/psm/purchase-orders",
            {
                "indent_id": 1,
                "vendor_id": 1,
                "unit_price": "100.00",
                "planned_delivery_date": "2030-01-01",
            },
        ),
        (
            "post",
            "/api/v1/psm/invoices",
            {
                "purchase_order_id": 1,
                "invoice_number": "INV-1",
                "billed_quantity": 1,
                "billed_amount": "100.00",
            },
        ),
        ("post", "/api/v1/psm/invoices/1/pay", {"amount": "100.00"}),
        (
            "post",
            "/api/v1/psm/policy",
            {"direct_limit": "1000.00", "final_approval_threshold": "2000.00"},
        ),
        ("get", "/api/v1/psm/audit", None),
        ("post", "/api/v1/psm/reports/generate", {"report_type": "financial"}),
        (
            "post",
            "/api/v1/psm/stock/adjustments",
            {"item_id": 1, "location_id": 1, "quantity_delta": 5, "reason": "x"},
        ),
        (
            "post",
            "/api/v1/psm/transfers",
            {"item_id": 1, "source_location_id": 1, "destination_location_id": 2, "quantity": 1},
        ),
        ("post", "/api/v1/psm/indents/1/review", {"decision": "approve"}),
        ("post", "/api/v1/psm/indents/1/recommend", {"decision": "recommend"}),
        ("post", "/api/v1/psm/indents/1/procurement-review", {}),
        ("post", "/api/v1/psm/indents/1/final-decision", {"decision": "approve"}),
    ],
)
def test_plain_employee_refused_privileged_endpoints(stub_iam, method, path, body):
    # BR-PSM-020, AFR-PSM-090
    c = _client(stub_iam, role="faculty", permissions=tuple(registry.ROLE_GRANTS["faculty"]))
    resp = (
        getattr(c, method)(path, body, format="json")
        if body is not None
        else getattr(c, method)(path)
    )
    assert resp.status_code == 403


def test_role_switch_enforces_acting_role_only(stub_iam):
    # User holds faculty + ps_admin; acting as faculty must not see ps_admin permissions/screens.
    c = _client(
        stub_iam,
        role="faculty",
        roles=("faculty", "ps_admin"),
        permissions=tuple(registry.ROLE_GRANTS["faculty"]),
    )
    assert c.get("/api/v1/psm/vendors").status_code == 403
    assert c.post("/api/v1/psm/vendors", {"name": "Blocked"}, format="json").status_code == 403


def test_hostile_query_params_return_400_not_500(stub_iam):
    c = _client(stub_iam, role="ps_admin", permissions=tuple(registry.ROLE_GRANTS["ps_admin"]))
    assert c.get("/api/v1/psm/stock/availability?item_id=not-an-int").status_code == 400
    assert c.get("/api/v1/psm/stock/availability?location_id=abc").status_code == 400


def test_server_owned_fields_cannot_be_forged_on_create(stub_iam):
    seed_default_policy()
    c = _client(
        stub_iam, uid=3010, role="faculty", permissions=tuple(registry.ROLE_GRANTS["faculty"])
    )
    r = c.post(
        "/api/v1/psm/indents",
        {
            "department": "CSE",
            "item_description": "Monitor",
            "quantity": 1,
            "estimated_cost": "12000.00",
            "justification": "Dev",
            "status": "procurement_authorized",
            "user_id": 9999,
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.data["status"] == "submitted"
    assert r.data["user_id"] == 3010


def test_all_permission_strings_in_module_code_are_declared():
    # Step 5.1: fails immediately if a permission code in views/services/tests drifts from registry.
    declared = {code for code, _ in registry.PERMISSIONS}
    root = Path(__file__).resolve().parents[1]
    used: set[str] = set()
    for py in root.rglob("*.py"):
        if py.name == "registry.py":
            continue
        used.update(
            re.findall(r'["\'](psm\.[a-z_]+\.[a-z_]+)["\']', py.read_text(encoding="utf-8"))
        )
    unknown = used - declared
    assert not unknown, f"Undeclared permission codes found: {sorted(unknown)}"


def test_every_psm_route_and_method_enforces_both_403_gates(stub_iam):
    # R1-10: verify both module-grant gate and permission gate across every PSM route/method pair.
    from modules.psm.api import urls as psm_urls

    all_perms = tuple(code for code, _ in registry.PERMISSIONS)
    pairs: list[tuple[str, str]] = []
    for pattern in psm_urls.urlpatterns:
        raw = str(pattern.pattern)
        path = "/api/v1/psm/" + re.sub(r"<int:[^>]+>", "1", raw)
        view_cls = pattern.callback.view_class
        pairs.extend(
            (method, path)
            for method in ("get", "post", "patch", "put", "delete")
            if hasattr(view_cls, method)
        )
    assert len(pairs) >= 40
    for method, path in pairs:
        c_no_mod = _client(stub_iam, modules=(), permissions=all_perms)
        r_no_mod = getattr(c_no_mod, method)(path, {}, format="json")
        assert r_no_mod.status_code == 403, f"No-module gate missed on {method.upper()} {path}"
        c_no_perm = _client(stub_iam, modules=("psm",), permissions=())
        r_no_perm = getattr(c_no_perm, method)(path, {}, format="json")
        assert r_no_perm.status_code == 403, f"No-permission gate missed on {method.upper()} {path}"
