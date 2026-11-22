"""WF end-to-end success paths (TC-WF-001..012)."""

import pytest

REASON = (
    "NOT_AUTOMATED: the implemented RSPC interfaces drive only the Proposal flow "
    "(draft, submitted_hod, endorsed_hod, approved_dean) and project closure; the "
    "Admin verification and Forward-to-Director steps and this request type's own "
    "states do not exist, so the path cannot be driven"
)


@pytest.mark.skip(reason=REASON)
def test_tc_wf_001():
    """TC-WF-001 | source_id: BW-RSPC-01 main path (also exercises CW-RSPC-01 rows 1,2,4,6)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_002():
    """TC-WF-002 | source_id: BW-RSPC-02 main path (also exercises CW-RSPC-01 rows 7,9)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_003():
    """TC-WF-003 | source_id: BW-RSPC-03 main path (also exercises CW-RSPC-02 rows 1,2,5,7)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_004():
    """TC-WF-004 | source_id: BW-RSPC-04 main path (also exercises CW-RSPC-02 rows 8,10)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_005():
    """TC-WF-005 | source_id: BW-RSPC-05 main path (also exercises CW-RSPC-03 rows 1,2,4,5)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_006():
    """TC-WF-006 | source_id: BW-RSPC-06 main path (also exercises CW-RSPC-03 rows 6,8)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_007():
    """TC-WF-007 | source_id: BW-RSPC-07 main path (also exercises CW-RSPC-04 rows 1,2,4)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_008():
    """TC-WF-008 | source_id: BW-RSPC-08 main path (also exercises CW-RSPC-04 rows 5,7)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_009():
    """TC-WF-009 | source_id: BW-RSPC-09 main path (also exercises CW-RSPC-05 rows 1,2,4)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_010():
    """TC-WF-010 | source_id: BW-RSPC-10 main path (also exercises CW-RSPC-05 rows 5,7)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_011():
    """TC-WF-011 | source_id: BW-RSPC-11 main path (also exercises CW-RSPC-06 rows 1,2,4)"""


@pytest.mark.skip(reason=REASON)
def test_tc_wf_012():
    """TC-WF-012 | source_id: BW-RSPC-12 main path (also exercises CW-RSPC-06 rows 5,7)"""

