from dataclasses import replace
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.api.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from devtools.management.commands.seed_psm_demo import DEMO_POLICY
from fusion_auth.principal import Principal
from modules.psm import models as m
from modules.psm import selectors
from modules.psm import services as s
from modules.psm.registry import PERMISSIONS
from modules.psm.reporting import generate_report, run_due_reports, schedule_report
from modules.psm.tasks import monitor_sla

pytestmark = pytest.mark.django_db


@pytest.fixture
def actors():
    people = {}
    for i, role in enumerate(
        (
            "employee",
            "department_admin",
            "department_head",
            "ps_admin",
            "accounts",
            "final_authority",
            "committee",
            "vendor",
            "auditor",
        ),
        1,
    ):
        m.Membership.objects.create(user_id=i, role=role, department="CSE")
        people[role] = Principal(
            user_id=i,
            username=role,
            display_name=role,
            kind="staff",
            active_role="psm_" + role,
            roles=("psm_" + role,),
            modules=("psm",),
            permissions=frozenset(c for c, _ in PERMISSIONS),
        )
    m.Policy.objects.create(name="Explicit test policy", active=True, configuration=DEMO_POLICY)
    return people


def draft(actors, **changes):
    return s.create_indent(
        actors["employee"],
        {
            "item": "Microscope",
            "quantity": "4",
            "estimated_cost": "4000",
            "justification": "Teaching laboratory",
            **changes,
        },
    )


def submitted(actors, **changes):
    obj = draft(actors, **changes)
    return s.indent_action(actors["employee"], obj.pk, "submit", {})


def approved(actors, **changes):
    obj = submitted(actors, **changes)
    s.indent_action(actors["department_admin"], obj.pk, "reserve", {})
    for role in ("department_admin", "department_head", "ps_admin"):
        s.indent_action(actors[role], obj.pk, "review", {"decision": "approve"})
    obj.refresh_from_db()
    if obj.status == "awaiting_approval":
        s.indent_action(actors["final_authority"], obj.pk, "review", {"decision": "approve"})
    obj.refresh_from_db()
    return obj


def vendor(actors):
    obj = s.create_vendor(
        actors["ps_admin"],
        {
            "name": "Test vendor",
            "gst": "GST-TEST",
            "bank_details": "Bank reference",
            "compliance": ["compliance-reference"],
        },
    )
    return s.vendor_action(actors["ps_admin"], obj.pk, "verify", {})


def ordered(actors):
    obj = approved(actors)
    v = vendor(actors)
    order = s.create_order(
        actors["ps_admin"],
        {
            "indent": str(obj.pk),
            "vendor": str(v.pk),
            "amount": "4000",
            "planned_delivery": (timezone.now() + timedelta(days=2)).isoformat(),
        },
    )
    s.order_action(
        actors["ps_admin"], order.pk, "deliver", {"actual_delivery": timezone.now().isoformat()}
    )
    return obj, order


def received(actors, qty="4"):
    obj, order = ordered(actors)
    receipt = s.create_receipt(
        actors["employee"],
        {"indent": str(obj.pk), "accepted": qty, "rejected": "0", "inspection": "Accepted"},
    )
    return obj, order, receipt


def confirm(actors, obj, receipt):
    return s.indent_action(
        actors["employee"], obj.pk, "confirm_receipt", {"receipt_id": str(receipt.pk)}
    )


def invoice(actors, order, quantity="4", amount="4000", number="INV-1"):
    return s.create_invoice(
        actors["accounts"],
        {"po": str(order.pk), "number": number, "quantity": quantity, "amount": amount},
    )


