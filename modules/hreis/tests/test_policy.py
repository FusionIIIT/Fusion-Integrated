from decimal import Decimal

import pytest

from modules.hreis.domain.policy import HRPolicy


def test_authority_order_is_preserved():
    assert HRPolicy.validate_authorities(["HOD", "Director"]) == ("HOD", "Director")


@pytest.mark.parametrize("roles", [[], ["HOD", "HOD"], ["HOD", ""], [1], None])
def test_invalid_authorities_rejected(roles):
    with pytest.raises(ValueError):
        HRPolicy.validate_authorities(roles)


def test_leave_balance_reduces_by_requested_days():
    assert HRPolicy.available_leave({"casual": "5.5"}, "casual", Decimal("2.5")) == Decimal("3.0")


@pytest.mark.parametrize("days", [Decimal("-1"), Decimal("6"), Decimal("NaN")])
def test_invalid_leave_duration_rejected(days):
    with pytest.raises(ValueError):
        HRPolicy.available_leave({"casual": "5"}, "casual", days)


def test_claim_document_references_required():
    assert not HRPolicy.valid_claim_documents([])
    assert not HRPolicy.valid_claim_documents([""])
    assert HRPolicy.valid_claim_documents(["archive/ltc-application.pdf"])
