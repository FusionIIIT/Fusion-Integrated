"""Phase-2 regressions for hierarchy integrity and reserved leave balances."""
from decimal import Decimal

import pytest

from core.api.exceptions import BadRequestError
from modules.leave.models import LedgerEntry, OrgUnit
from modules.leave.services import administration
from modules.leave.tests.conftest import ADMIN, HEAD, OTHER, STAFF
from modules.leave.tests.test_workflow import act, apply

pytestmark = pytest.mark.django_db


def test_unit_cannot_be_reparented_under_its_descendant(world):
    before = OrgUnit.objects.get(name="Academics")
    with pytest.raises(BadRequestError):
        administration.save_unit("Academics", HEAD, "CSE")
    before.refresh_from_db()
    assert before.parent_id is None


def test_existing_parent_cycle_is_rejected_without_hanging(world):
    a = OrgUnit.objects.create(name="A")
    b = OrgUnit.objects.create(name="B", parent=a)
    OrgUnit.objects.filter(pk=a.pk).update(parent=b)
    with pytest.raises(BadRequestError):
        administration.save_unit("New unit", HEAD, "A")
    assert not OrgUnit.objects.filter(name="New unit").exists()


def test_correction_cannot_spend_balance_reserved_by_pending_requests(world, as_user):
    pk = apply(as_user(STAFF)).json()["id"]
    before = LedgerEntry.objects.count()
    response = as_user(OTHER, perms=ADMIN).post("/api/v1/leave/records/corrections", {
        "user_id": STAFF, "category": "CL", "year": 2027, "days": "-7",
        "note": "Correction must preserve the two days already reserved.",
    }, format="json")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "reserved_balance"
    assert LedgerEntry.objects.count() == before
    assert act(as_user(HEAD), pk, "review", decision="approve").status_code == 200


def test_correction_can_use_exactly_the_unreserved_balance(world, as_user):
    pk = apply(as_user(STAFF)).json()["id"]
    response = as_user(OTHER, perms=ADMIN).post("/api/v1/leave/records/corrections", {
        "user_id": STAFF, "category": "CL", "year": 2027, "days": "-6",
        "note": "Leave the pending request funded.",
    }, format="json")
    assert response.status_code == 201
    assert act(as_user(HEAD), pk, "review", decision="approve").status_code == 200
    from modules.leave.selectors.accounts import balances

    assert balances(STAFF, 2027)["CL"] == Decimal(0)
