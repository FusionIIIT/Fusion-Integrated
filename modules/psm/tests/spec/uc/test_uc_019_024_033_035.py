"""Vendor, tender, versioning, transfer, and scheduled-report UC tests."""

from decimal import Decimal

import pytest
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import ConflictError, DomainError
from modules.psm.models import (
    Indent,
    IndentVersion,
    PsmAuditLog,
    PsmNotification,
    StockLedgerEntry,
    StockReservation,
    StockTransfer,
    Tender,
    VendorVersion,
)
from modules.psm.services import indents, policy, tenders, transfers, vendors

pytestmark = pytest.mark.django_db


def _actor(uid, role, department="CSE"):
    roles = {"deptadmin_cse": ("deptadmin_cse",), "ps_admin": ("ps_admin",)}
    return make_principal(
        user_id=uid,
        kind="staff" if role in roles or role.startswith("deptadmin_") else "faculty",
        active_role=role,
        roles=roles.get(role, (role,)),
        modules=("psm",),
    )


def _indent(uid=34001, *, item="Projector", quantity=2):
    return indents.create_indent(
        actor=_actor(uid, "faculty"),
        department="CSE",
        item_description=item,
        quantity=quantity,
        estimated_cost=Decimal("40000.00"),
        justification="Teaching lab",
    )


def _vendor(uid=34002, *, verified=False):
    actor = _actor(uid, "ps_admin")
    vendor = vendors.onboard_vendor(
        actor=actor,
        name="UC Test Vendor",
        gstin="23AABCU9603R1ZM",
        bank_account_number="1234567890",
        bank_ifsc="SBIN0001234",
        bank_name="SBI",
        compliance_documents=["GST"],
    )
    if verified:
        vendor = vendors.verify_vendor(actor=actor, vendor_id=vendor.pk)
    return vendor


def test_tc_019_main_psm_uc_019_main_success_scenario():
    """TC-019-MAIN; source_id: PSM-UC-019 Main Success Scenario."""
    policy.seed_default_policy()
    actor = _actor(34101, "ps_admin")
    vendor = vendors.onboard_vendor(actor=actor, name="Verified Co", gstin="23AABCU9603R1ZM",
        bank_account_number="1234567890", bank_ifsc="SBIN0001234", bank_name="SBI",
        compliance_documents=["GST"])
    verified = vendors.verify_vendor(actor=actor, vendor_id=vendor.pk)

    assert verified.is_verified
    assert VendorVersion.objects.filter(vendor=vendor, version=1).exists()
    assert VendorVersion.objects.filter(vendor=vendor, version=verified.version).exists()
    assert PsmAuditLog.objects.filter(action="vendor.verified", target_id=vendor.pk).exists()


def test_tc_019_a1_psm_uc_019_alternative_a1():
    """TC-019-A1; source_id: PSM-UC-019 Alternative A1."""
    policy.seed_default_policy()
    vendor = vendors.onboard_vendor(actor=_actor(34102, "ps_admin"), name="Incomplete Co")

    assert vendor.is_verified is False
    assert VendorVersion.objects.filter(vendor=vendor).count() == 1
    with pytest.raises(DomainError) as refused:
        vendors.verify_vendor(actor=_actor(34102, "ps_admin"), vendor_id=vendor.pk)
    assert refused.value.status_code == 422
    vendor.refresh_from_db()
    assert vendor.is_verified is False


def test_tc_019_a2_psm_uc_019_alternative_a2():
    """TC-019-A2; source_id: PSM-UC-019 Alternative A2."""
    policy.seed_default_policy()
    actor = _actor(34103, "ps_admin")
    vendor = vendors.onboard_vendor(actor=actor, name="Versioned Co")
    old_snapshot = VendorVersion.objects.get(vendor=vendor, version=1).snapshot

    changed = vendors.update_vendor(actor=actor, vendor_id=vendor.pk,
        contact_email="new@example.test", change_reason="Contact update")

    assert changed.version == 2
    assert VendorVersion.objects.get(vendor=vendor, version=1).snapshot == old_snapshot
    assert VendorVersion.objects.get(vendor=vendor, version=2).snapshot["contact_email"] == "new@example.test"


