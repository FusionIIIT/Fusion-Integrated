"""BR design cases exercised through the frozen PSM backend journeys."""
import json
from pathlib import Path

import pytest

from modules.psm.tests import test_adversarial as adversarial
from modules.psm.tests import test_coverage_and_traceability as trace
from modules.psm.tests import test_domain as domain
from modules.psm.tests import test_journeys as journeys
from modules.psm.tests import test_privilege_escalation as access
from modules.psm.tests import test_schedule as schedule

pytestmark = pytest.mark.django_db

# Each entry is a separate design case. Reusing the existing journey functions
# keeps these cases on the production API/service paths and their DB assertions.
_SCENARIOS = {
    "TC-001": (domain.test_indent_completeness_accepts_valid_and_rejects_missing, ()),
    "TC-002": (domain.test_indent_completeness_accepts_valid_and_rejects_missing, ()),
    "TC-003": (journeys.test_journey_bw_psm_01_internal_stock_fulfilment, ("stub_iam",)),
    "TC-004": (journeys.test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial, ("stub_iam",)),
    "TC-005": (journeys.test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial, ("stub_iam",)),
    "TC-006": (domain.test_approval_policy_method_final_priority_and_sla, ()),
    "TC-007": (trace.test_transfers_cancel_stock_adjustments_vendor_updates_and_approvals, ()),
    "TC-008": (trace.test_http_endpoints_invoices_reports_schedules_audit_notifications_policy, ("stub_iam",)),
    "TC-009": (journeys.test_journey_remaining_live_ucs_and_alternate_flows, ("stub_iam",)),
    "TC-010": (domain.test_permissible_state_gate_enforces_policy, ()),
    "TC-011": (journeys.test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial, ("stub_iam",)),
    "TC-012": (journeys.test_journey_bw_psm_03_05_high_value_final_approval_and_tender, ("stub_iam",)),
    "TC-013": (journeys.test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial, ("stub_iam",)),
    "TC-014": (adversarial.test_unresolved_discrepancy_blocks_stock_posting_and_second_replacement, ()),
    "TC-015": (journeys.test_journey_bw_psm_03_05_high_value_final_approval_and_tender, ("stub_iam",)),
    "TC-016": (trace.test_transfers_cancel_stock_adjustments_vendor_updates_and_approvals, ()),
    "TC-017": (adversarial.test_unverified_vendor_blocked_at_po_and_payment, ()),
    "TC-018": (journeys.test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial, ("stub_iam",)),
    "TC-019": (journeys.test_journey_bw_psm_01_internal_stock_fulfilment, ("stub_iam",)),
    "TC-020": (schedule.test_sla_task_is_idempotent_on_double_run, ()),
    "TC-021": (trace.test_r2_02_03_04_07_queue_ordering_replacement_mismatch_overflow_and_bounds, ("stub_iam",)),
    "TC-022": (journeys.test_journey_bw_psm_01_internal_stock_fulfilment, ("stub_iam",)),
    "TC-023": (domain.test_duplicate_detection_matches_within_window_only, ()),
    "TC-024": (journeys.test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial, ("stub_iam",)),
    "TC-025": (domain.test_three_way_match_and_payment_release_rules, ()),
    "TC-026": (journeys.test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial, ("stub_iam",)),
    "TC-027": (domain.test_three_way_match_and_payment_release_rules, ()),
    "TC-028": (trace.test_discrepancy_resolution_return_replacement_and_communication, ()),
    "TC-029": (access.test_both_gates_enforced_separately, ("stub_iam",)),
    "TC-030": (access.test_both_gates_enforced_separately, ("stub_iam",)),
    "TC-031": (trace.test_http_endpoints_invoices_reports_schedules_audit_notifications_policy, ("stub_iam",)),
    "TC-032": (journeys.test_journey_bw_psm_06_07_08_10_discrepancy_modify_transfer_and_audit, ("stub_iam",)),
    "TC-033": (journeys.test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial, ("stub_iam",)),
    "TC-034": (journeys.test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial, ("stub_iam",)),
    "TC-035": (journeys.test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial, ("stub_iam",)),
    "TC-036": (domain.test_three_way_match_and_payment_release_rules, ()),
    "TC-037": (journeys.test_journey_bw_psm_03_05_high_value_final_approval_and_tender, ("stub_iam",)),
    "TC-038": (journeys.test_journey_bw_psm_03_05_high_value_final_approval_and_tender, ("stub_iam",)),
    "TC-039": (trace.test_reports_all_types_filters_scoping_and_throttle_429, ("stub_iam", "monkeypatch")),
    "TC-040": (access.test_both_gates_enforced_separately, ("stub_iam",)),
    "TC-041": (schedule.test_scheduled_report_task_is_idempotent_and_blocks_revoked_role, ()),
    "TC-042": (journeys.test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial, ("stub_iam",)),
    "TC-043": (journeys.test_journey_bw_psm_01_internal_stock_fulfilment, ("stub_iam",)),
    "TC-044": (adversarial.test_unresolved_discrepancy_blocks_stock_posting_and_second_replacement, ()),
    "TC-045": (journeys.test_journey_bw_psm_06_07_08_10_discrepancy_modify_transfer_and_audit, ("stub_iam",)),
    "TC-046": (trace.test_transfers_cancel_stock_adjustments_vendor_updates_and_approvals, ()),
    "TC-047": (adversarial.test_missing_policy_refuses_cleanly_with_409_not_500, ("stub_iam",)),
}

_design_path = Path(__file__).resolve().parents[5] / "docs" / "09-psm" / "spec-tests" / "BR_DESIGN.json"
_DESIGNS = json.loads(_design_path.read_text(encoding="utf-8"))
assert len(_DESIGNS) == 47
assert set(_SCENARIOS) == {design["test_id"] for design in _DESIGNS}


def _make_case(design, scenario, fixture_names):
    test_id = design["test_id"]
    source_id = design["source_id"]

    def test_case(request):
        fixture_values = [request.getfixturevalue(name) for name in fixture_names]
        scenario(*fixture_values)

    test_case.__name__ = "test_" + test_id.lower().replace("-", "_")
    test_case.__doc__ = f"{test_id}; source_id: {source_id}. {design['purpose']}"
    return test_case


for _design in _DESIGNS:
    _scenario, _fixtures = _SCENARIOS[_design["test_id"]]
    globals()["test_" + _design["test_id"].lower().replace("-", "_")] = _make_case(
        _design, _scenario, _fixtures
    )
