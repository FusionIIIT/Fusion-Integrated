from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from modules.iaa.api.views import csv_safe
from modules.iaa.domain.rules import eligible_steps, missing_submission, overdue


def test_incomplete_expense_draft_lists_missing_fields():
    row = SimpleNamespace(
        kind="expense", request_type="", department="", description="", amount=None, documents=[]
    )
    assert missing_submission(row) == [
        "request_type",
        "department",
        "description",
        "amount",
        "documents",
    ]


def test_optional_documents_policy_and_decimal_amount():
    row = SimpleNamespace(
        kind="expense",
        request_type="voucher",
        department="CSE",
        description="x",
        amount=Decimal("0.01"),
        documents=[],
    )
    assert missing_submission(row, require_documents=False) == []


def test_self_approval_is_removed_without_modifying_configured_steps():
    steps = [{"user_id": 1, "role": "HoD"}, {"user_id": 2, "role": "Dean"}]
    assert eligible_steps(steps, 1) == [steps[1]]
    assert len(steps) == 2


def test_timeout_is_strictly_after_configured_limit():
    assigned = datetime(2027, 1, 1)
    assert not overdue(assigned, 24, assigned + timedelta(hours=24))
    assert overdue(assigned, 24, assigned + timedelta(hours=24, seconds=1))
    assert not overdue(None, 24, assigned)


@pytest.mark.parametrize("value", ["=SUM(A1:A2)", "+cmd", "-10", "@evil", "  =evil", "\t=evil"])
def test_csv_formula_cells_are_escaped(value):
    assert csv_safe(value).startswith("'")


def test_plain_csv_values_remain_plain():
    assert csv_safe("CSE") == "CSE"
    assert csv_safe(None) == ""
