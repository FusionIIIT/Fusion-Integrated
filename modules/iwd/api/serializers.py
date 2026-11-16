from rest_framework import serializers

from modules.iwd.models import IwdAuditEvent, IwdComplaint, IwdEstimate


class ComplaintWriteSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    location = serializers.CharField()
    issue_category = serializers.CharField(required=False, default="other")
    urgency = serializers.ChoiceField(
        choices=("low", "normal", "high", "critical"), required=False, default="normal"
    )
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    urgent = serializers.BooleanField(required=False, default=False)
    metadata = serializers.JSONField(required=False, default=dict)


class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = IwdComplaint
        fields = "__all__"


class EstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IwdEstimate
        fields = "__all__"


class ActionSerializer(serializers.Serializer):
    assessment = serializers.JSONField(required=False)
    needs_site_information = serializers.BooleanField(required=False, default=False)
    total_cost = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    details = serializers.JSONField(required=False)
    estimated_time = serializers.CharField(required=False, allow_blank=True)
    materials = serializers.ListField(required=False)
    outcome = serializers.CharField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True)
    remarks = serializers.CharField(required=False, allow_blank=True)
    accepted = serializers.BooleanField(required=False)
    progress = serializers.CharField(required=False, allow_blank=True)
    complete = serializers.BooleanField(required=False, default=False)
    sku = serializers.CharField(required=False)
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, required=False)
    invoice_number = serializers.CharField(required=False)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    supporting_records = serializers.JSONField(required=False)
    approved = serializers.BooleanField(required=False)
    status = serializers.CharField(required=False)
    rating = serializers.IntegerField(required=False, allow_null=True)
    comments = serializers.CharField(required=False, allow_blank=True)
    post_repair_issue = serializers.CharField(required=False, allow_blank=True)


class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = IwdAuditEvent
        fields = "__all__"
