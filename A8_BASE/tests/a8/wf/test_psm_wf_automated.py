"""Automated specification-based tests for PSM workflows (WF_DESIGN.json).

One test per test_id (TC-001..TC-028). Tests with no available interface are
skipped with NOT_AUTOMATED: <reason>.

STATE MAPPING used where the design names workflow states and the supplied
IndentState enum has the closest equivalent (the only state machine supplied):
  Submitted                          -> SUBMITTED
  External Procurement Required      -> STOCK_CHECKED
  Department Reviewed                -> DEPT_REVIEWED
  Department Head Recommended        -> HEAD_RECOMMENDED
  Awaiting Final Approval            -> AWAITING_FINAL_APPROVAL
  Procurement Authorized             -> APPROVED
Each docstring lists parts of the expected result that no supplied interface can
observe under "Not observable".
"""
from datetime import date

import pytest

from core.api.exceptions import BadRequestError
from modules.psm.domain.rules import determine_procurement_routing
from modules.psm.domain.three_way_match import perform_three_way_match
from modules.psm.models import Indent, IndentVersion, PurchaseOrder
from modules.psm.selectors.stock import get_allocable_stock
from modules.psm.services import (
    create_purchase_order,
    modify_indent,
    record_grn,
    reserve_stock,
    transition_indent,
)

pytestmark = pytest.mark.django_db


def not_automated(reason):
    return pytest.mark.skip(reason=f"NOT_AUTOMATED: {reason}")


def _advance(principal, indent, targets):
    """Drive transition_indent through targets, returning the list of visited statuses."""
    visited = [Indent.objects.get(pk=indent.pk).status]
    for t in targets:
        transition_indent(principal=principal, indent_id=indent.id, target_state=t)
        visited.append(Indent.objects.get(pk=indent.pk).status)
    return visited


NO_INTERNAL = ("Internal-issue lifecycle states (Stock Reserved, Internal Issue Approved, Dispatched / Ready "
               "for Receipt, GRN Accepted, Stock Posted) and receipt-confirmation/stock-posting services are "
               "not in the supplied implementation.")
NO_PAYMENT = ("No invoice-verification state, payment-processing service, or Invoice Verified / Paid / "
              "Partially Paid states in the supplied implementation.")
NO_TENDER = "No tender/bid/committee interface in the supplied implementation."
NO_DISC = "No discrepancy-case / return / replacement interface in the supplied implementation."


# ----------------------------------------------------------------------- BW-PSM-01
@not_automated(NO_INTERNAL)
def test_tc_001():
    """TC-001 | BW-PSM-01 rows 1-6 internal fulfilment full-receipt path"""


@not_automated(NO_INTERNAL)
def test_tc_002():
    """TC-002 | BW-PSM-01 row 5 receipt accepted (partial) and row 6 accepted portion confirmed"""


@not_automated("No Employee receipt-confirmation or stock-posting service exists to attempt Confirm Delivery Receipt.")
def test_tc_003():
    """TC-003 | BW-PSM-01 row 6 guard: no unresolved discrepancy"""


# ----------------------------------------------------------------------- BW-PSM-02
def test_tc_004(make_indent, principal):
    """TC-004 | BW-PSM-02 rows 1-5 standard external authorization path

    Final authority review not required: HEAD_RECOMMENDED must advance to
    authorized (APPROVED) without entering AWAITING_FINAL_APPROVAL.
    Not observable: PS Admin method selection (no interface), audit."""
    indent = make_indent()
    visited = _advance(principal, indent,
                       ["STOCK_CHECKED", "DEPT_REVIEWED", "HEAD_RECOMMENDED", "APPROVED"])
    assert visited == ["SUBMITTED", "STOCK_CHECKED", "DEPT_REVIEWED", "HEAD_RECOMMENDED", "APPROVED"]
    assert "AWAITING_FINAL_APPROVAL" not in visited


# ----------------------------------------------------------------------- BW-PSM-03
def test_tc_005(make_indent, principal):
    """TC-005 | BW-PSM-03 rows 1-6 final authority approval path

    Not observable: per-decision audit log entries, actor roles (no interface)."""
    indent = make_indent()
    visited = _advance(principal, indent,
                       ["STOCK_CHECKED", "DEPT_REVIEWED", "HEAD_RECOMMENDED",
                        "AWAITING_FINAL_APPROVAL", "APPROVED"])
    assert visited == ["SUBMITTED", "STOCK_CHECKED", "DEPT_REVIEWED", "HEAD_RECOMMENDED",
                       "AWAITING_FINAL_APPROVAL", "APPROVED"]