def test_tc_021_main_psm_uc_021_main_success_scenario():
    """TC-021-MAIN; source_id: PSM-UC-021 Main Success Scenario."""
    policy.seed_default_policy()
    from modules.psm.services import stock

    ps = _actor(34201, "ps_admin")
    item = stock.create_stock_item(actor=ps, sku="UC21-ITEM", name="Cables")
    source = stock.create_stock_location(actor=ps, code="UC21-SRC", name="CSE store", department="CSE")
    destination = stock.create_stock_location(actor=ps, code="UC21-DST", name="ECE store", department="ECE")
    stock.record_adjustment(actor=ps, item_id=item.pk, location_id=source.pk, quantity_delta=8,
        reason="Opening", entry_type="opening")
    transfer = transfers.request_transfer(actor=_actor(34202, "deptadmin_ece"), item_id=item.pk,
        source_location_id=source.pk, destination_location_id=destination.pk, quantity=3)

    assert transfer.status == "requested"
    assert transfer.transfer_number
    assert PsmAuditLog.objects.filter(action="transfer.requested", target_id=transfer.pk).exists()


def test_tc_021_a1_psm_uc_021_alternative_a1():
    """TC-021-A1; source_id: PSM-UC-021 Alternative A1."""
    policy.seed_default_policy()
    from modules.psm.services import stock

    ps = _actor(34211, "ps_admin")
    item = stock.create_stock_item(actor=ps, sku="UC21-A1", name="Cables")
    source = stock.create_stock_location(actor=ps, code="UC21-AS", name="CSE store", department="CSE")
    destination = stock.create_stock_location(actor=ps, code="UC21-AD", name="ECE store", department="ECE")
    stock.record_adjustment(actor=ps, item_id=item.pk, location_id=source.pk, quantity_delta=1,
        reason="Opening", entry_type="opening")
    before = StockTransfer.objects.count()

    with pytest.raises(ConflictError) as refused:
        transfers.request_transfer(actor=_actor(34212, "deptadmin_ece"), item_id=item.pk,
            source_location_id=source.pk, destination_location_id=destination.pk, quantity=2)
    assert refused.value.status_code == 409

    assert StockTransfer.objects.count() == before


def test_tc_022_a1_psm_uc_022_alternative_a1():
    """TC-022-A1; source_id: PSM-UC-022 Alternative A1."""
    from datetime import timedelta

    from modules.psm.domain import state_machine as sm

    policy.seed_default_policy()
    indent = _indent(34301)
    Indent.objects.filter(pk=indent.pk).update(status=sm.PROCUREMENT_AUTHORIZED,
        procurement_method="tender")
    tender = tenders.create_tender(actor=_actor(34302, "ps_admin"), indent_id=indent.pk,
        title="Lab equipment", scope="CSE", evaluation_criteria="Price and compliance",
        submission_deadline=timezone.now() + timedelta(days=3))
    published = tenders.publish_tender(actor=_actor(34302, "ps_admin"), tender_id=tender.pk)

    assert published.status == sm.TENDER_PUBLISHED
    assert published.bids.count() == 0
    assert not Tender.objects.filter(indent=indent, status=sm.TENDER_DRAFT).exclude(pk=tender.pk).exists()


def test_tc_023_main_psm_uc_023_main_success_scenario(stub_iam):
    """TC-023-MAIN; source_id: PSM-UC-023 Main Success Scenario."""
    from rest_framework.test import APIClient

    from conftest import make_session
    from modules.psm import registry

    policy.seed_default_policy()
    indent = _indent(34401)
    stub_iam(make_session(user_id=34401, kind="faculty", active_role="faculty", roles=("faculty",),
        modules=("psm",), permissions=tuple(registry.ROLE_GRANTS["faculty"])))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token uc-34401")
    response = client.patch(f"/api/v1/psm/indents/{indent.pk}",
        {"quantity": 3, "justification": "Updated lab requirement"}, format="json")

    assert response.status_code == 200, response.data
    indent.refresh_from_db()
    assert indent.version == 2 and indent.quantity == 3
    assert IndentVersion.objects.filter(indent=indent, version=1).exists()
    assert IndentVersion.objects.filter(indent=indent, version=2).exists()
    assert indent.status == "submitted"