def test_internal_fulfilment_posts_only_once_after_confirmation(actors):
    stock = m.Stock.objects.create(item="Microscope", location="CENTRAL", quantity=10)
    obj = submitted(actors)
    s.indent_action(actors["department_admin"], obj.pk, "reserve", {})
    stock.refresh_from_db()
    assert stock.quantity == 10 and stock.reserved == 4
    s.indent_action(actors["department_admin"], obj.pk, "review", {"decision": "approve"})
    now = timezone.now().isoformat()
    s.indent_action(
        actors["department_admin"], obj.pk, "dispatch", {"pick_at": now, "dispatch_at": now}
    )
    receipt = s.create_receipt(
        actors["employee"],
        {"indent": str(obj.pk), "accepted": "4", "rejected": "0", "inspection": "All accepted"},
    )
    stock.refresh_from_db()
    assert stock.quantity == 10
    confirm(actors, obj, receipt)
    stock.refresh_from_db()
    assert stock.quantity == 6 and stock.reserved == 0
    with pytest.raises(ConflictError):
        confirm(actors, obj, receipt)
    assert m.LedgerEntry.objects.filter(source=str(receipt.pk)).count() == 1


def test_reservation_prevents_second_request_overcommitment(actors):
    stock = m.Stock.objects.create(item="Microscope", location="CSE", quantity=5)
    first, second = submitted(actors), submitted(actors)
    s.indent_action(actors["department_admin"], first.pk, "reserve", {})
    second = s.indent_action(actors["department_admin"], second.pk, "reserve", {})
    stock.refresh_from_db()
    assert stock.reserved == 4 and second.status == "external_required"


def test_cancellation_releases_reservation(actors):
    stock = m.Stock.objects.create(item="Microscope", location="CSE", quantity=5)
    obj = submitted(actors)
    s.indent_action(actors["department_admin"], obj.pk, "reserve", {})
    s.indent_action(actors["employee"], obj.pk, "cancel", {})
    stock.refresh_from_db()
    assert stock.reserved == 0


def test_duplicate_is_flagged_and_requires_review(actors):
    submitted(actors)
    second = submitted(actors)
    assert second.duplicate_ids
    s.indent_action(actors["department_admin"], second.pk, "reserve", {})
    with pytest.raises(ConflictError):
        s.indent_action(actors["department_admin"], second.pk, "review", {"decision": "approve"})
    result = s.indent_action(
        actors["department_admin"],
        second.pk,
        "review",
        {"decision": "approve", "duplicate_review": "Distinct lab requirement"},
    )
    assert result.approval_step == 1


def test_modify_versions_and_reruns_reviews(actors):
    obj = submitted(actors)
    modified = s.indent_action(
        actors["employee"],
        obj.pk,
        "modify",
        {
            "item": "Microscope",
            "quantity": "6",
            "estimated_cost": "6000",
            "justification": "Revised laboratory plan",
        },
    )
    assert modified.version == 2 and modified.status == "modified"
    assert set(
        m.Audit.objects.filter(object_id=obj.pk).values_list("snapshot__version", flat=True)
    ) == {1, 2}


def test_repeat_makes_separate_draft(actors):
    original = submitted(actors)
    new = s.indent_action(actors["employee"], original.pk, "repeat", {})
    assert new.pk != original.pk and new.status == "draft"
    original.refresh_from_db()
    assert original.status == "submitted"


def test_rejection_requires_reason_and_notifies(actors):
    obj = submitted(actors)
    s.indent_action(actors["department_admin"], obj.pk, "reserve", {})
    with pytest.raises(ConflictError):
        s.indent_action(actors["department_admin"], obj.pk, "review", {"decision": "reject"})
    s.indent_action(
        actors["department_admin"], obj.pk, "review", {"decision": "reject", "reason": "Not needed"}
    )
    assert m.Notification.objects.filter(
        indent=obj, event="reject", user_id=actors["employee"].user_id
    ).exists()


def test_approval_cannot_be_skipped(actors):
    obj = submitted(actors)
    with pytest.raises(ConflictError):
        s.create_order(actors["ps_admin"], {"indent": str(obj.pk)})
    s.indent_action(actors["department_admin"], obj.pk, "reserve", {})
    with pytest.raises(PermissionDeniedError):
        s.indent_action(actors["ps_admin"], obj.pk, "review", {"decision": "approve"})