def test_tc_006(make_indent, make_vendor):
    """TC-006 | BW-PSM-03 row 5/6 final authority gating"""
    indent = make_indent()
    Indent.objects.filter(pk=indent.pk).update(status="AWAITING_FINAL_APPROVAL")
    vendor = make_vendor(verified=True)
    with pytest.raises(BadRequestError):
        create_purchase_order(indent_id=indent.id, vendor_id=vendor.id,
                              procurement_method="DIRECT", total_cost="1000.00",
                              delivery_schedule=date.today())
    assert PurchaseOrder.objects.count() == 0
    indent.refresh_from_db()
    assert indent.status == "AWAITING_FINAL_APPROVAL"


# ----------------------------------------------------------------------- BW-PSM-04
@not_automated(NO_PAYMENT)
def test_tc_007():
    """TC-007 | BW-PSM-04 rows 1-6 direct procurement to payment, full payment"""


def test_tc_008(make_indent, make_vendor):
    """TC-008 | BW-PSM-04 row 1 guard: vendor verified and required approvals complete"""
    indent = make_indent()
    Indent.objects.filter(pk=indent.pk).update(status="APPROVED")  # Procurement Authorized
    vendor = make_vendor(verified=False)
    with pytest.raises(BadRequestError):
        create_purchase_order(indent_id=indent.id, vendor_id=vendor.id,
                              procurement_method="DIRECT", total_cost="1000.00",
                              delivery_schedule=date.today())
    assert PurchaseOrder.objects.count() == 0
    indent.refresh_from_db()
    assert indent.status == "APPROVED"


@not_automated(NO_PAYMENT)
def test_tc_009():
    """TC-009 | BW-PSM-04 row 6 outcome Partially Paid"""


def test_tc_010(make_po):
    """TC-010 | BW-PSM-04 row 5 guard: three-way match mismatch places invoice on hold

    Not observable: persisted invoice hold state / payment-release block (no invoice model
    or payment interface). The three-way-match outcome is asserted."""
    indent, po = make_po(quantity=10)
    grn = record_grn(purchase_order_id=po.id, accepted_quantity=10)
    assert grn.is_confirmed is True  # Receipt Confirmed precondition
    result = perform_three_way_match(po_amount=1000, grn_accepted_qty=10,
                                     unit_price=100, invoice_amount=1200)
    assert result["status"] == "MISMATCH_HOLD"
    assert result["is_matched"] is False
    assert result["discrepancies"]


# ----------------------------------------------------------------------- BW-PSM-05
@not_automated(NO_TENDER)
def test_tc_011():
    """TC-011 | BW-PSM-05 rows 1-7 tender procurement to payment"""


@not_automated(NO_TENDER)
def test_tc_012():
    """TC-012 | BW-PSM-05 row 1 guard: committee-approved selection recorded"""


# ----------------------------------------------------------------------- BW-PSM-06 / 10
@not_automated(NO_DISC)
def test_tc_013():
    """TC-013 | BW-PSM-06 rows 1-5 discrepancy return/adjustment path"""


@not_automated(NO_DISC)
def test_tc_014():
    """TC-014 | BW-PSM-10 rows 1-5 one replacement traversal"""


# ----------------------------------------------------------------------- BW-PSM-07
def test_tc_015(make_indent, principal):
    """TC-015 | BW-PSM-07 rows 1-3 modify pending indent and re-review

    Expected: modified indent awaits re-review (SUBMITTED; no distinct 'Modified' state exists),
    then DEPT_REVIEWED, then HEAD_RECOMMENDED, with the modification kept as a distinct version.
    Not observable: audit log entry."""
    indent = make_indent(justification="original reason")
    modify_indent(principal=principal, indent_id=indent.id, justification="revised reason")
    indent.refresh_from_db()
    assert indent.status == "SUBMITTED"
    assert indent.current_version == 2
    assert IndentVersion.objects.filter(indent=indent).count() >= 2  # distinct versions retained
    transition_indent(principal=principal, indent_id=indent.id, target_state="DEPT_REVIEWED")
    transition_indent(principal=principal, indent_id=indent.id, target_state="HEAD_RECOMMENDED")
    indent.refresh_from_db()
    assert indent.status == "HEAD_RECOMMENDED"


def test_tc_016(make_indent, principal):
    """TC-016 | BW-PSM-07 row 1 guard: modification permitted"""
    indent = make_indent()
    Indent.objects.filter(pk=indent.pk).update(status="HEAD_RECOMMENDED")
    before = IndentVersion.objects.filter(indent=indent).count()
    with pytest.raises(BadRequestError):
        modify_indent(principal=principal, indent_id=indent.id, justification="changed")
    indent.refresh_from_db()
    assert indent.status == "HEAD_RECOMMENDED"
    assert indent.justification == "Lab upgrade"
    assert indent.current_version == 1
    assert IndentVersion.objects.filter(indent=indent).count() == before


