"""Executable tests for the frozen PSM workflow designs."""

import json
from pathlib import Path

import pytest

from modules.psm.tests import test_coverage_and_traceability as trace
from modules.psm.tests import test_journeys as journeys

pytestmark = pytest.mark.django_db

_DESIGN_PATH = Path(__file__).resolve().parents[5] / "docs" / "09-psm" / "spec-tests" / "WF_DESIGN.json"
_DESIGNS = json.loads(_DESIGN_PATH.read_text(encoding="utf-8"))
_SCENARIOS = {
    "PSM-WF-01": (journeys.test_journey_bw_psm_01_internal_stock_fulfilment, ("stub_iam",)),
    "PSM-WF-02": (
        journeys.test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial,
        ("stub_iam",),
    ),
    "PSM-WF-03": (
        journeys.test_journey_bw_psm_03_05_high_value_final_approval_and_tender,
        ("stub_iam",),
    ),
    "PSM-WF-04": (
        trace.test_r1_04_discrepancy_resolve_atomic_inventory_and_accounting_adjustments,
        (),
    ),
    "PSM-WF-05": (
        journeys.test_journey_bw_psm_06_07_08_10_discrepancy_modify_transfer_and_audit,
        ("stub_iam",),
    ),
    "PSM-WF-06": (
        journeys.test_journey_bw_psm_06_07_08_10_discrepancy_modify_transfer_and_audit,
        ("stub_iam",),
    ),
    "PSM-WF-07": (
        journeys.test_journey_bw_psm_06_07_08_10_discrepancy_modify_transfer_and_audit,
        ("stub_iam",),
    ),
    "PSM-WF-08": (
        journeys.test_journey_bw_psm_02_04_direct_procurement_to_payment_and_partial,
        ("stub_iam",),
    ),
}


def _make_case(design, scenario, fixture_names):
    test_id = design["test_id"]
    source_id = design["source_id"]

    def test_case(request):
        fixture_values = [request.getfixturevalue(name) for name in fixture_names]
        scenario(*fixture_values)

    test_case.__name__ = "test_" + test_id.lower().replace("-", "_")
    test_case.__doc__ = f"{test_id}; source_id: {source_id}. {design['purpose']}"
    return test_case


assert len(_DESIGNS) == 8
assert set(_SCENARIOS) == {design["test_id"] for design in _DESIGNS}

for _design in _DESIGNS:
    _scenario, _fixtures = _SCENARIOS[_design["test_id"]]
    globals()["test_" + _design["test_id"].lower().replace("-", "_")] = _make_case(
        _design, _scenario, _fixtures
    )
