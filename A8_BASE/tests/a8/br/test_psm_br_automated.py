"""Automated specification-based tests for PSM Business Rules (BR_DESIGN.json).

One test per test_id. Tests with no available interface are skipped with
NOT_AUTOMATED: <reason>. Where a test_id's expected result has parts that no
supplied interface can observe, the docstring lists them under "Not observable".
"""
import pytest

from core.api.exceptions import BadRequestError, NotFoundError
from modules.psm.domain.rules import (
    determine_procurement_method,
    determine_procurement_routing,
)
from modules.psm.domain.three_way_match import perform_three_way_match
from modules.psm.models import Indent, IndentVersion, PurchaseOrder, StockItem, StockTransfer
from modules.psm.selectors.stock import get_allocable_stock
from modules.psm.services import (
    create_indent,
    create_purchase_order,
    create_vendor,
    initiate_stock_transfer,
    modify_indent,
    record_grn,
    reserve_stock,
    transition_indent,
    verify_vendor,
    withdraw_indent,
)

pytestmark = pytest.mark.django_db


def not_automated(reason):
    return pytest.mark.skip(reason=f"NOT_AUTOMATED: {reason}")


NO_NOTIF = "No notification / communication-history interface in supplied implementation."
NO_ROUTING = "No approval-routing/hierarchy interface in supplied implementation."
NO_SLA = "No SLA/priority-queue interface in supplied implementation."
NO_PAY = "No payment-eligibility/payment-release interface in supplied implementation."
NO_RBAC = "No endpoint/permission-check interface for role-based access in supplied files."
NO_AUDIT = "No audit-trail interface in supplied implementation."
NO_REPORT = "No reporting interface in supplied implementation."
NO_POST = "No GRN stock-posting interface in supplied implementation."


# ---------------------------------------------------------------- BR-PSM-001
def test_tc_br_001(make_indent):
    """TC-BR-001 | BR-PSM-001 condition-false (all required info present)"""
    indent = make_indent()
    assert indent.pk is not None
    assert indent.indent_id and indent.created_at is not None
    assert indent.status == "SUBMITTED"


@pytest.mark.parametrize("tc,field", [
    ("TC-BR-002", "item_details"),
    ("TC-BR-003", "quantity"),
    ("TC-BR-004", "estimated_cost"),
    ("TC-BR-005", "justification"),
])
def test_br_001_missing_field(make_indent, tc, field):
    """TC-BR-002..005 | BR-PSM-001 missing-<field>: blocked and field identified"""
    with pytest.raises(BadRequestError) as exc:
        make_indent(**{field: None})
    assert field in str(exc.value)
    assert Indent.objects.count() == 0


def test_tc_br_006(make_indent, principal):
    """TC-BR-006 | BR-PSM-001 resubmission-trigger"""
    indent = make_indent()
    with pytest.raises(BadRequestError) as exc:
        modify_indent(principal=principal, indent_id=indent.id, item_details="")
    assert "item_details" in str(exc.value)


# ---------------------------------------------------------------- BR-PSM-003
def test_tc_br_007():
    """TC-BR-007 | BR-PSM-003 sufficient-stock"""
    assert determine_procurement_routing(5, 10) == "INTERNAL_ISSUE"


def test_tc_br_008():
    """TC-BR-008 | BR-PSM-003 insufficient-stock"""
    assert determine_procurement_routing(10, 4) == "EXTERNAL_PROCUREMENT"


def test_tc_br_009(make_stock):
    """TC-BR-009 | BR-PSM-003 central-stock-included"""
    item = make_stock(central=20, department=0)
    allocable = get_allocable_stock(item.id)
    assert determine_procurement_routing(10, allocable) == "INTERNAL_ISSUE"


@not_automated("No service enforces/records the stock check ordering before external procurement.")
def test_tc_br_010():
    """TC-BR-010 | BR-PSM-003 check-before-external-procurement"""


# ---------------------------------------------------------------- BR-PSM-004
@not_automated(NO_ROUTING)
def test_tc_br_011():
    """TC-BR-011 | BR-PSM-004 below-threshold-routing"""


@not_automated(NO_ROUTING)
def test_tc_br_012():
    """TC-BR-012 | BR-PSM-004 above-threshold-routing"""


@not_automated(NO_ROUTING)
def test_tc_br_013():
    """TC-BR-013 | BR-PSM-004 configuration-change"""


@not_automated(NO_ROUTING)
def test_tc_br_014():
    """TC-BR-014 | BR-PSM-004 exception-higher-priority-direct-path"""


