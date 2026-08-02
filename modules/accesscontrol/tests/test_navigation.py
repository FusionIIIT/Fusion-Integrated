import pytest

from modules.accesscontrol import contracts
from modules.accesscontrol.models import Module, NavItem

pytestmark = pytest.mark.django_db


def _module(code="placement_cell", status="active", **kw):
    return Module.objects.create(
        code=code, label=code.title(), base_path=f"/{code}",
        nav_section=kw.pop("section", "Placement"), status=status, **kw)


def test_ungranted_module_is_absent():
    _module()
    assert contracts.build_navigation(granted_module_codes=[], permissions=[]) == []


def test_granted_module_appears():
    m = _module()
    NavItem.objects.create(module=m, code="p.list", label="Postings",
                           to="/placement/postings")
    nav = contracts.build_navigation(granted_module_codes=["placement_cell"],
                                     permissions=[])
    assert nav[0]["section"] == "Placement"
    assert nav[0]["items"][0]["code"] == "placement_cell"


def test_links_filtered_by_permission():
    m = _module()
    NavItem.objects.create(module=m, code="p.list", label="Postings",
                           to="/placement/postings")
    NavItem.objects.create(module=m, code="p.admin", label="Admin",
                           to="/placement/admin",
                           required_permission="placement_cell.offer.issue")
    nav = contracts.build_navigation(granted_module_codes=["placement_cell"],
                                     permissions=["placement_cell.offer.issue"])
    assert len(nav[0]["items"][0]["links"]) == 2

    nav = contracts.build_navigation(granted_module_codes=["placement_cell"],
                                     permissions=[])
    assert len(nav[0]["items"][0]["links"]) == 1


def test_module_whose_every_link_is_filtered_away_is_omitted():
    """A section that expands to nothing is worse than no section."""
    m = _module()
    NavItem.objects.create(module=m, code="p.admin", label="Admin",
                           to="/placement/admin",
                           required_permission="placement_cell.offer.issue")
    assert contracts.build_navigation(granted_module_codes=["placement_cell"],
                                      permissions=[]) == []


def test_single_link_at_base_path_collapses_to_a_flat_entry():
    m = _module(code="dashboard", section="Overview")
    NavItem.objects.create(module=m, code="d.home", label="Dashboard",
                           to="/dashboard")
    nav = contracts.build_navigation(granted_module_codes=["dashboard"],
                                     permissions=[])
    item = nav[0]["items"][0]
    assert item["to"] == "/dashboard" and "links" not in item


def test_planned_module_is_never_shown_even_if_granted():
    _module(code="hostel", status="planned")
    assert contracts.build_navigation(granted_module_codes=["hostel"],
                                      permissions=[]) == []
