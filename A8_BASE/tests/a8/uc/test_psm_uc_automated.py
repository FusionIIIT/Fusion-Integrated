"""A8 PSM use-case tests executed against the real indent write services.

Source: frozen UC_DESIGN.json. Every test carries its test_id and source_id in
its name and docstring. Nothing under test is mocked; preconditions that need
an arbitrary workflow state are seeded through the ORM (``make_indent``).
"""

from decimal import Decimal

import pytest

from core.api.exceptions import BadRequestError
from modules.psm.models import Indent, IndentVersion
from modules.psm.services.indents import (
    create_indent,
    modify_indent,
    transition_indent,
    withdraw_indent,
)

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------
# UC-001 Submit Indent
# --------------------------------------------------------------------------
def test_TC_002__UC_001_Alternative_A1_missing_mandatory_info_blocks_submission(
    requestor, err_text
):
    """test_id=TC-002 | source_id=UC-001 Alternative A1

    Submission with a mandatory field (justification) omitted is blocked; the
    missing field is identified; no indent ID is assigned, nothing is stored.
    """
    with pytest.raises(BadRequestError) as exc:
        create_indent(
            principal=requestor,
            item_details="A4 paper reams",
            quantity=10,
            estimated_cost="1500.00",
            justification=None,
        )

    assert "justification" in err_text(exc).lower()
    assert Indent.objects.count() == 0
    assert IndentVersion.objects.count() == 0


def test_TC_003__UC_001_Alternative_A2_potential_duplicate_flagged_not_merged(
    requestor, make_indent, other_user_id
):
    """test_id=TC-003 | source_id=UC-001 Alternative A2

    A new indent matching an existing active indent is flagged as a potential
    duplicate; it is not merged/cancelled and the existing indent is unchanged.
    """
    existing = make_indent(
        status="SUBMITTED",
        requestor_id=other_user_id,
        item_details="Laptop Dell 5420",
        estimated_cost=Decimal("50000.00"),
    )
    before = Indent.objects.filter(pk=existing.pk).values().get()

    new = create_indent(
        principal=requestor,
        item_details="  laptop dell 5420 ",
        quantity=1,
        estimated_cost="51000.00",  # within the 5% tolerance
        justification="Replacement laptop",
    )

    new.refresh_from_db()
    assert new.is_duplicate is True  # traceably flagged for review
    assert new.status == "SUBMITTED"  # not cancelled / merged
    assert Indent.objects.count() == 2  # nothing merged away

    after = Indent.objects.filter(pk=existing.pk).values().get()
    assert after == before  # existing indent unchanged (incl. is_duplicate, status)


# --------------------------------------------------------------------------
# UC-005 Withdraw / Cancel Indent
# --------------------------------------------------------------------------
def test_TC_012__UC_005_Alternative_A1_withdraw_blocked_in_non_permissible_state(
    requestor, make_indent, ref
):
    """test_id=TC-012 | source_id=UC-005 Alternative A1

    Withdraw on an indent in a non-permissible state (APPROVED, terminal) is
    blocked and the indent is left unchanged.
    """
    indent = make_indent(status="APPROVED", requestor_id=101)
    before = Indent.objects.filter(pk=indent.pk).values().get()

    with pytest.raises(BadRequestError):
        withdraw_indent(principal=requestor, indent_id=ref(indent))

    after = Indent.objects.filter(pk=indent.pk).values().get()
    assert after["status"] == "APPROVED"
    assert after == before