def test_tc_023_a1_psm_uc_023_alternative_a1():
    """TC-023-A1; source_id: PSM-UC-023 Alternative A1."""
    from core.api.exceptions import ConflictError

    policy.seed_default_policy()
    actor = _actor(34411, "faculty")
    indent = _indent(34411)
    Indent.objects.filter(pk=indent.pk).update(status="po_issued")
    before = IndentVersion.objects.filter(indent=indent).count()

    with pytest.raises(ConflictError) as refused:
        indents.modify_indent(actor=actor, indent_id=indent.pk, quantity=5)
    assert refused.value.status_code == 409

    indent.refresh_from_db()
    assert indent.status == "po_issued" and indent.quantity == 2
    assert IndentVersion.objects.filter(indent=indent).count() == before


def test_tc_023_a2_psm_uc_023_alternative_a2():
    """TC-023-A2; source_id: PSM-UC-023 Alternative A2."""
    from core.api.exceptions import DomainError

    policy.seed_default_policy()
    actor = _actor(34412, "faculty")
    indent = _indent(34412)
    before = (indent.status, indent.quantity, indent.version, IndentVersion.objects.filter(indent=indent).count())

    with pytest.raises(DomainError) as refused:
        indents.modify_indent(actor=actor, indent_id=indent.pk, quantity=0)
    assert refused.value.status_code == 422

    indent.refresh_from_db()
    assert (indent.status, indent.quantity, indent.version, IndentVersion.objects.filter(indent=indent).count()) == before


def test_tc_024_main_psm_uc_024_main_success_scenario():
    """TC-024-MAIN; source_id: PSM-UC-024 Main Success Scenario."""
    policy.seed_default_policy()
    actor = _actor(34501, "faculty")
    original = _indent(34501)
    repeated = indents.repeat_as_draft(actor=actor, indent_id=original.pk)

    assert repeated.pk != original.pk
    assert repeated.status == "draft"
    assert repeated.repeated_from_indent_id == original.pk
    original.refresh_from_db()
    assert original.status == "submitted"
    assert original.version == 1


def test_tc_024_a1_psm_uc_024_alternative_a1():
    """TC-024-A1; source_id: PSM-UC-024 Alternative A1."""
    from core.api.exceptions import NotFoundError

    policy.seed_default_policy()
    actor = _actor(34511, "faculty")
    original = _indent(34512)
    before = Indent.objects.count()

    with pytest.raises(NotFoundError) as refused:
        indents.repeat_as_draft(actor=actor, indent_id=original.pk)
    assert refused.value.status_code == 404

    original.refresh_from_db()
    assert original.status == "submitted"
    assert Indent.objects.count() == before


def test_tc_033_main_psm_uc_033_main_success_scenario():
    """TC-033-MAIN; source_id: PSM-UC-033 Main Success Scenario."""
    policy.seed_default_policy()
    from modules.psm.services import stock

    ps = _actor(34601, "ps_admin")
    item = stock.create_stock_item(actor=ps, sku="UC33", name="Sensor")
    source = stock.create_stock_location(actor=ps, code="UC33-S", name="CSE", department="CSE")
    destination = stock.create_stock_location(actor=ps, code="UC33-D", name="ECE", department="ECE")
    stock.record_adjustment(actor=ps, item_id=item.pk, location_id=source.pk, quantity_delta=5,
        reason="Opening", entry_type="opening")
    requester = _actor(34602, "deptadmin_ece")
    transfer = transfers.request_transfer(actor=requester, item_id=item.pk,
        source_location_id=source.pk, destination_location_id=destination.pk, quantity=2)

    dispatched = transfers.dispatch_transfer(actor=_actor(34603, "deptadmin_cse"), transfer_id=transfer.pk)
    assert dispatched.status == "dispatched"
    assert StockReservation.objects.filter(transfer_id=transfer.pk, status="active", quantity=2).exists()
    assert PsmNotification.objects.filter(topic="transfer.dispatched", payload__transfer_id=transfer.pk).exists()


