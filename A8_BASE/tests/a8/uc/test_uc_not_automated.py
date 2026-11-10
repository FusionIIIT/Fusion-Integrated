"""A8 UC tests that cannot be automated with the available backend interfaces.

Each is a skipped pytest test: NOT_AUTOMATED: <reason>.
"""

import pytest


@pytest.mark.skip(reason="NOT_AUTOMATED: no role-restricted audit/history entries are modelled; selectors only scope indents by requestor")
def test_tc_009_uc003_alternative_a1():
    """TC-009 | PSM-UC-003 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: indent has no SLA reminder/escalation or discrepancy status fields")
def test_tc_010_uc003_alternative_a2():
    """TC-010 | PSM-UC-003 Alternative A2"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no stock-adjustment service, ledger or audit interface exists")
def test_tc_017_uc008_main_flow():
    """TC-017 | PSM-UC-008 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no stock-adjustment service exists")
def test_tc_018_uc008_alternative_a1():
    """TC-018 | PSM-UC-008 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no stock-adjustment service exists; PSM services take no authorization argument")
def test_tc_019_uc008_alternative_a2():
    """TC-019 | PSM-UC-008 Alternative A2"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no picking/dispatch service exists; issue_internal_stock posts final deduction and releases reservation at once")
def test_tc_020_uc009_main_flow():
    """TC-020 | PSM-UC-009 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no reporting/export service exists in modules.psm")
def test_tc_022_uc010_main_flow():
    """TC-022 | PSM-UC-010 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no reporting/export service exists in modules.psm")
def test_tc_023_uc010_alternative_a1():
    """TC-023 | PSM-UC-010 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no invoice/payment model or service exists in modules.psm (only three_way_match pure function)")
def test_tc_032_uc013_alternative_a2():
    """TC-032 | PSM-UC-013 Alternative A2"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no auditor retrieval/export service exists")
def test_tc_033_uc014_main_flow():
    """TC-033 | PSM-UC-014 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no auditor scope service exists")
def test_tc_034_uc014_alternative_a1():
    """TC-034 | PSM-UC-014 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no reporting/export service exists in modules.psm")
def test_tc_035_uc015_main_flow():
    """TC-035 | PSM-UC-015 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no reporting/export service exists in modules.psm")
def test_tc_036_uc015_alternative_a1():
    """TC-036 | PSM-UC-015 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: TRANSITION_MATRIX has no backward edge to return an indent to the employee, and DEPT_REVIEWED is not modifiable")
def test_tc_038_uc016_alternative_a1():
    """TC-038 | PSM-UC-016 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no vendor update service and no vendor version-history table exist (only a version counter incremented by verify_vendor)")
def test_tc_044_uc019_alternative_a2():
    """TC-044 | PSM-UC-019 Alternative A2"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no discrepancy-case model or service exists (GoodsReceiptNote has only has_discrepancy flag)")
def test_tc_045_uc020_main_flow():
    """TC-045 | PSM-UC-020 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no discrepancy-case model or service exists (GoodsReceiptNote has only has_discrepancy flag)")
def test_tc_047_uc020_alternative_a2():
    """TC-047 | PSM-UC-020 Alternative A2"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no tender/bid/committee models or services exist")
def test_tc_051_uc022_main_flow():
    """TC-051 | PSM-UC-022 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no tender/bid/committee models or services exist")
def test_tc_052_uc022_alternative_a1():
    """TC-052 | PSM-UC-022 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no repeat/reorder service exists")
def test_tc_056_uc024_main_flow():
    """TC-056 | PSM-UC-024 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no repeat/reorder service exists")
def test_tc_057_uc024_alternative_a1():
    """TC-057 | PSM-UC-024 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no PO status/schedule update service exists")
def test_tc_065_uc027_main_flow():
    """TC-065 | PSM-UC-027 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no PO status/schedule update service exists")
def test_tc_066_uc027_alternative_a1():
    """TC-066 | PSM-UC-027 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no invoice/payment model or service exists in modules.psm (only three_way_match pure function)")
def test_tc_070_uc029_main_flow():
    """TC-070 | PSM-UC-029 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no invoice/payment model or service exists in modules.psm (only three_way_match pure function)")
def test_tc_071_uc029_alternative_a1():
    """TC-071 | PSM-UC-029 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no invoice/payment model or service exists in modules.psm (only three_way_match pure function)")
def test_tc_072_uc029_alternative_a2():
    """TC-072 | PSM-UC-029 Alternative A2"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no invoice/payment model or service exists in modules.psm (only three_way_match pure function)")
def test_tc_073_uc029_alternative_a3():
    """TC-073 | PSM-UC-029 Alternative A3"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no dashboard service exists")
def test_tc_074_uc030_main_flow():
    """TC-074 | PSM-UC-030 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no dashboard service exists")
def test_tc_075_uc030_alternative_a1():
    """TC-075 | PSM-UC-030 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no scheduled-report model or service exists in modules.psm")
def test_tc_076_uc031_main_flow():
    """TC-076 | PSM-UC-031 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no scheduled-report model or service exists in modules.psm")
def test_tc_077_uc031_alternative_a1():
    """TC-077 | PSM-UC-031 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no discrepancy-case model or service exists (GoodsReceiptNote has only has_discrepancy flag)")
def test_tc_078_uc032_main_flow():
    """TC-078 | PSM-UC-032 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no discrepancy-case model or service exists (GoodsReceiptNote has only has_discrepancy flag)")
def test_tc_079_uc032_alternative_a1():
    """TC-079 | PSM-UC-032 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no discrepancy-case model or service exists (GoodsReceiptNote has only has_discrepancy flag)")
def test_tc_080_uc032_alternative_a2():
    """TC-080 | PSM-UC-032 Alternative A2"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no transfer dispatch/receipt-confirmation service exists (only initiate_stock_transfer)")
def test_tc_081_uc033_main_flow():
    """TC-081 | PSM-UC-033 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no transfer dispatch/receipt-confirmation service exists (only initiate_stock_transfer)")
def test_tc_082_uc033_alternative_a1():
    """TC-082 | PSM-UC-033 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no transfer dispatch/receipt-confirmation service exists (only initiate_stock_transfer); no ledger model")
def test_tc_083_uc034_main_flow():
    """TC-083 | PSM-UC-034 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no transfer dispatch/receipt-confirmation service exists (only initiate_stock_transfer)")
def test_tc_084_uc034_alternative_a1():
    """TC-084 | PSM-UC-034 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no scheduled-report model or service exists in modules.psm")
def test_tc_085_uc035_main_flow():
    """TC-085 | PSM-UC-035 Main Flow"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no scheduled-report model or service exists in modules.psm")
def test_tc_086_uc035_alternative_a1():
    """TC-086 | PSM-UC-035 Alternative A1"""


@pytest.mark.skip(reason="NOT_AUTOMATED: no scheduled-report model or service exists in modules.psm")
def test_tc_087_uc035_alternative_a2():
    """TC-087 | PSM-UC-035 Alternative A2"""