# --------------------------------------------------------------------------
# Rejection requires justification (BR-PSM-005)
# --------------------------------------------------------------------------
def _assert_rejection_needs_justification(principal, indent, ref):
    # attempt without justification -> refused, state untouched
    with pytest.raises(BadRequestError):
        transition_indent(
            principal=principal,
            indent_id=ref(indent),
            target_state="REJECTED",
            justification="",
        )
    indent.refresh_from_db()
    assert indent.status != "REJECTED"
    assert not indent.rejection_justification
    original_status = indent.status

    # attempt with justification -> rejected, reason persisted
    reason = "Not aligned with approved budget"
    result = transition_indent(
        principal=principal,
        indent_id=ref(indent),
        target_state="REJECTED",
        justification=reason,
    )
    indent.refresh_from_db()
    assert original_status != "REJECTED"
    assert result.status == "REJECTED"
    assert indent.status == "REJECTED"
    assert indent.rejection_justification == reason


def test_TC_026__UC_011_Alternative_A1_dept_admin_rejection_requires_justification(
    requestor, make_indent, ref
):
    """test_id=TC-026 | source_id=UC-011 Alternative A1

    Submitted indent in Department Admin review: rejection without
    justification is refused; with justification it is rejected with the reason
    stored.
    """
    indent = make_indent(status="SUBMITTED", requestor_id=101)
    _assert_rejection_needs_justification(requestor, indent, ref)


def test_TC_029__UC_012_Alternative_A1_director_rejection_requires_justification(
    requestor, make_indent, ref
):
    """test_id=TC-029 | source_id=UC-012 Alternative A1

    Indent routed for final review (AWAITING_FINAL_APPROVAL): rejection without
    justification is refused; with justification it enters Rejected.
    """
    indent = make_indent(status="AWAITING_FINAL_APPROVAL", requestor_id=101)
    _assert_rejection_needs_justification(requestor, indent, ref)


def test_TC_039__UC_016_Alternative_A2_dept_head_rejection_requires_justification(
    requestor, make_indent, ref
):
    """test_id=TC-039 | source_id=UC-016 Alternative A2

    Indent routed to Department Head (DEPT_REVIEWED): rejection without
    justification is refused; with justification it is rejected and recorded.
    """
    indent = make_indent(status="DEPT_REVIEWED", requestor_id=101)
    _assert_rejection_needs_justification(requestor, indent, ref)


# --------------------------------------------------------------------------
# UC-023 Modify Indent
# --------------------------------------------------------------------------
def test_TC_053__UC_023_Alternative_A1_modify_blocked_in_non_modifiable_state(
    requestor, make_indent, ref
):
    """test_id=TC-053 | source_id=UC-023 Alternative A1

    Modify on an indent in a non-modifiable state (STOCK_CHECKED) is blocked;
    the indent (and its version history) is unchanged.
    """
    indent = make_indent(status="STOCK_CHECKED", requestor_id=101)
    before = Indent.objects.filter(pk=indent.pk).values().get()
    versions_before = IndentVersion.objects.filter(indent=indent).count()

    with pytest.raises(BadRequestError):
        modify_indent(principal=requestor, indent_id=ref(indent), quantity=99)

    assert Indent.objects.filter(pk=indent.pk).values().get() == before
    assert IndentVersion.objects.filter(indent=indent).count() == versions_before


def test_TC_054__UC_023_Alternative_A2_failed_validation_prevents_resubmission(
    requestor, ref
):
    """test_id=TC-054 | source_id=UC-023 Alternative A2

    Modifying a submitted indent leaving a mandatory field empty is rejected;
    the prior active version and state stay intact.
    """
    indent = create_indent(
        principal=requestor,
        item_details="Whiteboard markers",
        quantity=20,
        estimated_cost="800.00",
        justification="Classroom use",
    )
    before = Indent.objects.filter(pk=indent.pk).values().get()
    versions_before = IndentVersion.objects.filter(indent=indent).count()

    with pytest.raises(BadRequestError):
        modify_indent(principal=requestor, indent_id=ref(indent), justification="   ")

    after = Indent.objects.filter(pk=indent.pk).values().get()
    assert after == before
    assert after["status"] == "SUBMITTED"
    assert after["current_version"] == 1
    assert IndentVersion.objects.filter(indent=indent).count() == versions_before