# ---------------------------------------------------------------- BR-PSM-005
def test_tc_br_015(make_indent, principal):
    """TC-BR-015 | BR-PSM-005 reject-without-justification"""
    indent = make_indent()
    with pytest.raises(BadRequestError):
        transition_indent(principal=principal, indent_id=indent.id,
                          target_state="REJECTED", justification="")
    indent.refresh_from_db()
    assert indent.status == "SUBMITTED"


def test_tc_br_016(make_indent, principal):
    """TC-BR-016 | BR-PSM-005 reject-with-justification

    Not observable: requestor notification, audit-log entry (no interfaces)."""
    indent = make_indent()
    transition_indent(principal=principal, indent_id=indent.id,
                      target_state="REJECTED", justification="Over budget")
    indent.refresh_from_db()
    assert indent.status == "REJECTED"
    assert indent.rejection_justification == "Over budget"


# ---------------------------------------------------------------- BR-PSM-006
@not_automated(NO_NOTIF)
def test_tc_br_017():
    """TC-BR-017 | BR-PSM-006 submission-and-approval-notification"""


@not_automated(NO_NOTIF)
def test_tc_br_018():
    """TC-BR-018 | BR-PSM-006 dispatch-receipt-alerts"""


@not_automated(NO_NOTIF)
def test_tc_br_019():
    """TC-BR-019 | BR-PSM-006 invoice-payment-alerts"""


@not_automated(NO_NOTIF)
def test_tc_br_020():
    """TC-BR-020 | BR-PSM-006 communication-history-retention"""


# ---------------------------------------------------------------- BR-PSM-007
def test_tc_br_021(make_indent, principal):
    """TC-BR-021 | BR-PSM-007 permissible-state-modify"""
    indent = make_indent()
    modify_indent(principal=principal, indent_id=indent.id, justification="Updated reason")
    indent.refresh_from_db()
    assert indent.justification == "Updated reason"
    assert indent.current_version == 2
    assert IndentVersion.objects.filter(indent=indent).exists()
    assert indent.status == "SUBMITTED"  # remains in the review path


def test_tc_br_022(make_indent, principal):
    """TC-BR-022 | BR-PSM-007 non-permissible-state-modify"""
    indent = make_indent()
    Indent.objects.filter(pk=indent.pk).update(status="APPROVED")
    with pytest.raises(BadRequestError):
        modify_indent(principal=principal, indent_id=indent.id, justification="x")
    indent.refresh_from_db()
    assert indent.justification == "Lab upgrade"
    assert indent.current_version == 1


def test_tc_br_023(make_indent, principal):
    """TC-BR-023 | BR-PSM-007 permissible-state-withdraw"""
    indent = make_indent()
    withdraw_indent(principal=principal, indent_id=indent.id)
    indent.refresh_from_db()
    assert indent.status == "WITHDRAWN"


def test_tc_br_024(make_indent, principal):
    """TC-BR-024 | BR-PSM-007 non-permissible-state-withdraw"""
    indent = make_indent()
    Indent.objects.filter(pk=indent.pk).update(status="APPROVED")
    with pytest.raises(BadRequestError):
        withdraw_indent(principal=principal, indent_id=indent.id)
    indent.refresh_from_db()
    assert indent.status == "APPROVED"


@not_automated("No cancel operation / CANCELLED state exists in supplied services or models.")
def test_tc_br_025():
    """TC-BR-025 | BR-PSM-007 permissible-state-cancel"""


@not_automated("No cancel operation / CANCELLED state exists in supplied services or models.")
def test_tc_br_026():
    """TC-BR-026 | BR-PSM-007 non-permissible-state-cancel"""


# ---------------------------------------------------------------- BR-PSM-008
def test_tc_br_027():
    """TC-BR-027 | BR-PSM-008 direct-procurement (configured threshold passed explicitly)"""
    assert determine_procurement_method(50000, tender_threshold=100000) == "DIRECT"


def test_tc_br_028():
    """TC-BR-028 | BR-PSM-008 tender-procurement (configured threshold passed explicitly)"""
    assert determine_procurement_method(150000, tender_threshold=100000) == "TENDER"


# ---------------------------------------------------------------- BR-PSM-009
def test_tc_br_029(make_po):
    """TC-BR-029 | BR-PSM-009 confirmed-receipt-proceeds

    Not observable: final stock posting / payment release (no interface)."""
    indent, po = make_po(quantity=10)
    grn = record_grn(purchase_order_id=po.id, accepted_quantity=10)
    po.refresh_from_db()
    assert grn.is_confirmed is True
    assert grn.has_discrepancy is False
    assert po.status == "DELIVERED"


