from django.db.models import Q

from core.api.exceptions import NotFoundError
from modules.psm import models as m
from modules.psm.access import member

GLOBAL = ("ps_admin", "accounts", "final_authority", "committee", "auditor")


def indents(principal):
    scope = member(principal)
    qs = m.Indent.objects.all()
    if scope.role in GLOBAL:
        return qs
    if scope.role in ("department_admin", "department_head"):
        return qs.filter(department=scope.department)
    if scope.role == "vendor":
        return qs.filter(po__vendor_id=scope.vendor_id) if scope.vendor_id else qs.none()
    return qs.filter(requestor_id=principal.user_id)


def indent(principal, pk, lock=False):
    qs = indents(principal)
    if lock:
        qs = qs.select_for_update()
    obj = qs.filter(pk=pk).first()
    if obj is None:
        raise NotFoundError()
    return obj


def collection(principal, name):
    scope = member(principal)
    ids = indents(principal).values("id")
    if name == "attachments":
        cases = m.Discrepancy.objects.filter(indent_id__in=ids).values("id")
        vendors = collection(principal, "vendors").values("id")
        return m.Attachment.objects.filter(
            Q(entity="indent", object_id__in=ids)
            | Q(entity="case", object_id__in=cases)
            | Q(entity="vendor", object_id__in=vendors)
        )
    if name == "indents":
        return indents(principal)
    if name == "notifications":
        return m.Notification.objects.filter(user_id=principal.user_id)
    if name == "stock":
        if scope.role in GLOBAL:
            return m.Stock.objects.all()
        if scope.role in ("department_admin", "department_head"):
            return m.Stock.objects.filter(location__in=[scope.department, "CENTRAL"])
        return m.Stock.objects.none()
    if name == "vendors":
        if scope.role in ("ps_admin", "accounts", "auditor"):
            return m.Vendor.objects.all()
        return (
            m.Vendor.objects.filter(pk=scope.vendor_id)
            if scope.role == "vendor"
            else m.Vendor.objects.none()
        )
    if name == "vendor_history":
        return (
            m.VendorVersion.objects.all()
            if scope.role in ("ps_admin", "accounts", "auditor")
            else m.VendorVersion.objects.none()
        )
    if name == "tenders":
        return (
            m.Tender.objects.all() if scope.role in ("vendor", *GLOBAL) else m.Tender.objects.none()
        )
    if name == "bids":
        qs = m.Bid.objects.all()
        if scope.role in ("ps_admin", "committee", "auditor"):
            return qs
        return qs.filter(vendor_id=scope.vendor_id) if scope.role == "vendor" else qs.none()
    if name in ("orders", "invoices", "payments"):
        if scope.role not in (*GLOBAL, "vendor"):
            return {"orders": m.PurchaseOrder, "invoices": m.Invoice, "payments": m.Payment}[
                name
            ].objects.none()
        if name == "orders":
            return m.PurchaseOrder.objects.filter(indent_id__in=ids)
        if name == "invoices":
            return m.Invoice.objects.filter(po__indent_id__in=ids)
        return m.Payment.objects.filter(invoice__po__indent_id__in=ids)
    if name == "receipts":
        return m.Receipt.objects.filter(indent_id__in=ids)
    if name == "cases":
        return m.Discrepancy.objects.filter(indent_id__in=ids)
    if name == "communications":
        return m.Communication.objects.filter(case__indent_id__in=ids)
    if name == "transfers":
        qs = m.Transfer.objects.all()
        return (
            qs
            if scope.role in GLOBAL
            else qs.filter(Q(source__location=scope.department) | Q(destination=scope.department))
            if scope.role == "department_admin"
            else qs.none()
        )
    if name == "ledger":
        qs = m.LedgerEntry.objects.all()
        return (
            qs
            if scope.role in GLOBAL
            else qs.filter(stock__location=scope.department)
            if scope.role == "department_admin"
            else qs.none()
        )
    if name == "audit":
        qs = m.Audit.objects.all()
        if scope.role in GLOBAL:
            return qs
        if scope.role in ("department_admin", "department_head"):
            return qs.filter(department=scope.department).exclude(entity="vendor")
        return qs.filter(entity="indent", object_id__in=ids)
    if name == "schedules":
        return m.ReportSchedule.objects.filter(user_id=principal.user_id)
    if name == "reports":
        return m.ReportRun.objects.filter(user_id=principal.user_id)
    if name == "policies":
        return m.Policy.objects.all() if scope.role == "ps_admin" else m.Policy.objects.none()
    raise NotFoundError()
