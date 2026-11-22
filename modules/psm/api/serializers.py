from rest_framework import serializers

from modules.psm.models.discrepancy import DiscrepancyReport
from modules.psm.models.goods_receipt import GoodsReceiptNote, GRNItem
from modules.psm.models.indent import Indent, IndentItem
from modules.psm.models.inventory import StockItem
from modules.psm.models.item import ItemMaster
from modules.psm.models.purchase_order import POLineItem, PurchaseOrder
from modules.psm.models.vendor import Vendor


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            "id",
            "vendor_code",
            "name",
            "gstin",
            "email",
            "phone",
            "address",
            "bank_account_number",
            "bank_ifsc",
            "status",
            "verified_by_user_id",
            "verified_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "vendor_code",
            "status",
            "verified_by_user_id",
            "verified_at",
            "created_at",
        ]


class ItemMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemMaster
        fields = [
            "id",
            "item_code",
            "name",
            "description",
            "category",
            "unit_of_measure",
            "minimum_stock_level",
        ]


class IndentItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item_master.name", read_only=True)
    item_code = serializers.CharField(source="item_master.item_code", read_only=True)
    total_cost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = IndentItem
        fields = [
            "id",
            "item_master",
            "item_code",
            "item_name",
            "quantity_requested",
            "estimated_unit_cost",
            "specifications",
            "total_cost",
        ]


class IndentSerializer(serializers.ModelSerializer):
    items = IndentItemSerializer(many=True, read_only=True)

    class Meta:
        model = Indent
        fields = [
            "id",
            "indent_number",
            "user_id",
            "department_code",
            "title",
            "purpose",
            "priority",
            "estimated_total",
            "status",
            "current_approver_role",
            "rejection_reason",
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = [
            "id",
            "indent_number",
            "user_id",
            "estimated_total",
            "status",
            "current_approver_role",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]


class IndentItemInputSerializer(serializers.Serializer):
    item_master_id = serializers.IntegerField()
    quantity_requested = serializers.IntegerField(min_value=1)
    estimated_unit_cost = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    specifications = serializers.CharField(required=False, allow_blank=True)


class IndentCreateSerializer(serializers.Serializer):
    department_code = serializers.CharField(max_length=64)
    title = serializers.CharField(max_length=255)
    purpose = serializers.CharField()
    priority = serializers.CharField(default="NORMAL")
    items = IndentItemInputSerializer(many=True)


class IndentActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    remarks = serializers.CharField(required=False, allow_blank=True)


class POLineItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item_master.name", read_only=True)
    item_code = serializers.CharField(source="item_master.item_code", read_only=True)
    total_cost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = POLineItem
        fields = [
            "id",
            "item_master",
            "item_code",
            "item_name",
            "quantity_ordered",
            "unit_price",
            "total_cost",
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    lines = POLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "po_number",
            "indent",
            "vendor",
            "vendor_name",
            "procurement_method",
            "total_amount",
            "status",
            "delivery_due_date",
            "issued_by_user_id",
            "issued_at",
            "created_at",
            "lines",
        ]
        read_only_fields = [
            "id",
            "po_number",
            "total_amount",
            "procurement_method",
            "status",
            "issued_by_user_id",
            "issued_at",
            "created_at",
        ]


class POCreateSerializer(serializers.Serializer):
    indent_id = serializers.IntegerField()
    vendor_id = serializers.IntegerField()
    delivery_due_date = serializers.DateField(required=False, allow_null=True)


class GRNItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="po_line_item.item_master.name", read_only=True)

    class Meta:
        model = GRNItem
        fields = [
            "id",
            "po_line_item",
            "item_name",
            "quantity_received",
            "quantity_accepted",
            "quantity_rejected",
            "rejection_remarks",
        ]


class GoodsReceiptNoteSerializer(serializers.ModelSerializer):
    items = GRNItemSerializer(many=True, read_only=True)
    po_number = serializers.CharField(source="purchase_order.po_number", read_only=True)

    class Meta:
        model = GoodsReceiptNote
        fields = [
            "id",
            "grn_number",
            "purchase_order",
            "po_number",
            "store_keeper_user_id",
            "challan_number",
            "invoice_number",
            "receipt_date",
            "status",
            "indentor_acknowledged",
            "indentor_acknowledged_at",
            "notes",
            "created_at",
            "items",
        ]
        read_only_fields = [
            "id",
            "grn_number",
            "store_keeper_user_id",
            "status",
            "indentor_acknowledged",
            "indentor_acknowledged_at",
            "created_at",
        ]


class GRNItemInputSerializer(serializers.Serializer):
    po_line_item_id = serializers.IntegerField()
    quantity_received = serializers.IntegerField(min_value=1)
    quantity_accepted = serializers.IntegerField(min_value=0)
    quantity_rejected = serializers.IntegerField(min_value=0, default=0)
    rejection_remarks = serializers.CharField(required=False, allow_blank=True)


class GRNCreateSerializer(serializers.Serializer):
    po_id = serializers.IntegerField()
    receipt_date = serializers.DateField()
    challan_number = serializers.CharField(required=False, allow_blank=True)
    invoice_number = serializers.CharField(required=False, allow_blank=True)
    items = GRNItemInputSerializer(many=True)


class DiscrepancyReportSerializer(serializers.ModelSerializer):
    grn_number = serializers.CharField(source="grn.grn_number", read_only=True)

    class Meta:
        model = DiscrepancyReport
        fields = [
            "id",
            "discrepancy_code",
            "grn",
            "grn_number",
            "reported_by_user_id",
            "discrepancy_type",
            "details",
            "status",
            "resolution_summary",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "discrepancy_code",
            "reported_by_user_id",
            "status",
            "resolved_at",
            "created_at",
        ]


class StockItemSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(source="item_master.item_code", read_only=True)
    item_name = serializers.CharField(source="item_master.name", read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = StockItem
        fields = [
            "id",
            "item_master",
            "item_code",
            "item_name",
            "quantity_on_hand",
            "quantity_reserved",
            "available_quantity",
        ]


class StockIssueSerializer(serializers.Serializer):
    indent_id = serializers.IntegerField()


class DiscrepancyCreateSerializer(serializers.Serializer):
    grn_id = serializers.IntegerField()
    discrepancy_type = serializers.CharField(max_length=64)
    details = serializers.CharField()


class DiscrepancyResolveSerializer(serializers.Serializer):
    resolution_summary = serializers.CharField()


class InvoiceMatchSerializer(serializers.Serializer):
    invoice_number = serializers.CharField(required=False, default="")
    invoice_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