def test_final_authority_path_is_required(actors):
    obj = approved(actors, estimated_cost="150000")
    assert obj.method == "tender" and obj.status == "authorized"
    assert m.Audit.objects.filter(object_id=obj.pk, snapshot__role="final_authority").exists()


def test_vendor_version_history_and_reverification(actors):
    obj = vendor(actors)
    s.vendor_action(
        actors["ps_admin"],
        obj.pk,
        "update",
        {
            "name": "Renamed vendor",
            "gst": "GST-TEST",
            "bank_details": "Updated bank",
            "compliance": ["updated-reference"],
        },
    )
    obj.refresh_from_db()
    assert not obj.verified and obj.version == 2
    assert m.VendorVersion.objects.filter(
        vendor=obj, version=1, snapshot__bank_details="Bank reference"
    ).exists()


def test_unverified_vendor_cannot_receive_po(actors):
    obj = approved(actors)
    v = vendor(actors)
    m.Vendor.objects.filter(pk=v.pk).update(verified=False)
    with pytest.raises(ConflictError):
        s.create_order(
            actors["ps_admin"],
            {
                "indent": str(obj.pk),
                "vendor": str(v.pk),
                "amount": "4000",
                "planned_delivery": timezone.now().isoformat(),
            },
        )


def test_external_invoice_and_payment_gates(actors):
    obj, order, receipt = received(actors)
    bill = invoice(actors, order)
    held = s.invoice_action(actors["accounts"], bill.pk, "verify", {})
    assert held.status == "held"
    assert not m.Stock.objects.filter(item=obj.item, location="CSE").exists()
    confirm(actors, obj, receipt)
    bill = s.invoice_action(actors["accounts"], bill.pk, "verify", {})
    assert bill.status == "verified"
    bill = s.invoice_action(
        actors["accounts"], bill.pk, "pay", {"amount": "4000", "reference": "PAY-1"}
    )
    assert bill.status == "paid"
    with pytest.raises(ConflictError):
        s.invoice_action(
            actors["accounts"], bill.pk, "pay", {"amount": "4000", "reference": "PAY-2"}
        )
    assert m.Payment.objects.count() == 1


def test_mismatched_invoice_stays_on_hold(actors):
    obj, order, receipt = received(actors)
    confirm(actors, obj, receipt)
    bill = invoice(actors, order, amount="5000")
    result = s.invoice_action(actors["accounts"], bill.pk, "verify", {})
    assert result.status == "held" and "match" in result.hold_reason


def test_partial_receipt_limits_cumulative_invoice_amount(actors):
    obj, order, receipt = received(actors, qty="2")
    confirm(actors, obj, receipt)
    first = invoice(actors, order, quantity="2", amount="2000")
    s.invoice_action(actors["accounts"], first.pk, "verify", {})
    duplicate = invoice(actors, order, quantity="2", amount="2000", number="INV-2")
    assert s.invoice_action(actors["accounts"], duplicate.pk, "verify", {}).status == "held"


def test_unresolved_case_blocks_posting_and_payment(actors):
    obj, order, receipt = received(actors)
    case = s.create_case(
        actors["employee"],
        {
            "indent": str(obj.pk),
            "kind": "damage",
            "description": "Inspection issue",
            "evidence": ["photo reference"],
        },
    )
    with pytest.raises(ConflictError):
        confirm(actors, obj, receipt)
    s.case_action(
        actors["ps_admin"],
        case.pk,
        "resolve",
        {"resolution": "Inspection cleared", "inventory_delta": "0", "accounting_delta": "0"},
    )
    confirm(actors, obj, receipt)
    assert (
        s.invoice_action(actors["accounts"], invoice(actors, order).pk, "verify", {}).status
        == "verified"
    )


