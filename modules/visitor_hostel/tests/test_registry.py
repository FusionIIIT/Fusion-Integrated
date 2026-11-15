"""Permission strings are free text to the fake IAM; these keep them honest."""
from modules.visitor_hostel import registry
from modules.visitor_hostel.domain import permissions as perms

DECLARED = {code for code, _ in registry.PERMISSIONS}
GRANTED = {c for codes in registry.ROLE_GRANTS.values() for c in codes}


def _domain_codes():
    return {v for k, v in vars(perms).items() if k.isupper() and k != "MODULE"}


def test_the_code_and_the_registry_name_the_same_permissions():
    assert _domain_codes() == DECLARED


def test_every_permission_has_a_holder_or_is_explicitly_unassigned():
    assert not DECLARED - GRANTED - set(registry.SYSTEM_PERMISSIONS)


def test_nothing_unassigned_is_quietly_granted():
    assert not GRANTED & set(registry.SYSTEM_PERMISSIONS)


def test_nothing_is_granted_that_is_not_declared():
    assert not GRANTED - DECLARED


def test_every_code_carries_the_module_prefix():
    assert all(c.startswith(f"{registry.MODULE['code']}.") for c in DECLARED)


def test_every_nav_item_is_guarded_by_a_declared_permission():
    for item in registry.NAV_ITEMS:
        assert item["required_permission"] in DECLARED, item["code"]
        assert item["to"].startswith(registry.MODULE["base_path"])


def test_indenters_see_none_of_the_office_screens():
    """A student must not get a Caretaker menu item just by being granted the module."""
    indenter = set(registry.ROLE_GRANTS["student"])
    office = {i["code"] for i in registry.NAV_ITEMS
              if i["required_permission"] in indenter}
    assert office == {"vh.book", "vh.mine"}


def test_the_caretaker_cannot_approve_and_the_incharge_cannot_review():
    """The two-step routing (CW-VH-01) is only real if no one role holds both."""
    assert perms.BOOKING_APPROVE not in registry.ROLE_GRANTS["VhCaretaker"]
    assert perms.BOOKING_REVIEW not in registry.ROLE_GRANTS["VhIncharge"]


def test_no_designation_holds_an_authority_the_spec_leaves_unresolved():
    unresolved = {perms.TARIFF_MANAGE, perms.DUTY_MANAGE, perms.MODIFICATION_APPROVE}
    assert unresolved <= set(registry.SYSTEM_PERMISSIONS)
