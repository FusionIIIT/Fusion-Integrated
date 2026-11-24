# Pure-Python domain tests with zero database access (Step 5.3).
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from modules.psm.domain import approval_policy as ap
from modules.psm.domain import finance_rules as fr
from modules.psm.domain import indent_rules as ir
from modules.psm.domain import receipt_rules as rr
from modules.psm.domain import stock_rules as sr
from modules.psm.domain import vendor_rules as vr
from modules.psm.domain.errors import ConflictRuleError, ValidationRuleError

POLICY = ap.PolicySpec(
    direct_limit=Decimal("50000.00"),
    final_approval_threshold=Decimal("100000.00"),
    high_priority_direct_allowed=True,
    modifiable_states=("draft", "submitted", "changes_requested", "department_reviewed"),
    withdrawable_states=("draft", "submitted", "changes_requested", "department_reviewed"),
    sla_reminder_hours=24,
    sla_escalation_hours=48,
    high_priority_sla_reminder_hours=12,
    high_priority_sla_escalation_hours=24,
    partial_payment_enabled=True,
    duplicate_window_days=14,
)


def test_indent_completeness_accepts_valid_and_rejects_missing():
    # BR-PSM-001, AFR-PSM-002, AFR-PSM-003
    valid = ir.IndentInput("Switch", 2, Decimal("1000.00"), "Lab use", "CSE")
    ir.validate_indent_completeness(valid)
    with pytest.raises(ValidationRuleError) as exc:
        ir.validate_indent_completeness(ir.IndentInput("", 0, Decimal("0"), "", ""))
    assert exc.value.code == "indent_incomplete"
    assert len(exc.value.details) == 5


def test_permissible_state_gate_enforces_policy():
    # BR-PSM-007, AFR-PSM-008, AFR-PSM-009
    ir.ensure_state_permissible("submitted", POLICY.modifiable_states, "modify")
    with pytest.raises(ConflictRuleError) as exc:
        ir.ensure_state_permissible("po_issued", POLICY.modifiable_states, "modify")
    assert exc.value.code == "indent_state_not_permissible"


def test_duplicate_detection_matches_within_window_only():
    # BR-PSM-015, AFR-PSM-004
    now = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)
    cands = [
        ir.ExistingIndentRef(1, "CSE", "Switch", 5, now - timedelta(days=20)),
        ir.ExistingIndentRef(2, "CSE", "Switch", 5, now - timedelta(days=3)),
    ]
    assert (
        ir.find_potential_duplicate(
            department="cse",
            item_description="switch",
            quantity=5,
            now=now,
            window_days=14,
            candidates=cands,
        )
        == 2
    )
    assert (
        ir.find_potential_duplicate(
            department="cse",
            item_description="switch",
            quantity=5,
            now=now,
            window_days=14,
            candidates=cands,
            exclude_indent_id=2,
        )
        is None
    )


def test_stock_allocation_prefers_department_then_central():
    # BR-PSM-003, BR-PSM-013, AFR-PSM-013, AFR-PSM-016
    assert sr.allocable_quantity(10, 4) == 6
    assert sr.allocable_quantity(2, 5) == 0
    balances = [
        sr.StockBalance(1, "CSE-1", "CSE", False, 10, 8),
        sr.StockBalance(2, "CEN-1", "CENTRAL", True, 20, 5),
    ]
    chosen = sr.select_allocation_location(balances, "CSE", 5)
    assert chosen is not None and chosen.location_code == "CEN-1"
    dept_ok = [sr.StockBalance(1, "CSE-1", "CSE", False, 10, 2), balances[1]]
    chosen_dept = sr.select_allocation_location(dept_ok, "CSE", 5)
    assert chosen_dept is not None and chosen_dept.location_code == "CSE-1"
    assert sr.select_allocation_location(balances, "CSE", 50) is None
    with pytest.raises(ValidationRuleError):
        sr.select_allocation_location(balances, "CSE", 0)


def test_stock_adjustment_blocks_zero_and_below_reserved():
    # BR-PSM-013
    sr.ensure_adjustment_non_negative(10, 4, -6)
    with pytest.raises(ValidationRuleError):
        sr.ensure_adjustment_non_negative(10, 4, 0)
    with pytest.raises(ConflictRuleError):
        sr.ensure_adjustment_non_negative(10, 4, -7)