def test_return_adjustments_need_posted_stock_and_cannot_create_stock(actors):
    obj, _, _ = received(actors)
    case = s.create_case(
        actors["employee"],
        {
            "indent": str(obj.pk),
            "kind": "return",
            "description": "Return",
            "evidence": ["return reference"],
        },
    )
    with pytest.raises(ConflictError):
        s.case_action(
            actors["ps_admin"],
            case.pk,
            "resolve",
            {"resolution": "Return", "inventory_delta": "-1", "accounting_delta": "-1000"},
        )
    with pytest.raises(ConflictError):
        s.case_action(
            actors["ps_admin"],
            case.pk,
            "resolve",
            {"resolution": "Return", "inventory_delta": "1", "accounting_delta": "0"},
        )


def test_tender_requires_committee_and_selected_vendor(actors):
    obj = approved(actors, estimated_cost="150000")
    v = vendor(actors)
    tender = s.create_tender(
        actors["ps_admin"],
        {
            "indent": str(obj.pk),
            "criteria": ["Suitability", "Price"],
            "closes_at": (timezone.now() + timedelta(days=1)).isoformat(),
        },
    )
    bid = s.create_bid(
        actors["ps_admin"],
        {"tender": str(tender.pk), "vendor": str(v.pk), "amount": "150000", "proposal": "Proposal"},
    )
    with pytest.raises(ConflictError):
        s.tender_action(actors["committee"], tender.pk, "evaluate", {"bid": str(bid.pk)})
    m.Tender.objects.filter(pk=tender.pk).update(closes_at=timezone.now() - timedelta(seconds=1))
    with pytest.raises(PermissionDeniedError):
        s.tender_action(
            actors["ps_admin"], tender.pk, "select", {"bid": str(bid.pk), "reason": "Selected"}
        )
    s.tender_action(
        actors["committee"],
        tender.pk,
        "evaluate",
        {"bid": str(bid.pk), "evaluation": {"Suitability": "Accepted", "Price": "Accepted"}},
    )
    s.tender_action(
        actors["committee"],
        tender.pk,
        "select",
        {"bid": str(bid.pk), "reason": "Meets published criteria"},
    )
    po = s.create_order(
        actors["ps_admin"],
        {
            "indent": str(obj.pk),
            "vendor": str(v.pk),
            "amount": "150000",
            "planned_delivery": timezone.now().isoformat(),
        },
    )
    assert po.vendor_id == v.pk


def test_transfer_posts_both_ledgers_once(actors):
    source = m.Stock.objects.create(item="Cable", location="CENTRAL", quantity=10)
    obj = s.create_transfer(
        actors["department_admin"],
        {"source": str(source.pk), "quantity": "3", "reason": "Lab transfer"},
    )
    s.transfer_action(actors["ps_admin"], obj.pk, "dispatch", {})
    source.refresh_from_db()
    assert source.quantity == 10 and source.reserved == 3
    s.transfer_action(actors["department_admin"], obj.pk, "confirm", {})
    source.refresh_from_db()
    assert source.quantity == 7 and source.reserved == 0
    assert m.Stock.objects.get(item="Cable", location="CSE").quantity == 3
    assert m.LedgerEntry.objects.filter(source=str(obj.pk)).count() == 2
    with pytest.raises(ConflictError):
        s.transfer_action(actors["department_admin"], obj.pk, "confirm", {})


def test_department_and_employee_scope_fail_closed(actors):
    obj = submitted(actors)
    outsider = replace(actors["employee"], user_id=100)
    m.Membership.objects.create(user_id=100, role="employee", department="ECE")
    with pytest.raises(NotFoundError):
        selectors.indent(outsider, obj.pk)
    bad_role = replace(actors["ps_admin"], permissions=frozenset(["psm.workspace.view"]))
    with pytest.raises(PermissionDeniedError):
        selectors.indents(bad_role)
    assert not selectors.collection(actors["employee"], "invoices").exists()
    assert not selectors.collection(actors["employee"], "vendors").exists()


