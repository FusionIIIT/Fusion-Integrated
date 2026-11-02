from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from modules.purchase_stores.models import (
    GoodsReceipt,
    Indent,
    IndentLine,
    PurchaseOrder,
    StockBalance,
    StockTransfer,
    Vendor,
    VendorInvoice,
    WorkflowAction,
)


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {"non_field_errors": [f"Unsupported field(s): {', '.join(sorted(unknown))}."]}
            )
        return super().to_internal_value(data)


class IndentLineInputSerializer(StrictSerializer):
    item_name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    unit = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    estimated_unit_cost = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0")
    )
    sku = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")


class IndentCreateSerializer(StrictSerializer):
    department_id = serializers.IntegerField(min_value=1)
    justification = serializers.CharField(trim_whitespace=True)
    priority = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    lines = IndentLineInputSerializer(many=True, allow_empty=False)
    draft = serializers.BooleanField(required=False, default=False)

    def validate_justification(self, value):
        if not value:
            raise serializers.ValidationError("A purchase justification is required.")
        return value


class IndentLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndentLine
        fields = (
            "id",
            "item_name",
            "description",
            "quantity",
            "unit",
            "estimated_unit_cost",
            "sku",
        )
        read_only_fields = fields


class WorkflowActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowAction
        fields = ("action", "from_status", "to_status", "reason", "details", "at")
        read_only_fields = fields


class IndentSerializer(serializers.ModelSerializer):
    lines = IndentLineSerializer(many=True, read_only=True)
    actions = WorkflowActionSerializer(many=True, read_only=True)

    class Meta:
        model = Indent
        fields = (
            "id",
            "reference",
            "requestor_user_id",
            "department_id",
            "status",
            "justification",
            "priority",
            "duplicate_review_required",
            "duplicate_of_id",
            "current_version",
            "submitted_at",
            "created_at",
            "updated_at",
            "lines",
            "actions",
        )
        read_only_fields = fields


class IndentTransitionSerializer(StrictSerializer):
    to_status = serializers.ChoiceField(choices=Indent.Status.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    priority = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")


class IndentModifySerializer(StrictSerializer):
    justification = serializers.CharField(trim_whitespace=True)
    lines = IndentLineInputSerializer(many=True, allow_empty=False)


class VendorInputSerializer(StrictSerializer):
    legal_name = serializers.CharField(max_length=200)
    gst_number = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    bank_details = serializers.DictField(required=False, default=dict)
    compliance_documents = serializers.ListField(
        child=serializers.JSONField(), required=False, default=list
    )
    contact_email = serializers.EmailField(required=False, allow_blank=True, default="")
    contact_phone = serializers.CharField(
        max_length=32, required=False, allow_blank=True, default=""
    )


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = (
            "id",
            "legal_name",
            "gst_number",
            "bank_details",
            "compliance_documents",
            "status",
            "version",
            "contact_email",
            "contact_phone",
        )
        read_only_fields = fields


class PurchaseOrderCreateSerializer(StrictSerializer):
    indent_id = serializers.IntegerField(min_value=1)
    vendor_id = serializers.IntegerField(min_value=1)
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0"))
    planned_delivery_at = serializers.DateTimeField(required=False, allow_null=True)


class PurchaseOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = (
            "id",
            "reference",
            "indent_id",
            "vendor_id",
            "status",
            "total_amount",
            "line_items",
            "planned_delivery_at",
            "actual_delivery_at",
            "created_at",
        )
        read_only_fields = fields


class ReceiptLineInputSerializer(StrictSerializer):
    sku = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    item_name = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))

    def validate(self, attrs):
        if not attrs.get("sku") and not attrs.get("item_name"):
            raise serializers.ValidationError("Provide a SKU or item name for each receipt line.")
        return attrs


class ReceiptInputSerializer(StrictSerializer):
    accepted_lines = ReceiptLineInputSerializer(many=True, required=False, default=list)
    rejected_lines = ReceiptLineInputSerializer(many=True, required=False, default=list)
    discrepancy_note = serializers.CharField(required=False, allow_blank=True, default="")


class GoodsReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceipt
        fields = (
            "id",
            "purchase_order_id",
            "receipt_reference",
            "inspected_by_user_id",
            "accepted_lines",
            "rejected_lines",
            "discrepancy_note",
            "receipt_confirmed_by_user_id",
            "confirmed_at",
            "created_at",
        )
        read_only_fields = fields


class VendorInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorInvoice
        fields = (
            "id",
            "purchase_order_id",
            "goods_receipt_id",
            "vendor_id",
            "invoice_number",
            "invoice_amount",
            "status",
            "match_details",
            "hold_reason",
            "verified_at",
            "created_at",
        )
        read_only_fields = fields


class InvoiceVerificationSerializer(StrictSerializer):
    purchase_order_id = serializers.IntegerField(min_value=1)
    invoice_number = serializers.CharField(max_length=80)
    invoice_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0")
    )
    goods_receipt_id = serializers.IntegerField(min_value=1)
    match_details = serializers.DictField(required=False, default=dict)


class PaymentSerializer(StrictSerializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    reference = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")


class PolicySettingInputSerializer(StrictSerializer):
    key = serializers.ChoiceField(
        choices=(
            "final_approval_threshold",
            "procurement_method_threshold",
            "sla_policy",
            "approval_priority_policy",
        )
    )
    value = serializers.JSONField()
    description = serializers.CharField(required=False, allow_blank=True, default="")


class DiscrepancyResolutionSerializer(StrictSerializer):
    resolution_type = serializers.ChoiceField(
        choices=("replacement", "return", "warranty", "resolved")
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")
    communication = serializers.CharField(required=False, allow_blank=True, default="")


class ScheduledReportInputSerializer(StrictSerializer):
    report_code = serializers.ChoiceField(
        choices=("operations", "procurement", "stock", "financial")
    )
    frequency = serializers.ChoiceField(choices=("DAILY", "WEEKLY", "MONTHLY"))
    output_format = serializers.ChoiceField(choices=("json", "csv"), default="csv")
    filters = serializers.DictField(required=False, default=dict)
    next_run_at = serializers.DateTimeField()


class DepartmentAccessInputSerializer(StrictSerializer):
    user_id = serializers.IntegerField(min_value=1)
    department_id = serializers.IntegerField(min_value=1)


class StockBalanceSerializer(serializers.ModelSerializer):
    quantity_available = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = StockBalance
        fields = (
            "id",
            "sku",
            "item_name",
            "department_id",
            "quantity_on_hand",
            "quantity_reserved",
            "quantity_available",
            "is_central",
            "updated_at",
        )
        read_only_fields = fields


class StockTransferInputSerializer(StrictSerializer):
    source_department_id = serializers.IntegerField(min_value=1)
    destination_department_id = serializers.IntegerField(min_value=1)
    lines = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate_lines(self, lines):
        validated = []
        for line in lines:
            if set(line) - {"sku", "item_name", "quantity"}:
                raise serializers.ValidationError("A transfer line contains an unsupported field.")
            sku = str(line.get("sku", "")).strip()
            item_name = str(line.get("item_name", "")).strip()
            try:
                quantity = Decimal(str(line.get("quantity", "")))
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise serializers.ValidationError(
                    "Transfer quantities must be positive decimals."
                ) from exc
            if not sku or quantity <= 0:
                raise serializers.ValidationError(
                    "Each transfer line needs a SKU and positive quantity."
                )
            validated.append({"sku": sku, "item_name": item_name, "quantity": quantity})
        return validated


class TenderInputSerializer(StrictSerializer):
    indent_id = serializers.IntegerField(min_value=1)
    evaluation_criteria = serializers.ListField(child=serializers.JSONField(), allow_empty=False)


class TenderBidInputSerializer(StrictSerializer):
    vendor_id = serializers.IntegerField(min_value=1)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    proposal = serializers.DictField(required=False, default=dict)


class StockTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockTransfer
        fields = (
            "id",
            "reference",
            "source_department_id",
            "destination_department_id",
            "requested_by_user_id",
            "status",
            "lines",
            "dispatched_at",
            "received_at",
            "created_at",
        )
        read_only_fields = fields