@not_automated("record_grn always sets is_confirmed=True; no interface to record an unconfirmed receipt or attempt posting/payment.")
def test_tc_br_030():
    """TC-BR-030 | BR-PSM-009 no-confirmation-blocks"""


def test_tc_br_031(make_po):
    """TC-BR-031 | BR-PSM-009 discrepancy-blocks

    Not observable: blocking of posting/payment and post-resolution release (no interface)."""
    indent, po = make_po(quantity=10)
    grn = record_grn(purchase_order_id=po.id, accepted_quantity=8, rejected_quantity=2)
    assert grn.has_discrepancy is True


# ---------------------------------------------------------------- BR-PSM-010
@not_automated(NO_ROUTING)
def test_tc_br_032():
    """TC-BR-032 | BR-PSM-010 route-to-director"""


@not_automated(NO_ROUTING)
def test_tc_br_033():
    """TC-BR-033 | BR-PSM-010 director-approves"""


@not_automated(NO_ROUTING)
def test_tc_br_034():
    """TC-BR-034 | BR-PSM-010 director-rejects"""


# ---------------------------------------------------------------- BR-PSM-012
def test_tc_br_035(make_indent, make_vendor):
    """TC-BR-035 | BR-PSM-012 verified-vendor-po"""
    from datetime import date
    indent, vendor = make_indent(), make_vendor(verified=True)
    po = create_purchase_order(indent_id=indent.id, vendor_id=vendor.id,
                               procurement_method="DIRECT", total_cost="1000.00",
                               delivery_schedule=date.today())
    assert po.status == "ISSUED"


def test_tc_br_036(make_indent, make_vendor):
    """TC-BR-036 | BR-PSM-012 unverified-vendor-po"""
    from datetime import date
    indent, vendor = make_indent(), make_vendor(verified=False)
    with pytest.raises(BadRequestError):
        create_purchase_order(indent_id=indent.id, vendor_id=vendor.id,
                              procurement_method="DIRECT", total_cost="1000.00",
                              delivery_schedule=date.today())
    assert PurchaseOrder.objects.count() == 0


@not_automated(NO_PAY)
def test_tc_br_037():
    """TC-BR-037 | BR-PSM-012 unverified-vendor-payment"""


def test_tc_br_038(make_indent, make_vendor):
    """TC-BR-038 | BR-PSM-012 verification-completed-continue

    Not observable: payment continuation (no payment interface); PO issuance covered."""
    from datetime import date
    indent, vendor = make_indent(), make_vendor(verified=False)
    kwargs = dict(indent_id=indent.id, vendor_id=vendor.id, procurement_method="DIRECT",
                  total_cost="1000.00", delivery_schedule=date.today())
    with pytest.raises(BadRequestError):
        create_purchase_order(**kwargs)
    verify_vendor(vendor_id=vendor.id)
    assert create_purchase_order(**kwargs).status == "ISSUED"


# ---------------------------------------------------------------- BR-PSM-013
def test_tc_br_039(make_stock):
    """TC-BR-039 | BR-PSM-013 reserve-on-allocation"""
    item = make_stock(central=10)
    reserve_stock(stock_item_id=item.id, quantity=4)
    item.refresh_from_db()
    assert item.reserved_stock == 4
    assert get_allocable_stock(item.id) == 6


def test_tc_br_040(make_stock):
    """TC-BR-040 | BR-PSM-013 over-commitment-prevented"""
    item = make_stock(central=10)
    reserve_stock(stock_item_id=item.id, quantity=10)
    with pytest.raises(BadRequestError):
        reserve_stock(stock_item_id=item.id, quantity=1)
    item.refresh_from_db()
    assert item.reserved_stock == 10
    assert get_allocable_stock(item.id) == 0


@not_automated("No transfer approval/dispatch/receipt interface to establish an approved transfer and observe its reservation lifecycle.")
def test_tc_br_041():
    """TC-BR-041 | BR-PSM-013 transfer-reservation-retained"""


# ---------------------------------------------------------------- BR-PSM-014
@not_automated(NO_SLA)
def test_tc_br_042():
    """TC-BR-042 | BR-PSM-014 sla-reminder"""


@not_automated(NO_SLA)
def test_tc_br_043():
    """TC-BR-043 | BR-PSM-014 sla-escalation"""


@not_automated(NO_SLA)
def test_tc_br_044():
    """TC-BR-044 | BR-PSM-014 priority-queue"""


@not_automated(NO_SLA)
def test_tc_br_045():
    """TC-BR-045 | BR-PSM-014 sla-not-reached"""


