from rest_framework import serializers

from modules.psm import models as m

MODELS = {
    "attachments": m.Attachment,
    "vendor_history": m.VendorVersion,
    "indents": m.Indent,
    "stock": m.Stock,
    "vendors": m.Vendor,
    "tenders": m.Tender,
    "bids": m.Bid,
    "orders": m.PurchaseOrder,
    "receipts": m.Receipt,
    "cases": m.Discrepancy,
    "invoices": m.Invoice,
    "payments": m.Payment,
    "transfers": m.Transfer,
    "ledger": m.LedgerEntry,
    "audit": m.Audit,
    "notifications": m.Notification,
    "communications": m.Communication,
    "schedules": m.ReportSchedule,
    "reports": m.ReportRun,
    "policies": m.Policy,
}


def serializer_for(name):
    model = MODELS[name]
    fields = [f.name for f in model._meta.fields if f.name not in ("credential", "file")]
    meta = type("Meta", (), {"model": model, "fields": fields, "read_only_fields": fields})
    return type(model.__name__ + "Serializer", (serializers.ModelSerializer,), {"Meta": meta})


SERIALIZERS = {name: serializer_for(name) for name in MODELS}


def representation(obj):
    name = next(name for name, model in MODELS.items() if isinstance(obj, model))
    return SERIALIZERS[name](obj).data


class CommandSerializer(serializers.Serializer):
    action = serializers.CharField(max_length=60)
    data = serializers.DictField(default=dict)


class JsonCommandSerializer(serializers.Serializer):
    data = serializers.DictField()