def test_approval_policy_method_final_priority_and_sla():
    # BR-PSM-004, BR-PSM-005, BR-PSM-008, BR-PSM-010, BR-PSM-014, BR-PSM-028
    assert ap.select_procurement_method(Decimal("50000.00"), POLICY) == ap.METHOD_DIRECT
    assert ap.select_procurement_method(Decimal("50000.01"), POLICY) == ap.METHOD_TENDER
    with pytest.raises(ValidationRuleError):
        ap.select_procurement_method(Decimal("0"), POLICY)
    assert not ap.requires_final_approval(Decimal("100000.00"), POLICY)
    assert ap.requires_final_approval(Decimal("100000.01"), POLICY)
    assert ap.allows_high_priority_direct_path("critical", Decimal("20000.00"), POLICY)
    assert not ap.allows_high_priority_direct_path("normal", Decimal("20000.00"), POLICY)
    assert not ap.allows_high_priority_direct_path("critical", Decimal("200000.00"), POLICY)
    disabled = ap.PolicySpec(**{**POLICY.__dict__, "high_priority_direct_allowed": False})
    assert not ap.allows_high_priority_direct_path("critical", Decimal("20000.00"), disabled)
    ap.ensure_not_self_approval(1, 2)
    with pytest.raises(ConflictRuleError):
        ap.ensure_not_self_approval(1, 1)
    assert ap.ensure_rejection_reason("  Budget exceeded ") == "Budget exceeded"
    with pytest.raises(ValidationRuleError):
        ap.ensure_rejection_reason("   ")
    t0 = datetime(2026, 11, 20, 0, 0, tzinfo=UTC)
    v_ok = ap.evaluate_sla(
        stage_since=t0,
        now=t0 + timedelta(hours=5),
        priority="normal",
        policy=POLICY,
        already_reminded=False,
        already_escalated=False,
    )
    assert not v_ok.needs_reminder and not v_ok.needs_escalation
    v_rem = ap.evaluate_sla(
        stage_since=t0,
        now=t0 + timedelta(hours=13),
        priority="critical",
        policy=POLICY,
        already_reminded=False,
        already_escalated=False,
    )
    assert v_rem.needs_reminder and not v_rem.needs_escalation
    v_esc = ap.evaluate_sla(
        stage_since=t0,
        now=t0 + timedelta(hours=49),
        priority="normal",
        policy=POLICY,
        already_reminded=True,
        already_escalated=False,
    )
    assert not v_esc.needs_reminder and v_esc.needs_escalation


def test_vendor_master_validation_and_gate():
    # BR-PSM-012, AFR-PSM-062, AFR-PSM-063, AFR-PSM-064
    valid = vr.VendorMasterInput(
        "Apex Labs", "23AABCU9603R1ZM", "123456789012", "SBIN0001234", "SBI", ("GST Cert",)
    )
    vr.validate_vendor_master(valid)
    with pytest.raises(ValidationRuleError) as exc:
        vr.validate_vendor_master(vr.VendorMasterInput("", "BAD", "12", "BAD", "", ()))
    assert len(exc.value.details) == 6
    vr.ensure_vendor_verified(vendor_name="Apex", is_verified=True, is_active=True, action="pay")
    with pytest.raises(ConflictRuleError) as exc_u:
        vr.ensure_vendor_verified(
            vendor_name="Apex", is_verified=False, is_active=True, action="pay"
        )
    assert exc_u.value.code == "vendor_unverified"
    with pytest.raises(ConflictRuleError) as exc_i:
        vr.ensure_vendor_verified(
            vendor_name="Apex", is_verified=True, is_active=False, action="pay"
        )
    assert exc_i.value.code == "vendor_inactive"


