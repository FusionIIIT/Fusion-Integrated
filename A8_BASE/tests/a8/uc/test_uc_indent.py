"""A8 UC tests: indent lifecycle (UC-001/002/003/005/011/012/016/023).

Each test carries its UC_DESIGN test_id and source_id in the name and docstring.
Aspects with no backend interface (audit log, notifications) are not asserted.
"""

import pytest

from core.api.exceptions import BadRequestError, NotFoundError
from modules.psm.domain.rules import determine_procurement_routing
from modules.psm.models import GoodsReceiptNote, Indent, IndentVersion
from modules.psm.selectors import get_indent_by_id, get_indent_version_history
from modules.psm.services import (
    modify_indent,
    record_grn,
    transition_indent,
    withdraw_indent,
    issue_internal_stock,
)
from modules.psm.contracts import get_stock_items

pytestmark = pytest.mark.django_db


def _walk(indent, principal, *states):
    for s in states:
        indent = transition_indent(principal=principal, indent_id=indent.id, target_state=s)
    return indent


# ---------------------------------------------------------------- UC-001
def test_tc_001_uc001_main_flow_submit_valid_indent(make_indent):
    """TC-001 | PSM-UC-001 Main Flow"""
    ind = make_indent()
    assert ind.status == "SUBMITTED"
    assert ind.indent_id.startswith("IND-")
    assert ind.created_at is not None
    v = IndentVersion.objects.filter(indent=ind)
    assert v.count() == 1 and v.first().version_number == 1
    assert v.first().item_details == ind.item_details


def test_tc_002_uc001_alt_a1_missing_mandatory_field(employee):
    """TC-002 | PSM-UC-001 Alternative A1"""
    from modules.psm.services import create_indent

    with pytest.raises(BadRequestError) as exc:
        create_indent(
            principal=employee,
            item_details="Oscilloscope",
            quantity=1,
            estimated_cost="5000",
            justification="",
        )
    assert "justification" in str(exc.value)
    assert Indent.objects.count() == 0


def test_tc_003_uc001_alt_a2_potential_duplicate_flagged(make_indent):
    """TC-003 | PSM-UC-001 Alternative A2"""
    first = make_indent(item_details="Laptop", estimated_cost="50000")
    second = make_indent(item_details="Laptop", estimated_cost="50000")
    first.refresh_from_db()
    assert second.is_duplicate is True
    assert second.status == "SUBMITTED"
    assert first.status == "SUBMITTED" and first.is_duplicate is False
    assert Indent.objects.count() == 2


def test_tc_004_uc001_alt_a3_item_in_system_stock(make_indent, make_stock_item):
    """TC-004 | PSM-UC-001 Alternative A3"""
    item = make_stock_item(name="Router", central_stock=8, department_stock=0)
    ind = make_indent(item_details="Router")
    found = get_stock_items([item.item_code])
    assert found and found[0]["allocable_stock"] == 8
    assert ind.status == "SUBMITTED"


# ---------------------------------------------------------------- UC-002
def test_tc_005_uc002_main_flow_confirm_receipt(make_po):
    """TC-005 | PSM-UC-002 Main Flow"""
    po = make_po(quantity=10)
    grn = record_grn(purchase_order_id=po.id, accepted_quantity=10)
    po.refresh_from_db()
    assert grn.is_confirmed is True
    assert grn.has_discrepancy is False
    assert grn.created_at is not None
    assert po.status == "DELIVERED"


def test_tc_006_uc002_alt_a1_partial_receipt(make_po):
    """TC-006 | PSM-UC-002 Alternative A1"""
    po = make_po(quantity=10)
    grn = record_grn(purchase_order_id=po.id, accepted_quantity=4)
    po.refresh_from_db()
    assert grn.accepted_quantity == 4
    assert po.indent.quantity - grn.accepted_quantity == 6
    assert po.status != "DELIVERED"


