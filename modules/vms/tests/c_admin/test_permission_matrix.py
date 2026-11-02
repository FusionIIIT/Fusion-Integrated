"""Every admin endpoint: anonymous 401, wrong permission 403, right permission passes
the gate (and an unknown id is a 404, never a 403, so ids are not enumerable)."""
import pytest

from modules.vms import registry

BASE = "/api/v1/vms/"

# (method, path, permission that opens it)
ENDPOINTS = [
    ("get", "roles", "vms.role.assign"),
    ("post", "roles", "vms.role.assign"),
    ("post", "roles/999999/reassign", "vms.role.assign"),
    ("post", "roles/999999/revoke", "vms.role.assign"),
    ("get", "integrations", "vms.integration.manage"),
    ("get", "integrations/sms_gateway", "vms.integration.manage"),
    ("put", "integrations/sms_gateway", "vms.integration.manage"),
    ("get", "vip", "vms.vip.manage"),
    ("post", "vip", "vms.vip.manage"),
    ("post", "vip/999999/revoke", "vms.vip.manage"),
    ("get", "policies", "vms.policy.manage"),
    ("post", "policies", "vms.policy.manage"),
    ("get", "policies/999999", "vms.policy.manage"),
    ("patch", "policies/999999", "vms.policy.manage"),
    ("post", "policies/999999/publish", "vms.policy.publish"),
    ("get", "policies/999998/diff/999999", "vms.policy.manage"),
    ("get", "blacklist", "vms.blacklist.manage"),
    ("post", "blacklist", "vms.blacklist.manage"),
    ("get", "blacklist/versions", "vms.blacklist.manage"),
    ("post", "blacklist/versions", "vms.blacklist.manage"),
    ("get", "blacklist/versions/999999/entries", "vms.blacklist.manage"),
    ("post", "blacklist/versions/999999/entries", "vms.blacklist.manage"),
    ("patch", "blacklist/versions/999999/entries/1", "vms.blacklist.manage"),
    ("delete", "blacklist/versions/999999/entries/1", "vms.blacklist.manage"),
    ("post", "blacklist/versions/999999/publish", "vms.blacklist.publish"),
    ("get", "safelist", "vms.safelist.manage"),
    ("post", "safelist", "vms.safelist.manage"),
    ("post", "safelist/999999/revoke", "vms.safelist.manage"),
    ("get", "zones", "vms.zone.manage"),
    ("post", "zones", "vms.zone.manage"),
    ("patch", "zones/999999", "vms.zone.manage"),
    ("get", "gates", "vms.zone.manage"),
    ("post", "gates", "vms.zone.manage"),
    ("patch", "gates/999999", "vms.zone.manage"),
    ("get", "audit", "vms.audit.view"),
    ("get", "audit/export.csv", "vms.audit.view"),
]
IDS = [f"{m}-{p}" for m, p, _ in ENDPOINTS]


@pytest.mark.django_db
@pytest.mark.parametrize("method,path,perm", ENDPOINTS, ids=IDS)
def test_anonymous_is_401(api_as, method, path, perm):
    r = getattr(api_as(anonymous=True), method)(BASE + path, {}, format="json")
    assert r.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize("method,path,perm", ENDPOINTS, ids=IDS)
def test_wrong_role_is_403(api_as, method, path, perm):
    # holds every other VMS permission except the one required
    from modules.vms.registry import PERMISSIONS
    others = [c for c, _ in PERMISSIONS if c != perm
              and not (perm == "vms.policy.manage" and c == "vms.policy.publish")]
    r = getattr(api_as(permissions=others), method)(BASE + path, {}, format="json")
    assert r.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("method,path,perm", ENDPOINTS, ids=IDS)
def test_right_permission_passes_the_gate(api_as, method, path, perm):
    r = getattr(api_as(permissions=[perm]), method)(BASE + path, {}, format="json")
    assert r.status_code not in (401, 403, 405) and r.status_code < 500


@pytest.mark.django_db
@pytest.mark.parametrize("method,path,perm", [e for e in ENDPOINTS if "999999" in e[1]],
                         ids=str)
def test_unknown_id_is_404_not_403(api_as, method, path, perm):
    r = getattr(api_as(permissions=[perm]), method)(BASE + path, {}, format="json")
    # a body that fails validation first is a 400; what must never happen is 403/500
    assert r.status_code in (400, 404, 409)


@pytest.mark.django_db
def test_policy_publish_permission_alone_can_read_policies(api_as):
    assert api_as(permissions=["vms.policy.publish"]).get(BASE + "policies").status_code == 200
    assert api_as(permissions=["vms.policy.publish"]).post(
        BASE + "policies", {}, format="json").status_code == 403


@pytest.mark.django_db
def test_roles_me_needs_only_a_signed_in_user(api_as):
    assert api_as(anonymous=True).get(BASE + "roles/me").status_code == 401
    assert api_as().get(BASE + "roles/me").status_code == 200


def test_admin_designations_hold_pass_terminate():          # service request g-3
    for designation in ("Registrar", "acadadmin", "Director"):
        assert "vms.pass.terminate" in registry.ROLE_GRANTS[designation]
        assert "vms.event.manage" in registry.ROLE_GRANTS[designation]
    codes = [code for code, _ in registry.PERMISSIONS]
    assert codes.count("vms.pass.terminate") == 1
