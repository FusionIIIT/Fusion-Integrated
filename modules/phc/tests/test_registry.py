"""The permission strings tests and grants use are the ones registry.PERMISSIONS declares."""
import re
from pathlib import Path

from modules.phc import registry
from modules.phc.api import views

DECLARED = {code for code, _ in registry.PERMISSIONS}
VERBS = {"view", "create", "update", "delete", "approve", "publish", "review", "assign",
         "revoke", "export", "import", "restore", "manage"}


def test_codes_follow_the_naming_rule_and_closed_verb_list():
    for code in DECLARED:
        module, noun, verb = code.split(".")
        assert module == registry.MODULE["code"] == "phc"
        assert verb in VERBS, code
        assert noun.isidentifier(), code


# AFR-PHC-036
def test_every_granted_code_is_declared_afr_phc_036():
    for role, codes in registry.ROLE_GRANTS.items():
        assert set(codes) <= DECLARED, role


def test_every_nav_item_requires_a_declared_permission():
    for item in registry.NAV_ITEMS:
        assert item["required_permission"] in DECLARED, item["code"]


# PHC-BR-03
def test_every_view_gates_on_declared_permissions_phc_br_03():
    for name in dir(views):
        view = getattr(views, name)
        for codes in getattr(view, "method_permissions", {}).values():
            assert set(codes) <= DECLARED, name


def test_code_strings_in_tests_are_declared():
    here = Path(__file__).parent
    pattern = re.compile(r'"(phc\.[a-z_]+\.[a-z_]+)"')
    for path in here.rglob("test_*.py"):
        for code in pattern.findall(path.read_text()):
            assert code in DECLARED, f"{path.name}: {code}"


# PHC-BR-04
def test_students_cannot_claim_but_employees_can_phc_br_04():
    assert "phc.claim.create" not in registry.ROLE_GRANTS["student"]
    assert "phc.claim.create" in registry.ROLE_GRANTS["faculty"]
    assert "phc.claim.create" in registry.ROLE_GRANTS["staff"]


def test_processing_offices_cannot_submit_claims():
    for office in ("PHC Staff", "Accounts & Audit", "Approving Authority"):
        assert "phc.claim.create" not in registry.ROLE_GRANTS[office]


# PHC-BR-08
def test_one_office_per_claim_stage_phc_br_08():
    holders = {code: {r for r, c in registry.ROLE_GRANTS.items() if code in c}
               for code in ("phc.claim.review", "phc.claim.update", "phc.claim.approve")}
    assert holders == {"phc.claim.review": {"PHC Staff"},
                       "phc.claim.update": {"Accounts & Audit"},
                       "phc.claim.approve": {"Approving Authority"}}
