"""Serializers for PSM module."""
from rest_framework import serializers
from modules.psm.models import (
    DeliveryDiscrepancy,
    GoodsReceiptNote,
    Indent,
    IndentApproval,
    IndentItem,
    Invoice,
    Payment,
    PSMAuditLog,
    PurchaseOrder,
    PurchaseOrderItem,
    StockItem,
    StockTransfer,
    Vendor,
)


class IndentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndentItem
        fields = ["id", "item_name", "description", "quantity", "estimated_unit_cost", "total_cost", "reserved_quantity"]


class IndentApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndentApproval
        fields = ["id", "approver_user_id", "role", "action", "remarks", "action_timestamp", "created_at"]


class IndentSerializer(serializers.ModelSerializer):
    items = IndentItemSerializer(many=True, read_only=True)
    approvals = IndentApprovalSerializer(many=True, read_only=True)

    class Meta:
        model = Indent
        fields = [
            "id", "indent_number", "user_id", "department_id",
            "title", "justification", "status", "criticality",
            "total_estimated_cost", "is_duplicate_flag", "duplicate_notes",
            "rejection_reason", "version", "submitted_at", "created_at",
            "items", "approvals",
        ]


class IndentCreateSerializer(serializers.Serializer):
    department_id = serializers.IntegerField()
    title = serializers.CharField(max_length=255)
    justification = serializers.CharField()
    criticality = serializers.ChoiceField(choices=["normal", "high", "urgent"], default="normal")
    items = serializers.ListField(child=serializers.DictField())


class StockItemSerializer(serializers.ModelSerializer):
    available_quantity = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = StockItem
        fields = ["id", "item_code", "name", "description", "unit_of_measure", "department_id", "is_central", "current_quantity", "reserved_quantity", "available_quantity"]


class StockTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransfer
        fields = "__all__"


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = "__all__"


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = "__all__"


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = "__all__"


class GoodsReceiptNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceiptNote
        fields = "__all__"


class DeliveryDiscrepancySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryDiscrepancy
        fields = "__all__"


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class PSMAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PSMAuditLog
        fields = "__all__"
