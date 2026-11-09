from rest_framework import serializers

from modules.mms.models import (
    Announcement,
    Feedback,
    MenuEntry,
    MenuWeek,
    MonthlyBill,
    RebateHistory,
    RebateRequest,
    RegistrationWindow,
    RequestHistory,
    RoleAssignment,
    SpecialFoodHistory,
    SpecialFoodRequest,
    StudentRequest,
    VacationResponse,
    VacationSurvey,
)


class RoleAssignmentSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = RoleAssignment
        fields = ["id", "role", "user_id", "starts_at", "ends_at", "is_current",
                  "assigned_by_user_id", "created_at"]
        read_only_fields = ["id", "is_current", "assigned_by_user_id", "created_at"]

    def get_is_current(self, row):
        from django.utils import timezone

        now = timezone.now()
        return row.is_current and row.starts_at <= now < row.ends_at


class RegistrationWindowSerializer(serializers.ModelSerializer):
    is_open = serializers.SerializerMethodField()

    class Meta:
        model = RegistrationWindow
        fields = ["id", "cycle", "opens_at", "closes_at", "opened_by_user_id",
                  "is_open"]
        read_only_fields = ["id", "opened_by_user_id", "is_open"]

    def get_is_open(self, row):
        from django.utils import timezone
        now = timezone.now()
        return row.opens_at <= now < row.closes_at


class RequestHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestHistory
        fields = ["status", "actor_user_id", "note", "at"]


class StudentRequestSerializer(serializers.ModelSerializer):
    history = RequestHistorySerializer(many=True, read_only=True)

    class Meta:
        model = StudentRequest
        fields = ["id", "user_id", "kind", "status", "window_id",
                  "created_at", "decided_by_user_id", "decided_at",
                  "effective_at", "history"]
        read_only_fields = fields


class MenuEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuEntry
        fields = ["id", "day", "meal", "item"]
        read_only_fields = ["id"]


class MenuWeekSerializer(serializers.ModelSerializer):
    entries = MenuEntrySerializer(many=True, read_only=True)

    class Meta:
        model = MenuWeek
        fields = ["id", "week_start", "published_at", "entries"]
        read_only_fields = fields


class RebateSerializer(serializers.ModelSerializer):
    history = serializers.SerializerMethodField()

    class Meta:
        model = RebateRequest
        fields = ["id", "user_id", "reason", "explanation", "starts_on",
                  "ends_on", "status", "created_at", "decided_by_user_id",
                  "decided_at", "history"]
        read_only_fields = fields

    def get_history(self, row):
        return RebateHistorySerializer(row.history.all(), many=True).data


class RebateHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RebateHistory
        fields = ["status", "actor_user_id", "note", "at"]


class VacationSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationSurvey
        fields = ["id", "title", "vacation_starts_on", "vacation_ends_on",
                  "deadline", "created_by_user_id", "created_at"]
        read_only_fields = fields


class VacationResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationResponse
        fields = ["user_id", "response", "is_default", "responded_at"]
        read_only_fields = fields


class SpecialFoodHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialFoodHistory
        fields = ["status", "actor_user_id", "at"]


class SpecialFoodSerializer(serializers.ModelSerializer):
    history = SpecialFoodHistorySerializer(many=True, read_only=True)

    class Meta:
        model = SpecialFoodRequest
        fields = ["id", "user_id", "reason", "details", "requested_for",
                  "status", "created_at", "decided_at", "decided_by_user_id",
                  "charge_amount", "history"]
        read_only_fields = fields


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ["id", "title", "body", "published_by_user_id",
                  "published_by_role", "published_at"]
        read_only_fields = fields


class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyBill
        fields = ["id", "user_id", "year", "month", "daily_rate",
                  "served_days", "special_food_charges", "rebate_deduction",
                  "total", "status", "finalized_by_user_id", "finalized_at",
                  "published_at"]
        read_only_fields = fields


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ["id", "user_id", "message", "created_at"]
        read_only_fields = fields