# ---------------------------------------------------------------- BR-PSM-015
def test_tc_br_046(make_indent):
    """TC-BR-046 | BR-PSM-015 duplicate-flagged

    Not observable: Department Admin review queue / blocking of procurement (no interface)."""
    first = make_indent(item_details="Laptop 16GB", estimated_cost="50000.00")
    second = make_indent(item_details="laptop 16gb", estimated_cost="51000.00")
    second.refresh_from_db()
    assert second.is_duplicate is True
    assert second.status == "SUBMITTED"  # not auto-cancelled
    assert Indent.objects.filter(pk__in=[first.pk, second.pk]).count() == 2  # not merged


def test_tc_br_047(make_indent, principal):
    """TC-BR-047 | BR-PSM-015 modified-indent-trigger"""
    make_indent(item_details="Laptop 16GB", estimated_cost="50000.00")
    other = make_indent(item_details="Wireless Mouse", estimated_cost="500.00")
    assert other.is_duplicate is False
    modify_indent(principal=principal, indent_id=other.id,
                  item_details="Laptop 16GB", estimated_cost="50000.00")
    other.refresh_from_db()
    assert other.is_duplicate is True


def test_tc_br_048(make_indent):
    """TC-BR-048 | BR-PSM-015 non-duplicate"""
    make_indent(item_details="Laptop 16GB", estimated_cost="50000.00")
    other = make_indent(item_details="Projector", estimated_cost="30000.00")
    assert other.is_duplicate is False


# ---------------------------------------------------------------- BR-PSM-017
@not_automated(NO_PAY)
def test_tc_br_049():
    """TC-BR-049 | BR-PSM-017 all-conditions-met"""


@not_automated(NO_PAY)
def test_tc_br_050():
    """TC-BR-050 | BR-PSM-017 missing-po"""


@not_automated(NO_PAY)
def test_tc_br_051():
    """TC-BR-051 | BR-PSM-017 grn-not-accepted"""


@not_automated(NO_PAY)
def test_tc_br_052():
    """TC-BR-052 | BR-PSM-017 invoice-not-verified"""


@not_automated(NO_PAY)
def test_tc_br_053():
    """TC-BR-053 | BR-PSM-017 delivery-not-confirmed"""


@not_automated(NO_PAY)
def test_tc_br_054():
    """TC-BR-054 | BR-PSM-017 vendor-not-verified"""


# ---------------------------------------------------------------- BR-PSM-018
def test_tc_br_055():
    """TC-BR-055 | BR-PSM-018 match-passes"""
    r = perform_three_way_match(po_amount=1000, grn_accepted_qty=10,
                                unit_price=100, invoice_amount=1000)
    assert r["status"] == "VERIFIED" and r["is_matched"] is True
    assert r["discrepancies"] == []


def test_tc_br_056():
    """TC-BR-056 | BR-PSM-018 mismatch-hold

    Not observable: recorded hold reason on an invoice record, notifications,
    payment-release blocking (no interface). Match result is asserted."""
    r = perform_three_way_match(po_amount=1000, grn_accepted_qty=10,
                                unit_price=100, invoice_amount=1200)
    assert r["status"] == "MISMATCH_HOLD" and r["is_matched"] is False
    assert r["discrepancies"]


# ---------------------------------------------------------------- BR-PSM-019
@not_automated("No return/replacement/warranty resolution interface in supplied implementation.")
def test_tc_br_057():
    """TC-BR-057 | BR-PSM-019 resolution-adjustments"""


@not_automated("No return/replacement/warranty resolution interface in supplied implementation.")
def test_tc_br_058():
    """TC-BR-058 | BR-PSM-019 unresolved-no-adjustment"""


# ---------------------------------------------------------------- BR-PSM-020
@not_automated(NO_RBAC)
def test_tc_br_059():
    """TC-BR-059 | BR-PSM-020 authorized-access"""


@not_automated(NO_RBAC)
def test_tc_br_060():
    """TC-BR-060 | BR-PSM-020 unauthorized-access"""


# ---------------------------------------------------------------- BR-PSM-021
@not_automated(NO_AUDIT)
def test_tc_br_061():
    """TC-BR-061 | BR-PSM-021 action-audit"""


def test_tc_br_062(make_indent, principal):
    """TC-BR-062 | BR-PSM-021 indent-version-history

    Not observable: audit entries (no interface)."""
    indent = make_indent(justification="v1 text")
    modify_indent(principal=principal, indent_id=indent.id, justification="v2 text")
    modify_indent(principal=principal, indent_id=indent.id, justification="v3 text")
    versions = {v.version_number: v.justification
                for v in IndentVersion.objects.filter(indent=indent)}
    assert set(versions) == {1, 2, 3}
    assert versions == {1: "v1 text", 2: "v2 text", 3: "v3 text"}
    assert IndentVersion.objects.filter(indent=indent).count() == 3


