"""
DRF Serializers for the PSM Module.
Enforces explicit field allow-lists (NEVER fields = "__all__").
"""

from rest_framework import serializers
from modules.psm.models import (
    Indent,
    IndentVersion,
    Vendor,
    PurchaseOrder,
    GoodsReceiptNote,
    StockItem,
    StockTransfer,
)


class IndentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndentVersion
        fields = [
            "id",
            "version_number",
            "item_details",
            "quantity",
            "estimated_cost",
            "justification",
            "created_at",
        ]
        read_only_fields = fields


class IndentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indent
        fields = [
            "id",
            "indent_id",
            "requestor_id",
            "item_details",
            "quantity",
            "estimated_cost",
            "justification",
            "status",
            "priority",
            "is_duplicate",
            "rejection_justification",
            "current_version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "indent_id",
            "requestor_id",
            "is_duplicate",
            "current_version",
            "created_at",
            "updated_at",
        ]


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            "id",
            "name",
            "gst_number",
            "bank_account_number",
            "bank_ifsc",
            "compliance_docs_url",
            "is_verified",
            "version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_verified", "version", "created_at", "updated_at"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    indent_business_id = serializers.CharField(source="indent.indent_id", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "po_number",
            "indent",
            "indent_business_id",
            "vendor",
            "vendor_name",
            "procurement_method",
            "status",
            "total_cost",
            "delivery_schedule",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "po_number", "created_at", "updated_at"]


class GoodsReceiptNoteSerializer(serializers.ModelSerializer):
    po_number = serializers.CharField(source="purchase_order.po_number", read_only=True)

    class Meta:
        model = GoodsReceiptNote
        fields = [
            "id",
            "grn_number",
            "purchase_order",
            "po_number",
            "accepted_quantity",
            "rejected_quantity",
            "inspection_remarks",
            "is_confirmed",
            "has_discrepancy",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "grn_number", "created_at", "updated_at"]


class StockItemSerializer(serializers.ModelSerializer):
    allocable_stock = serializers.SerializerMethodField()

    class Meta:
        model = StockItem
        fields = [
            "id",
            "item_code",
            "name",
            "description",
            "department",
            "central_stock",
            "department_stock",
            "reserved_stock",
            "allocable_stock",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "allocable_stock", "created_at", "updated_at"]

    def get_allocable_stock(self, obj: StockItem) -> int:
        return max(0, (obj.central_stock + obj.department_stock) - obj.reserved_stock)


class StockTransferSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(source="stock_item.item_code", read_only=True)
    item_name = serializers.CharField(source="stock_item.name", read_only=True)

    class Meta:
        model = StockTransfer
        fields = [
            "id",
            "transfer_id",
            "source_department",
            "destination_department",
            "stock_item",
            "item_code",
            "item_name",
            "quantity",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "transfer_id", "created_at", "updated_at"]
