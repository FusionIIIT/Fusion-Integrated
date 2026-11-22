"""MMS API serializers. Every `fields` list is explicit; server-owned fields
are read-only (status, owner user_id, approver, timestamps)."""

from __future__ import annotations

from rest_framework import serializers

from modules.mms.models import (
    Announcement,
    Deregistration,
    Feedback,
    MenuItem,
    MonthlyBill,
    NotificationOutbox,
    RebateRequest,
    Registration,
    RegistrationWindow,
    RoleAssignment,
    SpecialFoodCharge,
    SpecialFoodPolicy,
    SpecialFoodRequest,
    SpecialFoodTransition,
    VacationResponse,
    VacationSurvey,
)


class SpecialFoodRequestSerializer(serializers.ModelSerializer):
    student_user_id = serializers.IntegerField(source="user_id", read_only=True)

    class Meta:
        model = SpecialFoodRequest
        fields = [
            "id",
            "user_id",
            "student_user_id",
            "reason",
            "requested_date",
            "status",
            "decision_due_at",
            "decided_at",
            "decided_by_user_id",
            "decision_note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "student_user_id",
            "status",
            "decision_due_at",
            "decided_at",
            "decided_by_user_id",
            "created_at",
            "updated_at",
        ]


class SpecialFoodRequestCreateSerializer(serializers.Serializer):
    reason = serializers.CharField()
    requested_date = serializers.DateField()


class SpecialFoodDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class SpecialFoodFulfillSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["served", "cancelled"])
    note = serializers.CharField(required=False, allow_blank=True, default="")


class SpecialFoodChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialFoodCharge
        fields = [
            "id",
            "request",
            "student_user_id",
            "month",
            "amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SpecialFoodPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialFoodPolicy
        fields = [
            "id",
            "decision_period_hours",
            "effective_from",
            "effective_until",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SpecialFoodTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialFoodTransition
        fields = [
            "id",
            "request",
            "from_status",
            "to_status",
            "actor_user_id",
            "occurred_at",
            "note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RegistrationSerializer(serializers.ModelSerializer):
    student_user_id = serializers.IntegerField(source="user_id", read_only=True)

    class Meta:
        model = Registration
        fields = [
            "id",
            "user_id",
            "student_user_id",
            "status",
            "submitted_at",
            "decided_at",
            "decided_by_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "student_user_id",
            "status",
            "submitted_at",
            "decided_at",
            "decided_by_user_id",
            "created_at",
            "updated_at",
        ]


class RegistrationDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class RegistrationWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationWindow
        fields = [
            "id",
            "cycle_or_period",
            "opens_at",
            "closes_at",
            "is_open",
            "opened_by_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_open",
            "opened_by_user_id",
            "created_at",
            "updated_at",
        ]


class RegistrationWindowCreateSerializer(serializers.Serializer):
    cycle_or_period = serializers.CharField(max_length=120)
    opens_at = serializers.DateTimeField()
    closes_at = serializers.DateTimeField()


class DeregistrationSerializer(serializers.ModelSerializer):
    student_user_id = serializers.IntegerField(source="user_id", read_only=True)

    class Meta:
        model = Deregistration
        fields = [
            "id",
            "user_id",
            "student_user_id",
            "status",
            "effective_date",
            "submitted_at",
            "decided_at",
            "decided_by_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "student_user_id",
            "status",
            "effective_date",
            "submitted_at",
            "decided_at",
            "decided_by_user_id",
            "created_at",
            "updated_at",
        ]


class DeregistrationDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class RebateRequestSerializer(serializers.ModelSerializer):
    student_user_id = serializers.IntegerField(source="user_id", read_only=True)

    class Meta:
        model = RebateRequest
        fields = [
            "id",
            "user_id",
            "student_user_id",
            "reason",
            "explanation",
            "start_date",
            "end_date",
            "status",
            "approved_start_date",
            "approved_end_date",
            "decided_at",
            "decided_by_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "student_user_id",
            "status",
            "approved_start_date",
            "approved_end_date",
            "decided_at",
            "decided_by_user_id",
            "created_at",
            "updated_at",
        ]


class RebateRequestCreateSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(
        choices=["medical", "institute_leave", "family_function", "other"]
    )
    explanation = serializers.CharField(required=False, allow_blank=True, default="")
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class RebateDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    approved_start_date = serializers.DateField(required=False, allow_null=True)
    approved_end_date = serializers.DateField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = [
            "id",
            "day",
            "meal",
            "item",
            "published_at",
            "created_by_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "published_at",
            "created_by_user_id",
            "created_at",
            "updated_at",
        ]


class MenuItemCreateSerializer(serializers.Serializer):
    day = serializers.DateField()
    meal = serializers.ChoiceField(choices=["breakfast", "lunch", "dinner"])
    item = serializers.CharField()


class MonthlyBillSerializer(serializers.ModelSerializer):
    student_user_id = serializers.IntegerField(source="user_id", read_only=True)

    class Meta:
        model = MonthlyBill
        fields = [
            "id",
            "user_id",
            "student_user_id",
            "month",
            "state",
            "served_day_charges",
            "special_meal_charges",
            "rebate_deductions",
            "total",
            "generated_at",
            "finalized_at",
            "published_at",
            "finalized_by_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "student_user_id",
            "month",
            "state",
            "served_day_charges",
            "special_meal_charges",
            "rebate_deductions",
            "total",
            "generated_at",
            "finalized_at",
            "published_at",
            "finalized_by_user_id",
            "created_at",
            "updated_at",
        ]


class MonthlyBillTransitionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["finalize", "publish"])


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "body",
            "publisher_user_id",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "publisher_user_id",
            "published_at",
            "created_at",
            "updated_at",
        ]


class AnnouncementCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()


class FeedbackSerializer(serializers.ModelSerializer):
    student_user_id = serializers.IntegerField(source="user_id", read_only=True)

    class Meta:
        model = Feedback
        fields = [
            "id",
            "user_id",
            "student_user_id",
            "text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "student_user_id",
            "created_at",
            "updated_at",
        ]


class FeedbackCreateSerializer(serializers.Serializer):
    text = serializers.CharField()


class VacationSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationSurvey
        fields = [
            "id",
            "vacation",
            "response_deadline",
            "is_open",
            "created_by_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_open",
            "created_by_user_id",
            "created_at",
            "updated_at",
        ]


class VacationSurveyCreateSerializer(serializers.Serializer):
    vacation = serializers.CharField(max_length=120)
    response_deadline = serializers.DateTimeField()


class VacationResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationResponse
        fields = [
            "id",
            "survey",
            "student_user_id",
            "response",
            "responded_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "student_user_id",
            "responded_at",
            "created_at",
            "updated_at",
        ]


class VacationResponseCreateSerializer(serializers.Serializer):
    response = serializers.ChoiceField(choices=["yes", "no"])


class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAssignment
        fields = [
            "id",
            "designation",
            "employee_user_id",
            "effective_from",
            "effective_until",
            "is_active",
            "assigned_by_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "assigned_by_user_id",
            "created_at",
            "updated_at",
        ]


class RoleAssignmentCreateSerializer(serializers.Serializer):
    designation = serializers.ChoiceField(choices=["caretaker", "warden"])
    employee_user_id = serializers.IntegerField()
    effective_from = serializers.DateTimeField()
    effective_until = serializers.DateTimeField(required=False, allow_null=True)


class NotificationOutboxSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationOutbox
        fields = [
            "id",
            "topic",
            "dedupe_key",
            "recipient_user_id",
            "recipient_email",
            "subject",
            "body",
            "payload",
            "status",
            "attempts",
            "last_error",
            "sent_at",
            "claimed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OperationalReportSerializer(serializers.Serializer):
    period = serializers.CharField()
    total_registered_students = serializers.IntegerField()
    pending_registrations = serializers.IntegerField()
    active_rebates = serializers.IntegerField()
    pending_special_food = serializers.IntegerField()
    bills_generated = serializers.IntegerField()
    feedback_count = serializers.IntegerField()


class SupervisoryReportSerializer(serializers.Serializer):
    period = serializers.CharField()
    total_billed_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_rebate_deductions = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_special_food_charges = serializers.DecimalField(max_digits=12, decimal_places=2)
    survey_participation_rate = serializers.FloatField()
    feedback_count = serializers.IntegerField()
