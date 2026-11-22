"""Shared fixtures for A8 PSM use-case tests (UC_DESIGN.json TC-001..TC-087)."""

import datetime
import itertools
from types import SimpleNamespace

import pytest

from modules.psm.models import Indent, StockItem
from modules.psm.services import (
    create_indent,
    create_purchase_order,
    create_vendor,
    verify_vendor,
)

_seq = itertools.count(1)


def _principal(user_id, active_role="", roles=()):
    return SimpleNamespace(
        user_id=user_id,
        id=user_id,
        active_role=active_role,
        roles=tuple(roles),
        is_superuser=False,
    )


@pytest.fixture
def employee():
    return _principal(101)


@pytest.fixture
def other_employee():
    return _principal(102)


@pytest.fixture
def dept_admin():
    return _principal(900, active_role="STORE_OFFICER")


@pytest.fixture
def director():
    return _principal(901, active_role="DIRECTOR")


@pytest.fixture
def ps_admin():
    return _principal(902, active_role="PS_ADMIN")


@pytest.fixture
def make_indent(employee):
    def _make(principal=None, **overrides):
        n = next(_seq)
        data = dict(
            item_details=f"Item {n}",
            quantity=10,
            estimated_cost="10000.00",
            justification="Required for lab work",
        )
        data.update(overrides)
        return create_indent(principal=principal or employee, **data)

    return _make


@pytest.fixture
def set_status():
    def _set(indent, status):
        Indent.objects.filter(pk=indent.pk).update(status=status)
        indent.refresh_from_db()
        return indent

    return _set


@pytest.fixture
def make_stock_item():
    def _make(**overrides):
        n = next(_seq)
        data = dict(
            item_code=f"ITM-{n:04d}",
            name=f"Stock item {n}",
            department="CSE",
            central_stock=10,
            department_stock=5,
            reserved_stock=0,
        )
        data.update(overrides)
        return StockItem.objects.create(**data)

    return _make


@pytest.fixture
def make_vendor():
    def _make(verified=True, **overrides):
        n = next(_seq)
        data = dict(
            name=f"Vendor {n}",
            gst_number=f"27AAAAA{n:04d}A1Z5",
            bank_account_number="123456789012",
            bank_ifsc="HDFC0001234",
            compliance_docs_url="https://docs.example/compliance.pdf",
        )
        data.update(overrides)
        vendor = create_vendor(**data)
        if verified:
            vendor = verify_vendor(vendor_id=vendor.id)
        return vendor

    return _make


@pytest.fixture
def make_po(make_indent, make_vendor, set_status):
    def _make(quantity=10, **kw):
        indent = make_indent(quantity=quantity)
        set_status(indent, "APPROVED")
        vendor = make_vendor(verified=True)
        po = create_purchase_order(
            indent_id=indent.id,
            vendor_id=vendor.id,
            procurement_method=kw.get("procurement_method", "DIRECT"),
            total_cost=kw.get("total_cost", "10000.00"),
            delivery_schedule=datetime.date(2026, 12, 31),
        )
        return po

    return _make