def test_unauthenticated_api_denied_and_employee_data_is_scoped(actors):
    api = APIClient()
    assert api.get("/api/v1/psm/workspace").status_code == 401
    obj = submitted(actors)
    # Real authentication sets principal, so inject that through an authentication stub.
    from unittest.mock import patch

    def auth(self, request):
        request.principal = actors["employee"]
        return actors["employee"], "test-token"

    with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", auth):
        response = api.get("/api/v1/psm/workspace")
        assert response.status_code == 200
        assert response.data["indents"][0]["id"] == str(obj.pk)
        assert response.data["invoices"] == [] and response.data["vendors"] == []
        assert (
            api.post(
                "/api/v1/psm/vendors", {"data": {"name": "Forbidden"}}, format="json"
            ).status_code
            == 403
        )


def test_report_scope_and_generation_logging(actors):
    submitted(actors)
    result = generate_report(
        actors["department_admin"], {"report": "operational", "filters": {"department": "CSE"}}
    )
    assert len(result.rows) == 1
    assert m.Audit.objects.filter(object_id=result.pk, action="report_generated").exists()
    with pytest.raises(DomainError):
        generate_report(actors["department_admin"], {"report": "financial"})
    with pytest.raises(DomainError):
        generate_report(actors["accounts"], {"report": "operational", "filters": {"unknown": "x"}})


def test_scheduled_report_reauthorizes_and_runs_idempotently(actors, monkeypatch):
    from modules.psm import reporting

    schedule = schedule_report(
        actors["accounts"],
        {
            "report": "financial",
            "filters": {},
            "interval_hours": "1",
            "next_run": (timezone.now() - timedelta(seconds=2)).isoformat(),
            "_credential": "sensitive-session",
        },
    )
    assert "sensitive-session" not in schedule.credential
    monkeypatch.setattr(reporting, "resolve_schedule", lambda obj: actors["accounts"])
    assert run_due_reports() == 1
    assert run_due_reports() == 0
    assert m.ReportRun.objects.filter(schedule=schedule).count() == 1


def test_revoked_report_schedule_is_disabled_and_audited(actors, monkeypatch):
    from modules.psm import reporting

    schedule = schedule_report(
        actors["accounts"],
        {
            "report": "financial",
            "interval_hours": "1",
            "next_run": (timezone.now() - timedelta(seconds=2)).isoformat(),
            "_credential": "session",
        },
    )

    def denied(obj):
        raise DomainError("Revoked")

    monkeypatch.setattr(reporting, "resolve_schedule", denied)
    assert run_due_reports() == 0
    schedule.refresh_from_db()
    assert not schedule.enabled
    assert m.Audit.objects.filter(object_id=schedule.pk, action="schedule_blocked").exists()


def test_sla_reminders_and_escalations_are_not_duplicated(actors):
    obj = submitted(actors)
    m.Indent.objects.filter(pk=obj.pk).update(updated_at=timezone.now() - timedelta(hours=50))
    assert monitor_sla() == 2
    assert monitor_sla() == 0
    assert m.Notification.objects.filter(indent=obj, event="sla_escalation").exists()


def test_policy_not_configured_is_explicit(actors):
    m.Policy.objects.update(active=False)
    obj = draft(actors)
    with pytest.raises(ConflictError):
        s.indent_action(actors["employee"], obj.pk, "submit", {})


@pytest.mark.parametrize("value", ["NaN", "Infinity", "abc", None, "0.001"])
def test_money_validation_rejects_invalid_values(actors, value):
    with pytest.raises(DomainError):
        draft(actors, estimated_cost=value)


def test_replacement_is_inspected_then_confirmed_before_posting(actors):
    obj, order = ordered(actors)
    first = s.create_receipt(
        actors["employee"],
        {
            "indent": str(obj.pk),
            "accepted": "2",
            "rejected": "2",
            "inspection": "Two damaged units",
            "evidence": ["inspection reference"],
        },
    )
    case = obj.cases.get()
    s.case_action(
        actors["ps_admin"], case.pk, "replace", {"resolution": "Vendor will replace two units"}
    )
    replacement = s.create_receipt(
        actors["employee"],
        {
            "indent": str(obj.pk),
            "accepted": "2",
            "rejected": "0",
            "inspection": "Replacement accepted",
            "replacement_case_id": str(case.pk),
        },
    )
    assert not m.Stock.objects.filter(item=obj.item, location="CSE").exists()
    confirm(actors, obj, first)
    confirm(actors, obj, replacement)
    assert m.Stock.objects.get(item=obj.item, location="CSE").quantity == 4
    assert (
        s.invoice_action(actors["accounts"], invoice(actors, order).pk, "verify", {}).status
        == "verified"
    )