def test_tc_017(make_indent, principal):
    """TC-017 | BW-PSM-07 row 1 guard: modified version validates"""
    indent = make_indent()
    with pytest.raises(BadRequestError):
        modify_indent(principal=principal, indent_id=indent.id, justification="")
    indent.refresh_from_db()
    assert indent.status == "SUBMITTED"
    assert indent.justification == "Lab upgrade"
    assert indent.current_version == 1


# ----------------------------------------------------------------------- BW-PSM-08
@not_automated("Only initiate_stock_transfer exists; no dispatch or destination-confirmation (completion/ledger update) service.")
def test_tc_018():
    """TC-018 | BW-PSM-08 rows 1-3 inter-departmental stock transfer"""


@not_automated("No transfer dispatch service exists to attempt Process and Dispatch Stock Transfer.")
def test_tc_019():
    """TC-019 | BW-PSM-08 row 2 guard: sufficient allocable stock"""


# ----------------------------------------------------------------------- CW-PSM-01
def test_tc_020(make_indent, make_stock):
    """TC-020 | CW-PSM-01 row 1/2 stock check routing decision

    Not observable: the named states Stock Reserved / Internal Path and External Procurement
    Required (no combined Check-and-Reserve service); routing decision and reservation asserted."""
    ok_item = make_stock(central=10)
    low_item = make_stock(central=2)
    ok_indent = make_indent(quantity=5)
    low_indent = make_indent(item_details="Projector", quantity=5)

    assert determine_procurement_routing(ok_indent.quantity, get_allocable_stock(ok_item.id)) == "INTERNAL_ISSUE"
    reserve_stock(stock_item_id=ok_item.id, quantity=ok_indent.quantity)
    ok_item.refresh_from_db()
    assert ok_item.reserved_stock == 5

    assert determine_procurement_routing(low_indent.quantity, get_allocable_stock(low_item.id)) == "EXTERNAL_PROCUREMENT"
    low_item.refresh_from_db()
    assert low_item.reserved_stock == 0


@not_automated("No cost/priority approval-routing or configured-policy interface in the supplied implementation.")
def test_tc_021():
    """TC-021 | CW-PSM-01 rows 3-4 routing by cost/priority policy with Dept Head included"""


def test_tc_022(make_indent, principal):
    """TC-022 | CW-PSM-01 rows 5-6 outcome Awaiting Final Approval then Authorized

    Not observable: configured 'final approval required' policy flag, actor roles (no interface)."""
    indent = make_indent()
    _advance(principal, indent, ["STOCK_CHECKED", "DEPT_REVIEWED", "HEAD_RECOMMENDED"])
    transition_indent(principal=principal, indent_id=indent.id, target_state="AWAITING_FINAL_APPROVAL")
    indent.refresh_from_db()
    assert indent.status == "AWAITING_FINAL_APPROVAL"
    transition_indent(principal=principal, indent_id=indent.id, target_state="APPROVED")
    indent.refresh_from_db()
    assert indent.status == "APPROVED"


@not_automated(NO_TENDER)
def test_tc_023():
    """TC-023 | CW-PSM-01 rows 7-8 tender method and PO issuance after tender; row 8 direct method"""


@not_automated("issue_internal_stock sets status APPROVED; the Dispatched / Ready for Receipt state and its dispatch step do not exist.")
def test_tc_024():
    """TC-024 | CW-PSM-01 row 9 internal issue path"""


# ----------------------------------------------------------------------- CW-PSM-02
def test_tc_025(make_po):
    """TC-025 | CW-PSM-02 rows 1-3 delivery inspection outcome branch

    Mapping: GRN Accepted = confirmed GRN without discrepancy; Discrepancy Identified =
    GRN with has_discrepancy. Not observable: Employee Confirm Receipt step (no service)."""
    _, ok_po = make_po(quantity=10)
    ok_grn = record_grn(purchase_order_id=ok_po.id, accepted_quantity=10)
    assert ok_grn.is_confirmed is True and ok_grn.has_discrepancy is False

    _, bad_po = make_po(quantity=10)
    bad_grn = record_grn(purchase_order_id=bad_po.id, accepted_quantity=7, rejected_quantity=3)
    assert bad_grn.has_discrepancy is True


@not_automated(NO_DISC)
def test_tc_026():
    """TC-026 | CW-PSM-02 rows 5-6 case resolution branch (return/adjustment vs replacement)"""


@not_automated(NO_DISC)
def test_tc_027():
    """TC-027 | CW-PSM-02 row 7 exactly one replacement received and accepted"""


@not_automated(NO_PAYMENT)
def test_tc_028():
    """TC-028 | CW-PSM-02 rows 8-9 invoice verification from alternate source states and payment"""