def test_receipt_validation_and_stock_posting_gate():
    # BR-PSM-009, BR-PSM-022, BR-PSM-026, AFR-PSM-020, AFR-PSM-021, AFR-PSM-045, AFR-PSM-047
    assert (
        rr.validate_grn_quantities(
            ordered_quantity=10,
            previously_accepted=0,
            received_quantity=10,
            accepted_quantity=10,
            rejected_quantity=0,
        )
        == "accepted"
    )
    assert (
        rr.validate_grn_quantities(
            ordered_quantity=10,
            previously_accepted=0,
            received_quantity=6,
            accepted_quantity=4,
            rejected_quantity=2,
        )
        == "partial"
    )
    assert (
        rr.validate_grn_quantities(
            ordered_quantity=10,
            previously_accepted=0,
            received_quantity=5,
            accepted_quantity=0,
            rejected_quantity=5,
        )
        == "rejected"
    )
    with pytest.raises(ValidationRuleError):
        rr.validate_grn_quantities(
            ordered_quantity=10,
            previously_accepted=0,
            received_quantity=0,
            accepted_quantity=0,
            rejected_quantity=0,
        )
    with pytest.raises(ValidationRuleError):
        rr.validate_grn_quantities(
            ordered_quantity=10,
            previously_accepted=0,
            received_quantity=5,
            accepted_quantity=-1,
            rejected_quantity=6,
        )
    with pytest.raises(ValidationRuleError):
        rr.validate_grn_quantities(
            ordered_quantity=10,
            previously_accepted=0,
            received_quantity=5,
            accepted_quantity=2,
            rejected_quantity=2,
        )
    with pytest.raises(ConflictRuleError):
        rr.validate_grn_quantities(
            ordered_quantity=10,
            previously_accepted=8,
            received_quantity=4,
            accepted_quantity=4,
            rejected_quantity=0,
        )
    rr.ensure_can_post_stock(accepted_quantity=5, has_open_discrepancy=False, already_posted=False)
    for kw in (
        {"accepted_quantity": 5, "has_open_discrepancy": False, "already_posted": True},
        {"accepted_quantity": 0, "has_open_discrepancy": False, "already_posted": False},
        {"accepted_quantity": 5, "has_open_discrepancy": True, "already_posted": False},
    ):
        with pytest.raises(ConflictRuleError):
            rr.ensure_can_post_stock(**kw)


def test_three_way_match_and_payment_release_rules():
    # BR-PSM-017, BR-PSM-018, BR-PSM-022, AFR-PSM-056..059
    base = {
        "po_ordered_quantity": 10,
        "po_unit_price": Decimal("100.00"),
        "po_total_amount": Decimal("1000.00"),
        "confirmed_accepted_quantity": 10,
        "billed_quantity": 10,
        "billed_amount": Decimal("1000.00"),
        "has_open_discrepancy": False,
        "vendor_verified": True,
        "partial_payment_enabled": True,
    }
    ok = fr.three_way_match(fr.ThreeWayMatchInput(**base))
    assert ok.matched and ok.eligible_amount == Decimal("1000.00")
    assert not fr.three_way_match(
        fr.ThreeWayMatchInput(**{**base, "vendor_verified": False})
    ).matched
    assert not fr.three_way_match(
        fr.ThreeWayMatchInput(**{**base, "has_open_discrepancy": True})
    ).matched
    assert not fr.three_way_match(
        fr.ThreeWayMatchInput(**{**base, "confirmed_accepted_quantity": 0})
    ).matched
    assert not fr.three_way_match(fr.ThreeWayMatchInput(**{**base, "billed_quantity": 12})).matched
    assert not fr.three_way_match(
        fr.ThreeWayMatchInput(**{**base, "billed_amount": Decimal("1200.00")})
    ).matched
    assert not fr.three_way_match(
        fr.ThreeWayMatchInput(
            **{
                **base,
                "billed_quantity": 5,
                "billed_amount": Decimal("500.00"),
                "partial_payment_enabled": False,
            }
        )
    ).matched
    assert (
        fr.validate_payment_release(
            invoice_status="verified",
            eligible_amount=Decimal("1000.00"),
            already_paid=Decimal("0.00"),
            requested_amount=Decimal("400.00"),
            vendor_verified=True,
            has_open_discrepancy=False,
            partial_payment_enabled=True,
        )
        is True
    )
    assert (
        fr.validate_payment_release(
            invoice_status="partially_paid",
            eligible_amount=Decimal("1000.00"),
            already_paid=Decimal("400.00"),
            requested_amount=Decimal("600.00"),
            vendor_verified=True,
            has_open_discrepancy=False,
            partial_payment_enabled=True,
        )
        is False
    )
    with pytest.raises(ValidationRuleError):
        fr.validate_payment_release(
            invoice_status="verified",
            eligible_amount=Decimal("1000.00"),
            already_paid=Decimal("0.00"),
            requested_amount=Decimal("0.00"),
            vendor_verified=True,
            has_open_discrepancy=False,
            partial_payment_enabled=True,
        )
    for bad in (
        {"vendor_verified": False},
        {"has_open_discrepancy": True},
        {"invoice_status": "on_hold"},
        {"requested_amount": Decimal("1500.00")},
        {"requested_amount": Decimal("400.00"), "partial_payment_enabled": False},
    ):
        kw = {
            "invoice_status": "verified",
            "eligible_amount": Decimal("1000.00"),
            "already_paid": Decimal("0.00"),
            "requested_amount": Decimal("1000.00"),
            "vendor_verified": True,
            "has_open_discrepancy": False,
            "partial_payment_enabled": True,
        }
        kw.update(bad)
        with pytest.raises(ConflictRuleError):
            fr.validate_payment_release(**kw)
