"""A8 UC tests: stock, reservation, transfer (UC-007/009/017/021)."""

import pytest

from core.api.exceptions import BadRequestError, NotFoundError
from modules.psm.contracts import get_stock_items
from modules.psm.domain.rules import determine_procurement_routing
from modules.psm.models import StockItem, StockTransfer
from modules.psm.selectors import get_allocable_stock
from modules.psm.services import (
    initiate_stock_transfer,
    issue_internal_stock,
    reserve_stock,
)

pytestmark = pytest.mark.django_db


def test_tc_013_uc007_main_flow_reserve_when_sufficient(make_stock_item):
    """TC-013 | PSM-UC-007 Main Flow"""
    item = make_stock_item(central_stock=10, department_stock=5, reserved_stock=3)
    assert get_allocable_stock(item.id) == 12
    reserve_stock(stock_item_id=item.id, quantity=5)
    item.refresh_from_db()
    assert item.reserved_stock == 8
    assert get_allocable_stock(item.id) == 7


def test_tc_014_uc007_main_flow_external_procurement_when_insufficient(make_stock_item):
    """TC-014 | PSM-UC-007 Main Flow (insufficient stock)"""
    item = make_stock_item(central_stock=0, department_stock=0)
    assert get_allocable_stock(item.id) == 0
    assert determine_procurement_routing(10, get_allocable_stock(item.id)) == "EXTERNAL_PROCUREMENT"
    with pytest.raises(BadRequestError):
        reserve_stock(stock_item_id=item.id, quantity=10)
    item.refresh_from_db()
    assert item.reserved_stock == 0


def test_tc_015_uc007_alt_a1_partial_availability_no_split(make_stock_item):
    """TC-015 | PSM-UC-007 Alternative A1"""
    item = make_stock_item(central_stock=4, department_stock=0)
    assert get_allocable_stock(item.id) == 4
    assert determine_procurement_routing(10, 4) == "EXTERNAL_PROCUREMENT"
    with pytest.raises(BadRequestError):
        reserve_stock(stock_item_id=item.id, quantity=10)
    item.refresh_from_db()
    assert item.reserved_stock == 0


def test_tc_016_uc007_alt_a2_stock_records_unavailable(make_indent):
    """TC-016 | PSM-UC-007 Alternative A2"""
    ind = make_indent()
    missing_id = 999999
    assert get_allocable_stock(missing_id) == 0
    with pytest.raises(NotFoundError):
        reserve_stock(stock_item_id=missing_id, quantity=1)
    ind.refresh_from_db()
    assert ind.status == "SUBMITTED"
    assert StockItem.objects.count() == 0


def test_tc_021_uc009_alt_a1_issue_blocked_when_reservation_invalid(make_indent, make_stock_item):
    """TC-021 | PSM-UC-009 Alternative A1

    Reserved stock was invalidated by an inventory correction (stock now 0).
    Expected: issue cannot proceed and no dispatch/approved state is recorded.
    """
    item = make_stock_item(central_stock=10, department_stock=0, reserved_stock=10)
    StockItem.objects.filter(pk=item.pk).update(central_stock=0)
    ind = make_indent(quantity=10)
    with pytest.raises((BadRequestError, NotFoundError)):
        issue_internal_stock(indent_id=ind.id, stock_item_id=item.id)
    ind.refresh_from_db()
    assert ind.status == "SUBMITTED"


def test_tc_040_uc017_main_flow_view_stock_without_change(make_stock_item):
    """TC-040 | PSM-UC-017 Main Flow"""
    item = make_stock_item(central_stock=10, department_stock=5, reserved_stock=2)
    rows = get_stock_items([item.item_code])
    assert rows[0]["central_stock"] == 10
    assert rows[0]["department_stock"] == 5
    assert rows[0]["reserved_stock"] == 2
    assert rows[0]["allocable_stock"] == 13
    item.refresh_from_db()
    assert (item.central_stock, item.department_stock, item.reserved_stock) == (10, 5, 2)


def test_tc_041_uc017_alt_a1_stock_info_unavailable(make_indent):
    """TC-041 | PSM-UC-017 Alternative A1"""
    ind = make_indent()
    assert get_stock_items(["NO-SUCH-CODE"]) == []
    ind.refresh_from_db()
    assert ind.status == "SUBMITTED"


def test_tc_049_uc021_main_flow_transfer_request_created(make_stock_item):
    """TC-049 | PSM-UC-021 Main Flow"""
    item = make_stock_item(central_stock=10, department_stock=0)
    t = initiate_stock_transfer(
        source_dept="CSE", dest_dept="ECE", stock_item_id=item.id, quantity=6
    )
    assert t.status == "REQUESTED"
    assert t.transfer_id.startswith("TRF-")
    assert (t.source_department, t.destination_department, t.quantity) == ("CSE", "ECE", 6)


def test_tc_050_uc021_alt_a1_transfer_blocked_unavailable_quantity(make_stock_item):
    """TC-050 | PSM-UC-021 Alternative A1"""
    item = make_stock_item(central_stock=3, department_stock=0)
    with pytest.raises(BadRequestError):
        initiate_stock_transfer(
            source_dept="CSE", dest_dept="ECE", stock_item_id=item.id, quantity=4
        )
    assert StockTransfer.objects.count() == 0
