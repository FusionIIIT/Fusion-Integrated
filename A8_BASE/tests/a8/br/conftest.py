"""Fixtures for tests/a8/br (BR_DESIGN.json executable tests).

ASSUMPTION: `principal` is a minimal stand-in for the authenticated requestor
(services only need an id via `_get_principal_user_id`). If the existing Fusion
test infrastructure (tests/a8/uc/conftest.py) already provides a principal /
user factory, replace this fixture with that one - no test body needs to change.
"""
import uuid
from datetime import date
from types import SimpleNamespace

import pytest

from modules.psm.models import StockItem
from modules.psm.services import create_indent, create_vendor, verify_vendor, create_purchase_order


@pytest.fixture
def principal():
    return SimpleNamespace(id=1001, pk=1001, user_id=1001)


@pytest.fixture
def make_indent(principal):
    def _make(**overrides):
        data = dict(
            item_details="Laptop 16GB",
            quantity=10,
            estimated_cost="50000.00",
            justification="Lab upgrade",
        )
        data.update(overrides)
        return create_indent(principal=principal, **data)
    return _make


@pytest.fixture
def make_stock():
    def _make(central=0, department=0, reserved=0):
        return StockItem.objects.create(
            item_code=f"ITM-{uuid.uuid4().hex[:8]}",
            name="Test item",
            department="CSE",
            central_stock=central,
            department_stock=department,
            reserved_stock=reserved,
        )
    return _make


@pytest.fixture
def make_vendor():
    def _make(verified=True):
        v = create_vendor(
            name="Acme Supplies",
            gst_number=uuid.uuid4().hex[:15].upper(),
            bank_account_number="1234567890",
            bank_ifsc="HDFC0001234",
            compliance_docs_url="http://docs.example/acme",
        )
        return verify_vendor(vendor_id=v.id) if verified else v
    return _make


@pytest.fixture
def make_po(make_indent, make_vendor):
    def _make(quantity=100):
        indent = make_indent(quantity=quantity)
        vendor = make_vendor(verified=True)
        po = create_purchase_order(
            indent_id=indent.id,
            vendor_id=vendor.id,
            procurement_method="DIRECT",
            total_cost="1000.00",
            delivery_schedule=date.today(),
        )
        return indent, po
    return _make
