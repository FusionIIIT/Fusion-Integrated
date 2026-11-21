from rest_framework import serializers
from modules.cms.models import (
    Complaint,
    ComplaintAttachment,
    ComplaintProgress,
    ComplaintReopening,
    ComplaintFeedback,
    ComplaintAnnouncement,
    CmsRoleAssignment,
)

class ComplaintAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintAttachment
        fields = '__all__'
        read_only_fields = ['id', 'uploaded_at']

class ComplaintProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintProgress
        fields = '__all__'
        read_only_fields = ['id', 'timestamp']

class ComplaintReopeningSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintReopening
        fields = '__all__'
        read_only_fields = ['id', 'requested_at', 'decided_at']

class ComplaintFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintFeedback
        fields = '__all__'
        read_only_fields = ['id', 'complainant_user_id', 'submitted_at']

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

class ComplaintAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintAnnouncement
        fields = '__all__'
        read_only_fields = ['id', 'author_user_id', 'published_at']

class CmsRoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CmsRoleAssignment
        fields = '__all__'
        read_only_fields = ['id', 'assigned_by_id', 'created_at']

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
        return attrs

class ComplaintSerializer(serializers.ModelSerializer):
    attachments = ComplaintAttachmentSerializer(many=True, read_only=True)
    progress_history = ComplaintProgressSerializer(many=True, read_only=True)
    reopenings = ComplaintReopeningSerializer(many=True, read_only=True)
    feedbacks = ComplaintFeedbackSerializer(many=True, read_only=True)

    class Meta:
        model = Complaint
        fields = '__all__'
        read_only_fields = [
            'id', 'complaint_id', 'complainant_user_id', 'submission_timestamp',
            'status', 'closure_timestamp', 'is_escalated', 'escalation_type',
            'escalation_timestamp', 'sla_due_date', 'sla_reminder_sent',
            'user_verified', 'supervisor_verified', 'created_at', 'updated_at'
        ]

class ComplaintCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = [
            'id', 'complaint_id', 'complainant_user_id', 'category', 'description',
            'priority', 'status', 'requires_supervisor_verification', 'submission_timestamp',
        ]
        read_only_fields = [
            'id', 'complaint_id', 'complainant_user_id', 'status', 'submission_timestamp',
        ]

    def validate_category(self, value):
        valid = [c[0] for c in Complaint.CATEGORY_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(f"Invalid category '{value}'. Allowed: {valid}")
        return value

    def validate_description(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Description is mandatory.")
        return value.strip()

    def create(self, validated_data):
        if 'complaint_id' not in validated_data or not validated_data['complaint_id']:
            validated_data['complaint_id'] = Complaint.generate_unique_complaint_id()
        return super().create(validated_data)

class ComplaintAssignSerializer(serializers.Serializer):
    assigned_handler_id = serializers.IntegerField(required=False)
    handler_id = serializers.IntegerField(required=False)
    priority = serializers.ChoiceField(choices=['Low', 'Medium', 'High'], default='Low')
    category = serializers.ChoiceField(choices=[c[0] for c in Complaint.CATEGORY_CHOICES], required=False)

    def validate(self, attrs):
        hid = attrs.get('assigned_handler_id') or attrs.get('handler_id')
        if not hid:
            raise serializers.ValidationError("Either assigned_handler_id or handler_id is required.")
        attrs['assigned_handler_id'] = hid
        return attrs

class ComplaintProgressUpdateSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=True, min_length=1)

class ComplaintResolveSerializer(serializers.Serializer):
    resolution_details = serializers.CharField(required=True, min_length=3)

class ComplaintRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(required=True, min_length=3)

class ComplaintClosureVerificationSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default='')

class ComplaintReopeningRequestSerializer(serializers.Serializer):
    dissatisfaction_reason = serializers.CharField(required=True, min_length=3)

class ComplaintReopeningDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['approve', 'approved', 'deny', 'denied'])
    supervisor_remarks = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_decision(self, value):
        if value in ['approve', 'approved']:
            return 'approve'
        return 'deny'

class ComplaintManualEscalateSerializer(serializers.Serializer):
    escalation_remarks = serializers.CharField(required=True, min_length=3)
