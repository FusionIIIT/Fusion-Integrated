"""The two frozen UC cases that were absent from the source test export."""

import pytest


@pytest.mark.skip(
    reason="NOT_AUTOMATED: no scheduled-report model or service exists in modules.psm"
)
def test_tc_086_uc035_alternative_a1():
    """test_id=TC-086 | source_id=PSM-UC-035 Alternative A1"""


@pytest.mark.skip(
    reason="NOT_AUTOMATED: no scheduled-report model or service exists in modules.psm"
)
def test_tc_087_uc035_alternative_a2():
    """test_id=TC-087 | source_id=PSM-UC-035 Alternative A2"""