def test_tc_007_uc002_alt_a2_discrepant_goods_not_accepted(make_po):
    """TC-007 | PSM-UC-002 Alternative A2"""
    po = make_po(quantity=10)
    grn = record_grn(purchase_order_id=po.id, accepted_quantity=7, rejected_quantity=3)
    po.refresh_from_db()
    assert grn.has_discrepancy is True
    assert grn.rejected_quantity == 3 and grn.accepted_quantity == 7
    assert po.status != "DELIVERED"


# ---------------------------------------------------------------- UC-003
def test_tc_008_uc003_main_flow_view_own_indent_status(make_indent, employee):
    """TC-008 | PSM-UC-003 Main Flow"""
    ind = make_indent()
    seen = get_indent_by_id(employee, ind.indent_id)
    history = get_indent_version_history(employee, ind.id)
    assert seen is not None and seen.status == "SUBMITTED"
    assert history.count() == 1
    ind.refresh_from_db()
    assert ind.status == "SUBMITTED" and ind.current_version == 1


# ---------------------------------------------------------------- UC-005
def test_tc_011_uc005_main_flow_withdraw_permissible_state(make_indent, employee):
    """TC-011 | PSM-UC-005 Main Flow"""
    ind = make_indent()
    out = withdraw_indent(principal=employee, indent_id=ind.id)
    assert out.status == "WITHDRAWN"


def test_tc_012_uc005_alt_a1_withdraw_blocked_non_permissible(make_indent, employee, set_status):
    """TC-012 | PSM-UC-005 Alternative A1"""
    ind = set_status(make_indent(), "APPROVED")
    with pytest.raises(BadRequestError):
        withdraw_indent(principal=employee, indent_id=ind.id)
    ind.refresh_from_db()
    assert ind.status == "APPROVED"


# ---------------------------------------------------------------- UC-011
def test_tc_024_uc011_main_flow_approve_external_path(make_indent, dept_admin):
    """TC-024 | PSM-UC-011 Main Flow"""
    ind = make_indent(quantity=10)
    assert determine_procurement_routing(10, 0) == "EXTERNAL_PROCUREMENT"
    modify_indent(principal=dept_admin, indent_id=ind.id, priority="HIGH")
    ind = _walk(ind, dept_admin, "STOCK_CHECKED", "DEPT_REVIEWED")
    assert ind.priority == "HIGH"
    assert ind.status == "DEPT_REVIEWED"


def test_tc_025_uc011_main_flow_approve_internal_issue(make_indent, make_stock_item):
    """TC-025 | PSM-UC-011 Main Flow (internal issue)"""
    item = make_stock_item(central_stock=20, department_stock=0)
    ind = make_indent(quantity=10)
    assert determine_procurement_routing(10, 20) == "INTERNAL_ISSUE"
    out = issue_internal_stock(indent_id=ind.id, stock_item_id=item.id)
    assert out.status == "APPROVED"


def test_tc_026_uc011_alt_a1_rejection_requires_justification(make_indent, dept_admin):
    """TC-026 | PSM-UC-011 Alternative A1"""
    a = make_indent()
    rejected = transition_indent(
        principal=dept_admin, indent_id=a.id, target_state="REJECTED", justification="Budget exceeded"
    )
    assert rejected.status == "REJECTED"
    assert rejected.rejection_justification == "Budget exceeded"

    b = make_indent()
    with pytest.raises(BadRequestError):
        transition_indent(principal=dept_admin, indent_id=b.id, target_state="REJECTED", justification="  ")
    b.refresh_from_db()
    assert b.status == "SUBMITTED"


def test_tc_027_uc011_alt_a2_duplicate_reviewed_not_cancelled(make_indent, dept_admin):
    """TC-027 | PSM-UC-011 Alternative A2"""
    make_indent(item_details="Projector", estimated_cost="30000")
    dup = make_indent(item_details="Projector", estimated_cost="30000")
    opened = get_indent_by_id(dept_admin, dup.id)
    assert opened.is_duplicate is True
    assert opened.status == "SUBMITTED"


