from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from fusion_auth.principal import Principal
from modules.psm import models as m
from modules.psm import services as s
from modules.psm.domain.rules import ROLES
from modules.psm.registry import PERMISSIONS

DEMO_POLICY = {
    "demo_only": True,
    "minimum_quantity": "0.001",
    "minimum_estimated_cost": "0",
    "resolution_adjustments": True,
    "approval_bands": [
        {"up_to": "100000", "roles": ["department_admin", "department_head", "ps_admin"]},
        {
            "up_to": None,
            "roles": ["department_admin", "department_head", "ps_admin", "final_authority"],
        },
    ],
    "tender_threshold": "100000",
    "modify_states": [
        "submitted",
        "modified",
        "changes_requested",
        "external_required",
        "stock_reserved",
        "awaiting_approval",
    ],
    "withdraw_states": [
        "submitted",
        "modified",
        "external_required",
        "stock_reserved",
        "awaiting_approval",
    ],
    "cancel_states": ["submitted", "modified", "external_required", "stock_reserved"],
    "duplicate_fields": ["requestor_id", "item", "quantity"],
    "sla_reminder_hours": 24,
    "sla_escalation_hours": 48,
    "partial_payments": True,
    "manual_adjustments": True,
}


def actor(role):
    row = m.Membership.objects.filter(role=role).order_by("user_id").first()
    return Principal(
        user_id=row.user_id,
        username=role,
        display_name=role.replace("_", " ").title(),
        kind="staff",
        active_role="psm_" + role,
        roles=("psm_" + role,),
        permissions=frozenset(c for c, _ in PERMISSIONS),
        modules=("psm",),
    )


class Command(BaseCommand):
    help = "Seed synthetic PSM preview data; never operates in production settings."

    @transaction.atomic
    def handle(self, *args, **options):
        if not getattr(settings, "PSM_PREVIEW", False):
            raise CommandError("Use config.settings.psm_preview with its isolated database.")
        if m.Membership.objects.exists():
            self.stdout.write("PSM demo already exists; no changes made.")
            return
        for i, role in enumerate(ROLES, 1):
            m.Membership.objects.create(user_id=9000 + i, role=role, department="CSE")
        m.Membership.objects.create(user_id=9100, role="department_admin", department="ECE")
        admin = actor("ps_admin")
        s.configure_policy(
            admin,
            {
                "name": "Illustrative demo policy — not institute policy",
                "configuration": DEMO_POLICY,
            },
        )
        vendor = s.create_vendor(
            admin,
            {
                "name": "Demo Campus Supplies",
                "gst": "DEMO-GST-ONLY",
                "bank_details": "Synthetic bank account — no financial connection",
                "compliance": ["demo-compliance.pdf"],
            },
        )
        s.vendor_action(admin, vendor.pk, "verify", {})
        m.Membership.objects.filter(role="vendor").update(vendor_id=vendor.pk)
        for item, qty, location in [
            ("Lab chairs", "80", "CENTRAL"),
            ("HDMI adapters", "15", "CSE"),
            ("Printer paper", "240", "CENTRAL"),
            ("Network switches", "8", "ECE"),
        ]:
            s.adjust_stock(
                admin,
                {
                    "item": item,
                    "location": location,
                    "delta": qty,
                    "reason": "Synthetic opening stock",
                    "source": "DEMO-OPENING",
                },
            )
        employee, dept, head = (
            actor("employee"),
            actor("department_admin"),
            actor("department_head"),
        )
        for item, qty, cost, state in [
            ("Lab chairs", "6", "18000", "reserved"),
            ("HDMI adapters", "4", "2400", "dispatched"),
            ("Oscilloscope", "2", "80000", "approval"),
            ("GPU workstation", "1", "180000", "final"),
            ("Library scanners", "2", "60000", "delivered"),
            ("Printer paper", "20", "1800", "draft"),
            ("Laser printers", "3", "45000", "submitted"),
            ("Seminar microphones", "4", "32000", "case"),
        ]:
            obj = s.create_indent(
                employee,
                {
                    "item": item,
                    "quantity": qty,
                    "estimated_cost": cost,
                    "justification": "Synthetic teaching and laboratory equipment request.",
                },
            )
            if state == "draft":
                continue
            s.indent_action(employee, obj.pk, "submit", {})
            if state == "submitted":
                continue
            s.indent_action(dept, obj.pk, "reserve", {})
            if state == "reserved":
                continue
            s.indent_action(dept, obj.pk, "review", {"decision": "approve", "priority": 1})
            if state == "dispatched":
                s.indent_action(
                    dept,
                    obj.pk,
                    "dispatch",
                    {
                        "pick_at": timezone.now().isoformat(),
                        "dispatch_at": timezone.now().isoformat(),
                    },
                )
                continue
            if state == "approval":
                continue
            s.indent_action(
                head, obj.pk, "review", {"decision": "approve", "reason": "Demo budget review."}
            )
            s.indent_action(
                admin,
                obj.pk,
                "review",
                {"decision": "approve", "reason": "Demo procurement review."},
            )
            if state == "final":
                continue
            order = s.create_order(
                admin,
                {
                    "indent": str(obj.pk),
                    "vendor": str(vendor.pk),
                    "amount": cost,
                    "planned_delivery": (timezone.now() + timedelta(days=5)).isoformat(),
                },
            )
            s.order_action(
                admin, order.pk, "deliver", {"actual_delivery": timezone.now().isoformat()}
            )
            receipt = s.create_receipt(
                employee,
                {
                    "indent": str(obj.pk),
                    "accepted": qty,
                    "rejected": "0",
                    "inspection": "Demo inspection accepted.",
                },
            )
            if state == "case":
                s.create_case(
                    employee,
                    {
                        "indent": str(obj.pk),
                        "kind": "warranty",
                        "description": "Demo microphone has intermittent output",
                        "evidence": ["demo-inspection.txt"],
                    },
                )
            else:
                s.indent_action(
                    employee, obj.pk, "confirm_receipt", {"receipt_id": str(receipt.pk)}
                )
                invoice = s.create_invoice(
                    actor("accounts"),
                    {
                        "po": str(order.pk),
                        "number": "DEMO-INV-001",
                        "quantity": qty,
                        "amount": cost,
                    },
                )
                s.invoice_action(actor("accounts"), invoice.pk, "verify", {})
        self.stdout.write("Created synthetic PSM preview, roles and lifecycle examples.")