def test_tc_033_a1_psm_uc_033_alternative_a1():
    """TC-033-A1; source_id: PSM-UC-033 Alternative A1."""
    policy.seed_default_policy()
    from modules.psm.services import stock

    ps = _actor(34611, "deptadmin_cse")
    item = stock.create_stock_item(actor=ps, sku="UC33-A1", name="Sensor")
    source = stock.create_stock_location(actor=ps, code="UC33-AS", name="CSE", department="CSE")
    destination = stock.create_stock_location(actor=ps, code="UC33-AD", name="ECE", department="ECE")
    stock.record_adjustment(actor=ps, item_id=item.pk, location_id=source.pk, quantity_delta=5,
        reason="Opening", entry_type="opening")
    transfer = transfers.request_transfer(actor=_actor(34612, "deptadmin_ece"), item_id=item.pk,
        source_location_id=source.pk, destination_location_id=destination.pk, quantity=2)
    stock.record_adjustment(actor=ps, item_id=item.pk, location_id=source.pk, quantity_delta=-5,
        reason="Verified inventory correction", entry_type="adjustment")
    before_ledger = StockLedgerEntry.objects.count()

    with pytest.raises(ConflictError) as refused:
        transfers.dispatch_transfer(actor=ps, transfer_id=transfer.pk)
    assert refused.value.status_code == 409

    transfer.refresh_from_db()
    assert transfer.status == "requested"
    assert StockLedgerEntry.objects.count() == before_ledger


def test_tc_034_main_psm_uc_034_main_success_scenario():
    """TC-034-MAIN; source_id: PSM-UC-034 Main Success Scenario."""
    policy.seed_default_policy()
    from modules.psm.services import stock

    ps = _actor(34701, "deptadmin_cse")
    item = stock.create_stock_item(actor=ps, sku="UC34", name="Sensor")
    source = stock.create_stock_location(actor=ps, code="UC34-S", name="CSE", department="CSE")
    destination = stock.create_stock_location(actor=ps, code="UC34-D", name="ECE", department="ECE")
    stock.record_adjustment(actor=ps, item_id=item.pk, location_id=source.pk, quantity_delta=5,
        reason="Opening", entry_type="opening")
    transfer = transfers.request_transfer(actor=_actor(34702, "deptadmin_ece"), item_id=item.pk,
        source_location_id=source.pk, destination_location_id=destination.pk, quantity=2)
    transfers.dispatch_transfer(actor=_actor(34701, "deptadmin_cse"), transfer_id=transfer.pk)

    completed = transfers.confirm_transfer(actor=_actor(34703, "deptadmin_ece"), transfer_id=transfer.pk)
    assert completed.status == "completed"
    assert StockLedgerEntry.objects.filter(source_ref_type="stock_transfer", source_ref_id=transfer.pk).count() == 2
    assert PsmAuditLog.objects.filter(action="transfer.completed", target_id=transfer.pk).exists()


def test_tc_034_a1_psm_uc_034_alternative_a1():
    """TC-034-A1; source_id: PSM-UC-034 Alternative A1."""
    policy.seed_default_policy()
    from modules.psm.services import stock

    ps = _actor(34711, "deptadmin_cse")
    item = stock.create_stock_item(actor=ps, sku="UC34-A1", name="Sensor")
    source = stock.create_stock_location(actor=ps, code="UC34-AS", name="CSE", department="CSE")
    destination = stock.create_stock_location(actor=ps, code="UC34-AD", name="ECE", department="ECE")
    stock.record_adjustment(actor=ps, item_id=item.pk, location_id=source.pk, quantity_delta=5,
        reason="Opening", entry_type="opening")
    transfer = transfers.request_transfer(actor=_actor(34712, "deptadmin_ece"), item_id=item.pk,
        source_location_id=source.pk, destination_location_id=destination.pk, quantity=2)
    transfers.dispatch_transfer(actor=_actor(34711, "deptadmin_cse"), transfer_id=transfer.pk)
    before = StockLedgerEntry.objects.count()

    transfer.refresh_from_db()
    assert transfer.status == "dispatched"
    assert StockLedgerEntry.objects.count() == before