def test_partial_payment_cannot_exceed_remaining_balance(actors):
    obj, order, receipt = received(actors)
    confirm(actors, obj, receipt)
    bill = invoice(actors, order)
    s.invoice_action(actors["accounts"], bill.pk, "verify", {})
    result = s.invoice_action(
        actors["accounts"], bill.pk, "pay", {"amount": "2000", "reference": "PART-1"}
    )
    assert result.status == "partially_paid"
    with pytest.raises(ConflictError):
        s.invoice_action(
            actors["accounts"], bill.pk, "pay", {"amount": "2500", "reference": "PART-2"}
        )
    from django.db.models import Sum

    assert m.Payment.objects.filter(invoice=bill).aggregate(n=Sum("amount"))["n"] == 2000


def test_revoked_vendor_verification_blocks_previously_verified_invoice(actors):
    obj, order, receipt = received(actors)
    confirm(actors, obj, receipt)
    bill = invoice(actors, order)
    s.invoice_action(actors["accounts"], bill.pk, "verify", {})
    m.Vendor.objects.filter(pk=order.vendor_id).update(verified=False)
    with pytest.raises(ConflictError):
        s.invoice_action(
            actors["accounts"], bill.pk, "pay", {"amount": "4000", "reference": "PAY-1"}
        )
    assert not m.Payment.objects.exists()


def test_attachments_are_retained_and_scoped(actors, tmp_path, settings):
    from unittest.mock import patch

    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.PSM_UPLOAD_ROOT = tmp_path
    obj = submitted(actors)
    api = APIClient()

    def auth(self, request):
        request.principal = actors["employee"]
        return actors["employee"], "session"

    with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", auth):
        response = api.post(
            "/api/v1/psm/attachments/upload",
            {
                "entity": "indent",
                "object_id": str(obj.pk),
                "file": SimpleUploadedFile("inspection.txt", b"inspection evidence"),
            },
            format="multipart",
        )
        assert response.status_code == 201
        attachment_id = response.data["id"]
        download = api.get(f"/api/v1/psm/attachments/{attachment_id}/download")
        assert b"".join(download.streaming_content) == b"inspection evidence"
    outsider = replace(actors["employee"], user_id=100)
    m.Membership.objects.create(user_id=100, role="employee", department="ECE")
    assert not selectors.collection(outsider, "attachments").exists()
    assert m.Audit.objects.filter(object_id=obj.pk, action="document_retained").exists()


def test_configuration_rejects_incomplete_or_invalid_routes(actors):
    with pytest.raises(DomainError):
        s.configure_policy(actors["ps_admin"], {"name": "Incomplete", "configuration": {}})
    invalid = {**DEMO_POLICY, "priority_routes": {"1": ["department_admin", "vendor", "ps_admin"]}}
    with pytest.raises(DomainError):
        s.configure_policy(
            actors["ps_admin"], {"name": "Invalid priority", "configuration": invalid}
        )


def test_failed_modification_keeps_reserved_stock(actors):
    stock = m.Stock.objects.create(item="Microscope", location="CSE", quantity=10)
    obj = submitted(actors)
    s.indent_action(actors["department_admin"], obj.pk, "reserve", {})
    with pytest.raises(DomainError):
        s.indent_action(
            actors["employee"],
            obj.pk,
            "modify",
            {"item": "", "quantity": "6", "estimated_cost": "6000", "justification": "Edited"},
        )
    stock.refresh_from_db()
    obj.refresh_from_db()
    assert stock.reserved == 4 and obj.status == "stock_reserved" and obj.version == 1