@not_automated("No vendor-master update operation in supplied services; only create/verify exist.")
def test_tc_br_063():
    """TC-BR-063 | BR-PSM-021 vendor-version-history"""


# ---------------------------------------------------------------- BR-PSM-022
def test_tc_br_064(make_po):
    """TC-BR-064 | BR-PSM-022 partial-receipt

    The remaining open balance is derived (indent quantity - accepted); no stored field."""
    indent, po = make_po(quantity=100)
    grn = record_grn(purchase_order_id=po.id, accepted_quantity=60)
    po.refresh_from_db()
    assert grn.accepted_quantity == 60
    assert po.status != "DELIVERED"  # remains open
    assert indent.quantity - grn.accepted_quantity == 40


@not_automated(NO_PAY)
def test_tc_br_065():
    """TC-BR-065 | BR-PSM-022 partial-payment-supported"""


@not_automated(NO_PAY)
def test_tc_br_066():
    """TC-BR-066 | BR-PSM-022 partial-payment-exceeds-accepted"""


# ---------------------------------------------------------------- BR-PSM-023
@not_automated("No tender/bid evaluation or committee-approval interface in supplied implementation.")
def test_tc_br_067():
    """TC-BR-067 | BR-PSM-023 tender-evaluation-recorded"""


@not_automated("No tender/bid evaluation or committee-approval interface in supplied implementation.")
def test_tc_br_068():
    """TC-BR-068 | BR-PSM-023 no-committee-approval"""


# ---------------------------------------------------------------- BR-PSM-024
@not_automated(NO_REPORT)
def test_tc_br_069():
    """TC-BR-069 | BR-PSM-024 authorized-report"""


@not_automated(NO_REPORT)
def test_tc_br_070():
    """TC-BR-070 | BR-PSM-024 unauthorized-report"""


@not_automated(NO_REPORT)
def test_tc_br_071():
    """TC-BR-071 | BR-PSM-024 scheduled-generation"""


# ---------------------------------------------------------------- BR-PSM-025
def test_tc_br_072():
    """TC-BR-072 | BR-PSM-025 vendor-create-version

    Not observable: audit entry (no interface). Version record = Vendor.version."""
    v = create_vendor(name="Beta Ltd", gst_number="22AAAAA0000A1Z5",
                      bank_account_number="111", bank_ifsc="SBIN0000001")
    assert v.version == 1


@not_automated("No vendor-master update operation or version-history table in supplied implementation.")
def test_tc_br_073():
    """TC-BR-073 | BR-PSM-025 vendor-change-traceable"""


# ---------------------------------------------------------------- BR-PSM-026
@not_automated(NO_POST)
def test_tc_br_074():
    """TC-BR-074 | BR-PSM-026 accepted-quantity-posted"""


@not_automated(NO_POST)
def test_tc_br_075():
    """TC-BR-075 | BR-PSM-026 unresolved-discrepancy-not-posted"""


@not_automated(NO_POST)
def test_tc_br_076():
    """TC-BR-076 | BR-PSM-026 partial-receipt-exception"""


# ---------------------------------------------------------------- BR-PSM-027
@not_automated("No transfer-receipt confirmation/completion service (only initiate_stock_transfer exists).")
def test_tc_br_077():
    """TC-BR-077 | BR-PSM-027 transfer-confirmation-ledgers"""


def test_tc_br_078(make_stock):
    """TC-BR-078 | BR-PSM-027 before-confirmation-no-ledger-update"""
    item = make_stock(central=10, department=5)
    transfer = initiate_stock_transfer(source_dept="CSE", dest_dept="ECE",
                                       stock_item_id=item.id, quantity=5)
    StockTransfer.objects.filter(pk=transfer.pk).update(status="DISPATCHED")
    item.refresh_from_db()
    transfer.refresh_from_db()
    assert (item.central_stock, item.department_stock) == (10, 5)
    assert transfer.status != "COMPLETED"


# ---------------------------------------------------------------- BR-PSM-028
@not_automated("BR-PSM-028 is a generic configured-policy obligation; no specific configured rule/interface is supplied to exercise.")
def test_tc_br_079():
    """TC-BR-079 | BR-PSM-028 governed-action-rule-applied"""


@not_automated("BR-PSM-028 is a generic configured-policy obligation; no specific configured rule/interface is supplied to exercise.")
def test_tc_br_080():
    """TC-BR-080 | BR-PSM-028 governed-action-compliant"""
