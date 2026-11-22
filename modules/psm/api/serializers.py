# Explicit-field DRF serializers for PSM read and write payloads.
from rest_framework import serializers


def _validate_choice(value: str, allowed: tuple[str, ...]) -> str:
    if value not in allowed:
        raise serializers.ValidationError(f"Must be one of: {', '.join(allowed)}.")
    return value


class PsmPolicySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    version = serializers.IntegerField(read_only=True)
    effective_from = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    direct_limit = serializers.DecimalField(max_digits=14, decimal_places=2)
    final_approval_threshold = serializers.DecimalField(max_digits=14, decimal_places=2)
    high_priority_direct_allowed = serializers.BooleanField(default=True)
    modifiable_states = serializers.ListField(
        child=serializers.CharField(max_length=32), required=False
    )
    withdrawable_states = serializers.ListField(
        child=serializers.CharField(max_length=32), required=False
    )
    sla_reminder_hours = serializers.IntegerField(min_value=1, default=24)
    sla_escalation_hours = serializers.IntegerField(min_value=2, default=48)
    high_priority_sla_reminder_hours = serializers.IntegerField(min_value=1, default=12)
    high_priority_sla_escalation_hours = serializers.IntegerField(min_value=2, default=24)
    partial_payment_enabled = serializers.BooleanField(default=True)
    duplicate_window_days = serializers.IntegerField(min_value=1, default=14)


class IndentVersionSerializer(serializers.Serializer):
    version = serializers.IntegerField(read_only=True)
    snapshot = serializers.JSONField(read_only=True)
    actor_user_id = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class IndentTransitionSerializer(serializers.Serializer):
    from_status = serializers.CharField(read_only=True)
    to_status = serializers.CharField(read_only=True)
    actor_user_id = serializers.IntegerField(read_only=True, allow_null=True)
    actor_role = serializers.CharField(read_only=True)
    reason = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class IndentReadSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    indent_number = serializers.CharField(read_only=True, allow_null=True)
    user_id = serializers.IntegerField(read_only=True)
    department = serializers.CharField(read_only=True)
    item_id = serializers.IntegerField(read_only=True, allow_null=True)
    item_description = serializers.CharField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    estimated_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    justification = serializers.CharField(read_only=True)
    priority = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    procurement_method = serializers.CharField(read_only=True)
    is_duplicate_flagged = serializers.BooleanField(read_only=True)
    duplicate_of_indent_id = serializers.IntegerField(read_only=True, allow_null=True)
    duplicate_reviewed = serializers.BooleanField(read_only=True)
    version = serializers.IntegerField(read_only=True)
    submitted_at = serializers.DateTimeField(read_only=True, allow_null=True)
    rejection_reason = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class IndentDetailSerializer(IndentReadSerializer):
    versions = IndentVersionSerializer(many=True, read_only=True)
    transitions = IndentTransitionSerializer(many=True, read_only=True)


class IndentCreateSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=64)
    item_id = serializers.IntegerField(required=False, allow_null=True)
    item_description = serializers.CharField(max_length=300)
    quantity = serializers.IntegerField()
    estimated_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    justification = serializers.CharField()
    submit = serializers.BooleanField(default=True)


class IndentUpdateSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=64, required=False)
    item_id = serializers.IntegerField(required=False, allow_null=True)
    item_description = serializers.CharField(max_length=300, required=False)
    quantity = serializers.IntegerField(required=False)
    estimated_cost = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    justification = serializers.CharField(required=False)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class DeptAdminReviewSerializer(serializers.Serializer):
    decision = serializers.CharField(max_length=20)
    priority = serializers.ChoiceField(choices=["normal", "high", "critical"], required=False)
    reason = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_decision(self, value: str) -> str:
        return _validate_choice(value, ("approve", "reject"))


class HodRecommendSerializer(serializers.Serializer):
    decision = serializers.CharField(max_length=20)
    reason = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_decision(self, value: str) -> str:
        return _validate_choice(value, ("recommend", "request_changes", "reject"))


class ProcurementReviewSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class FinalDecisionSerializer(serializers.Serializer):
    decision = serializers.CharField(max_length=20)
    reason = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_decision(self, value: str) -> str:
        return _validate_choice(value, ("approve", "reject"))


class StockItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    sku = serializers.CharField(max_length=40)
    name = serializers.CharField(max_length=200)
    category = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    unit = serializers.CharField(max_length=32, required=False, default="unit")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    is_active = serializers.BooleanField(read_only=True)


class StockLocationSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    code = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=120)
    department = serializers.CharField(max_length=64)
    is_central = serializers.BooleanField(default=False)


class StockAvailabilitySerializer(serializers.Serializer):
    item_id = serializers.IntegerField(read_only=True)
    sku = serializers.CharField(read_only=True)
    item_name = serializers.CharField(read_only=True)
    unit = serializers.CharField(read_only=True)
    location_id = serializers.IntegerField(read_only=True)
    location_code = serializers.CharField(read_only=True)
    location_name = serializers.CharField(read_only=True)
    department = serializers.CharField(read_only=True)
    is_central = serializers.BooleanField(read_only=True)
    on_hand = serializers.IntegerField(read_only=True)
    reserved = serializers.IntegerField(read_only=True)
    allocable = serializers.IntegerField(read_only=True)


class StockAdjustmentCreateSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    location_id = serializers.IntegerField()
    quantity_delta = serializers.IntegerField()
    reason = serializers.CharField(max_length=300)
    entry_type = serializers.ChoiceField(choices=["opening", "adjustment"], default="adjustment")
    source_ref_type = serializers.CharField(max_length=32, required=False, default="manual")
    source_ref_id = serializers.IntegerField(required=False, allow_null=True)


class StockLedgerEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    item_id = serializers.IntegerField(read_only=True)
    location_id = serializers.IntegerField(read_only=True)
    entry_type = serializers.CharField(read_only=True)
    quantity_delta = serializers.IntegerField(read_only=True)
    reason = serializers.CharField(read_only=True)
    actor_user_id = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class InternalIssueSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    indent_id = serializers.IntegerField(read_only=True)
    indent_number = serializers.CharField(source="indent.indent_number", read_only=True)
    item_description = serializers.CharField(source="indent.item_description", read_only=True)
    quantity = serializers.IntegerField(source="indent.quantity", read_only=True)
    location_id = serializers.IntegerField(read_only=True)
    location_code = serializers.CharField(source="location.code", read_only=True)
    status = serializers.CharField(read_only=True)
    picking_scheduled_at = serializers.DateTimeField(read_only=True, allow_null=True)
    dispatch_scheduled_at = serializers.DateTimeField(read_only=True, allow_null=True)
    dispatched_at = serializers.DateTimeField(read_only=True, allow_null=True)


class SchedulePickingSerializer(serializers.Serializer):
    picking_scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    dispatch_scheduled_at = serializers.DateTimeField(required=False, allow_null=True)


class StockTransferReadSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    transfer_number = serializers.CharField(read_only=True)
    item_id = serializers.IntegerField(read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    source_location_id = serializers.IntegerField(read_only=True)
    source_location_code = serializers.CharField(source="source_location.code", read_only=True)
    destination_location_id = serializers.IntegerField(read_only=True)
    destination_location_code = serializers.CharField(
        source="destination_location.code", read_only=True
    )
    quantity = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    notes = serializers.CharField(read_only=True)
    dispatched_at = serializers.DateTimeField(read_only=True, allow_null=True)
    confirmed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)


class StockTransferCreateSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    source_location_id = serializers.IntegerField()
    destination_location_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class VendorVersionSerializer(serializers.Serializer):
    version = serializers.IntegerField(read_only=True)
    snapshot = serializers.JSONField(read_only=True)
    changed_by_user_id = serializers.IntegerField(read_only=True)
    change_reason = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class VendorReadSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    code = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    gstin = serializers.CharField(read_only=True)
    bank_account_number = serializers.CharField(read_only=True)
    bank_ifsc = serializers.CharField(read_only=True)
    bank_name = serializers.CharField(read_only=True)
    compliance_documents = serializers.ListField(child=serializers.CharField(), read_only=True)
    contact_email = serializers.EmailField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    verified_at = serializers.DateTimeField(read_only=True, allow_null=True)
    version = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)


class VendorDetailSerializer(VendorReadSerializer):
    versions = VendorVersionSerializer(many=True, read_only=True)


class VendorWriteSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32, required=False, allow_blank=True)
    name = serializers.CharField(max_length=200)
    gstin = serializers.CharField(max_length=15, required=False, allow_blank=True, default="")
    bank_account_number = serializers.CharField(
        max_length=34, required=False, allow_blank=True, default=""
    )
    bank_ifsc = serializers.CharField(max_length=11, required=False, allow_blank=True, default="")
    bank_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    compliance_documents = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    contact_email = serializers.EmailField(required=False, allow_blank=True, default="")
    change_reason = serializers.CharField(
        max_length=300, required=False, allow_blank=True, default=""
    )


class VendorPatchSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    gstin = serializers.CharField(max_length=15, required=False, allow_blank=True)
    bank_account_number = serializers.CharField(max_length=34, required=False, allow_blank=True)
    bank_ifsc = serializers.CharField(max_length=11, required=False, allow_blank=True)
    bank_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    compliance_documents = serializers.ListField(child=serializers.CharField(), required=False)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    change_reason = serializers.CharField(
        max_length=300, required=False, allow_blank=True, default=""
    )


class TenderBidReadSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    vendor_id = serializers.IntegerField(read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    quoted_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    technical_score = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True, allow_null=True
    )
    financial_score = serializers.DecimalField(
        max_digits=6, decimal_places=2, read_only=True, allow_null=True
    )
    evaluation_notes = serializers.CharField(read_only=True)
    is_selected = serializers.BooleanField(read_only=True)


class TenderReadSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    tender_number = serializers.CharField(read_only=True)
    indent_id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    scope = serializers.CharField(read_only=True)
    evaluation_criteria = serializers.CharField(read_only=True)
    submission_deadline = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    committee_members = serializers.ListField(child=serializers.CharField(), read_only=True)
    committee_minutes = serializers.CharField(read_only=True)
    awarded_vendor_id = serializers.IntegerField(read_only=True, allow_null=True)
    bids = TenderBidReadSerializer(many=True, read_only=True)


class TenderCreateSerializer(serializers.Serializer):
    indent_id = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    scope = serializers.CharField()
    evaluation_criteria = serializers.CharField()
    submission_deadline = serializers.DateTimeField()


class TenderBidCreateSerializer(serializers.Serializer):
    vendor_id = serializers.IntegerField()
    quoted_amount = serializers.DecimalField(max_digits=14, decimal_places=2)


class TenderEvaluateItemSerializer(serializers.Serializer):
    bid_id = serializers.IntegerField()
    technical_score = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    financial_score = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True
    )
    evaluation_notes = serializers.CharField(required=False, allow_blank=True, default="")


class TenderEvaluateSerializer(serializers.Serializer):
    evaluations = TenderEvaluateItemSerializer(many=True)
    committee_members = serializers.ListField(child=serializers.CharField(), default=list)
    committee_minutes = serializers.CharField(required=False, allow_blank=True, default="")


class TenderAwardSerializer(serializers.Serializer):
    bid_id = serializers.IntegerField()
    committee_minutes = serializers.CharField(required=False, allow_blank=True, default="")


class PurchaseOrderReadSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    po_number = serializers.CharField(read_only=True)
    indent_id = serializers.IntegerField(read_only=True)
    indent_number = serializers.CharField(source="indent.indent_number", read_only=True)
    vendor_id = serializers.IntegerField(read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    tender_id = serializers.IntegerField(read_only=True, allow_null=True)
    ordered_quantity = serializers.IntegerField(read_only=True)
    unit_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)
    planned_delivery_date = serializers.DateField(read_only=True)
    actual_delivery_date = serializers.DateField(read_only=True, allow_null=True)
    delivery_notes = serializers.CharField(read_only=True)
    issued_at = serializers.DateTimeField(read_only=True)


class PurchaseOrderCreateSerializer(serializers.Serializer):
    indent_id = serializers.IntegerField()
    vendor_id = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=14, decimal_places=2)
    planned_delivery_date = serializers.DateField()
    ordered_quantity = serializers.IntegerField(required=False, allow_null=True)
    tender_id = serializers.IntegerField(required=False, allow_null=True)
    delivery_notes = serializers.CharField(required=False, allow_blank=True, default="")


class PurchaseOrderUpdateSerializer(serializers.Serializer):
    status = serializers.CharField(required=False)
    planned_delivery_date = serializers.DateField(required=False)
    actual_delivery_date = serializers.DateField(required=False, allow_null=True)
    delivery_notes = serializers.CharField(required=False, allow_blank=True)


class GrnReadSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    grn_number = serializers.CharField(read_only=True)
    purchase_order_id = serializers.IntegerField(read_only=True, allow_null=True)
    internal_issue_id = serializers.IntegerField(read_only=True, allow_null=True)
    replacement_for_case_id = serializers.IntegerField(read_only=True, allow_null=True)
    inspected_by_user_id = serializers.IntegerField(read_only=True)
    received_quantity = serializers.IntegerField(read_only=True)
    accepted_quantity = serializers.IntegerField(read_only=True)
    rejected_quantity = serializers.IntegerField(read_only=True)
    inspection_notes = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    confirmed_by_user_id = serializers.IntegerField(read_only=True, allow_null=True)
    confirmed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    stock_posted = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class GrnCreateSerializer(serializers.Serializer):
    purchase_order_id = serializers.IntegerField(required=False, allow_null=True)
    internal_issue_id = serializers.IntegerField(required=False, allow_null=True)
    replacement_for_case_id = serializers.IntegerField(required=False, allow_null=True)
    received_quantity = serializers.IntegerField()
    accepted_quantity = serializers.IntegerField()
    rejected_quantity = serializers.IntegerField(default=0)
    inspection_notes = serializers.CharField(required=False, allow_blank=True, default="")


class DiscrepancyCommSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    sender_label = serializers.CharField(max_length=120)
    message = serializers.CharField()
    recorded_by_user_id = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class DiscrepancyReadSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    case_number = serializers.CharField(read_only=True)
    grn_id = serializers.IntegerField(read_only=True)
    reported_by_user_id = serializers.IntegerField(read_only=True)
    discrepancy_type = serializers.CharField(read_only=True)
    affected_quantity = serializers.IntegerField(read_only=True)
    description = serializers.CharField(read_only=True)
    evidence_url = serializers.CharField(read_only=True)
    evidence_filename = serializers.CharField(read_only=True)
    requested_resolution = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    replacement_count = serializers.IntegerField(read_only=True)
    resolution_notes = serializers.CharField(read_only=True)
    inventory_adjusted = serializers.BooleanField(read_only=True)
    accounting_adjusted = serializers.BooleanField(read_only=True)
    communications = DiscrepancyCommSerializer(many=True, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class DiscrepancyCreateSerializer(serializers.Serializer):
    grn_id = serializers.IntegerField()
    discrepancy_type = serializers.ChoiceField(
        choices=["damage", "shortage", "wrong_item", "quality_defect"]
    )
    affected_quantity = serializers.IntegerField()
    description = serializers.CharField()
    requested_resolution = serializers.ChoiceField(
        choices=["return", "replacement", "warranty", "adjustment"]
    )
    evidence_url = serializers.CharField(required=False, allow_blank=True, default="")
    evidence_filename = serializers.CharField(required=False, allow_blank=True, default="")


class DiscrepancyResolveSerializer(serializers.Serializer):
    resolution_action = serializers.ChoiceField(choices=["await_replacement", "resolve", "close"])
    resolution_notes = serializers.CharField()
    inventory_adjusted = serializers.BooleanField(default=False)
    accounting_adjusted = serializers.BooleanField(default=False)


class PaymentReadSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    payment_reference = serializers.CharField(read_only=True)
    is_partial = serializers.BooleanField(read_only=True)
    status = serializers.CharField(read_only=True)
    processed_by_user_id = serializers.IntegerField(read_only=True)
    notes = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class InvoiceReadSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    invoice_number = serializers.CharField(read_only=True)
    purchase_order_id = serializers.IntegerField(read_only=True)
    po_number = serializers.CharField(source="purchase_order.po_number", read_only=True)
    vendor_id = serializers.IntegerField(read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    billed_quantity = serializers.IntegerField(read_only=True)
    billed_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    eligible_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)
    hold_reason = serializers.CharField(read_only=True)
    verified_at = serializers.DateTimeField(read_only=True, allow_null=True)
    payments = PaymentReadSerializer(many=True, read_only=True)


class InvoiceCreateSerializer(serializers.Serializer):
    purchase_order_id = serializers.IntegerField()
    invoice_number = serializers.CharField(max_length=64)
    billed_quantity = serializers.IntegerField()
    billed_amount = serializers.DecimalField(max_digits=14, decimal_places=2)


class PaymentCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    payment_reference = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ReportGenerateSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(
        choices=["operational", "procurement", "stock", "financial"]
    )
    filters = serializers.DictField(required=False, default=dict)


class ReportScheduleReadSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    report_type = serializers.CharField(read_only=True)
    filters = serializers.DictField(read_only=True)
    cadence = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    last_run_at = serializers.DateTimeField(read_only=True, allow_null=True)
    next_run_at = serializers.DateTimeField(read_only=True)


class ReportScheduleCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    report_type = serializers.ChoiceField(
        choices=["operational", "procurement", "stock", "financial"]
    )
    cadence = serializers.ChoiceField(choices=["daily", "weekly", "monthly"])
    filters = serializers.DictField(required=False, default=dict)


class ReportSchedulePatchSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)
    cadence = serializers.ChoiceField(choices=["daily", "weekly", "monthly"], required=False)


class AuditLogSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    actor_user_id = serializers.IntegerField(read_only=True, allow_null=True)
    actor_role = serializers.CharField(read_only=True)
    action = serializers.CharField(read_only=True)
    target_type = serializers.CharField(read_only=True)
    target_id = serializers.IntegerField(read_only=True)
    from_state = serializers.CharField(read_only=True)
    to_state = serializers.CharField(read_only=True)
    details = serializers.DictField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class NotificationSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    topic = serializers.CharField(read_only=True)
    subject = serializers.CharField(read_only=True)
    body = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    sent_at = serializers.DateTimeField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)


class DashboardSerializer(serializers.Serializer):
    active_role = serializers.CharField(read_only=True)
    indents_total = serializers.IntegerField(read_only=True)
    indents_pending_approval = serializers.IntegerField(read_only=True)
    indents_by_status = serializers.DictField(read_only=True)
    purchase_orders_total = serializers.IntegerField(read_only=True)
    purchase_orders_by_status = serializers.DictField(read_only=True)
    open_discrepancies = serializers.IntegerField(read_only=True)
    pending_transfers = serializers.IntegerField(read_only=True)
    invoices_on_hold = serializers.IntegerField(read_only=True)
    invoices_pending_payment = serializers.IntegerField(read_only=True)