# ---------------------------------------------------------------- UC-012
def test_tc_028_uc012_main_flow_director_approves(make_indent, director, set_status):
    """TC-028 | PSM-UC-012 Main Flow"""
    ind = set_status(make_indent(), "AWAITING_FINAL_APPROVAL")
    out = transition_indent(principal=director, indent_id=ind.id, target_state="APPROVED")
    assert out.status == "APPROVED"


def test_tc_029_uc012_alt_a1_director_rejection_requires_justification(make_indent, director, set_status):
    """TC-029 | PSM-UC-012 Alternative A1"""
    a = set_status(make_indent(), "AWAITING_FINAL_APPROVAL")
    out = transition_indent(
        principal=director, indent_id=a.id, target_state="REJECTED", justification="Not approved"
    )
    assert out.status == "REJECTED"

    b = set_status(make_indent(), "AWAITING_FINAL_APPROVAL")
    with pytest.raises(BadRequestError):
        transition_indent(principal=director, indent_id=b.id, target_state="REJECTED")
    b.refresh_from_db()
    assert b.status == "AWAITING_FINAL_APPROVAL"


# ---------------------------------------------------------------- UC-016
def test_tc_037_uc016_main_flow_head_recommends(make_indent, dept_admin, set_status):
    """TC-037 | PSM-UC-016 Main Flow"""
    ind = set_status(make_indent(), "DEPT_REVIEWED")
    out = transition_indent(principal=dept_admin, indent_id=ind.id, target_state="HEAD_RECOMMENDED")
    assert out.status == "HEAD_RECOMMENDED"


def test_tc_039_uc016_alt_a2_head_rejection_requires_justification(make_indent, dept_admin, set_status):
    """TC-039 | PSM-UC-016 Alternative A2"""
    a = set_status(make_indent(), "DEPT_REVIEWED")
    out = transition_indent(
        principal=dept_admin, indent_id=a.id, target_state="REJECTED", justification="Not needed"
    )
    assert out.status == "REJECTED" and out.rejection_justification == "Not needed"

    b = set_status(make_indent(), "DEPT_REVIEWED")
    with pytest.raises(BadRequestError):
        transition_indent(principal=dept_admin, indent_id=b.id, target_state="REJECTED", justification="")
    b.refresh_from_db()
    assert b.status == "DEPT_REVIEWED"


# ---------------------------------------------------------------- UC-023
def test_tc_053_uc023_main_flow_modify_creates_new_version(make_indent, employee):
    """TC-053 | PSM-UC-023 Main Flow"""
    ind = make_indent(item_details="Old item", quantity=5)
    out = modify_indent(principal=employee, indent_id=ind.id, item_details="New item", quantity=8)
    assert out.current_version == 2
    assert out.item_details == "New item" and out.quantity == 8
    prior = IndentVersion.objects.filter(indent=ind, version_number=1, item_details="Old item")
    assert prior.exists()


def test_tc_054_uc023_alt_a1_modify_blocked_non_modifiable(make_indent, employee, set_status):
    """TC-054 | PSM-UC-023 Alternative A1"""
    ind = set_status(make_indent(item_details="Frozen"), "APPROVED")
    with pytest.raises(BadRequestError):
        modify_indent(principal=employee, indent_id=ind.id, item_details="Changed")
    ind.refresh_from_db()
    assert ind.item_details == "Frozen" and ind.current_version == 1


def test_tc_055_uc023_alt_a2_failed_validation_preserves_prior(make_indent, employee):
    """TC-055 | PSM-UC-023 Alternative A2"""
    ind = make_indent(justification="Valid reason")
    with pytest.raises(BadRequestError):
        modify_indent(principal=employee, indent_id=ind.id, justification="")
    ind.refresh_from_db()
    assert ind.justification == "Valid reason"
    assert ind.current_version == 1 and ind.status == "SUBMITTED"
    assert IndentVersion.objects.filter(indent=ind).count() == 1
