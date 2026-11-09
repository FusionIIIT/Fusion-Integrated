"""Staff endpoints need the `vms` module grant on top of the permission."""
import pytest

pytestmark = pytest.mark.django_db

BASE = "/api/v1/vms/"

# One endpoint per area package: (method, path, permission the view wants).
AREAS = [
    ("host", "get", "host/requests", "vms.request.view_assigned"),
    ("gate", "post", "gate/validate", "vms.gate.operate"),
    ("zones", "get", "zones/elevations", "vms.zone.elevate"),
    ("admin", "get", "blacklist", "vms.blacklist.manage"),
    ("walkin", "get", "walkin/registrations", "vms.request.decide"),
    ("visit", "post", "visit/check-out", "vms.gate.operate"),
    ("notify", "get", "notify/inbox", "vms.notification.view_self"),
    ("monitor", "get", "monitor/dashboard", "vms.monitor.view"),
    ("muster", "get", "muster/current", "vms.monitor.view"),
    ("events", "get", "events", "vms.event.manage"),
    ("reports", "get", "reports", "vms.report.view"),
    ("extensions", "get", "extensions", "vms.request.decide"),
]


@pytest.mark.parametrize("area,method,path,perm", AREAS, ids=[a[0] for a in AREAS])
def test_permission_without_module_is_forbidden(api_as, area, method, path, perm):
    client = api_as(permissions=(perm,), modules=())
    resp = getattr(client, method)(BASE + path, {}, format="json")
    assert resp.status_code == 403


@pytest.mark.parametrize("area,method,path,perm",
                         [a for a in AREAS if a[0] in ("host", "gate", "admin", "notify",
                                                        "events", "reports", "extensions", "visit")],
                         ids=lambda v: v if isinstance(v, str) and "/" not in v else None)
def test_module_grant_lets_request_past_the_gate(api_as, area, method, path, perm):
    client = api_as(permissions=(perm,))
    resp = getattr(client, method)(BASE + path, {}, format="json")
    assert resp.status_code != 403


def test_visitor_session_endpoint_is_unaffected(api_as):
    # Visitor endpoints never consult the staff module gate: a staff token
    # without the module is rejected by visitor-session auth (401), not 403.
    client = api_as(permissions=(), modules=())
    assert client.get(BASE + "visitor/requests").status_code == 401
