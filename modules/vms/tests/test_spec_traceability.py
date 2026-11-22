"""Every active spec item is exercised by a test that names it.

The VMS spec (vms_srs/) has 47 business rules, 39 active use cases (UC-029 is retired and its
id is not reused) and 30 workflows (BW-VMS-01..23, CW-VMS-01..07). This guard fails when a
test rename or deletion leaves one of them with no test that cites it, so a spec item cannot
silently lose its coverage. A citation is the id in a test name, docstring or comment in any
of the accepted spellings: ``BR-112``, ``br_112``, ``UC-010``, ``uc_010``, ``BW-VMS-04``,
``bw_vms_04``, ``bw04``, ``CW-02``.

It proves a test *names* the item, not that the test is strong; the behaviour tests do that.
"""
import re
from pathlib import Path

import pytest

BUSINESS_RULES = ['037', '038', '049', '050', '051', '052', '053', '062', '073', '077', '082', '085', '096', '101', '105', '112', '116', '117', '118', '119', '120', '125', '126', '127', '128', '129', '130', '174', '181', '182', '183', '184', '185', '186', '187', '190', '191', '192', '193', '194', '195', '196', '197', '200', '202', '203', '211']
USE_CASES = ['001', '002', '003', '004', '005', '006', '007', '008', '009', '010', '011', '012', '013', '014', '015', '016', '017', '018', '019', '020', '021', '022', '023', '024', '025', '026', '027', '028', '030', '031', '032', '033', '034', '035', '036', '037', '038', '039', '040']   # UC-029 retired
BASIC_WORKFLOWS = list(range(1, 24))
COMPOSITE_WORKFLOWS = list(range(1, 8))

_HERE = Path(__file__).resolve()
_TEXT = "\n".join(p.read_text(encoding="utf-8")
                  for p in _HERE.parent.rglob("*.py") if p != _HERE)


def _cited(kind: str, number: int) -> bool:
    n = f"0*{number}"
    pattern = (rf"(?i)(?<![a-z0-9]){kind}[-_ ]?(?:vms[-_ ]?)?{n}(?![0-9])")
    return re.search(pattern, _TEXT) is not None


@pytest.mark.parametrize("number", BUSINESS_RULES)
def test_every_business_rule_is_cited_by_a_test(number):
    assert _cited("br", int(number)), f"VMS-BR-{number} has no test that names it"


@pytest.mark.parametrize("number", USE_CASES)
def test_every_active_use_case_is_cited_by_a_test(number):
    assert _cited("uc", int(number)), f"VMS-UC-{number} has no test that names it"


@pytest.mark.parametrize("number", BASIC_WORKFLOWS)
def test_every_basic_workflow_is_cited_by_a_test(number):
    assert _cited("bw", number), f"BW-VMS-{number:02d} has no test that names it"


@pytest.mark.parametrize("number", COMPOSITE_WORKFLOWS)
def test_every_composite_workflow_is_cited_by_a_test(number):
    assert _cited("cw", number), f"CW-VMS-{number:02d} has no test that names it"


def test_retired_uc_029_is_not_expected_to_have_a_test():
    assert "029" not in USE_CASES
