from rest_framework import serializers

from modules.department.models import (
    Announcement,
    DepartmentChange,
    DepartmentDetails,
    Feedback,
    InventoryItem,
    StockMovement,
    StockRequest,
    ResourceProfile,
    TimetableEntry,
)


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ("id", "title", "body", "target_roles", "target_programmes",
                  "target_academic_years", "status", "created_at")
        read_only_fields = fields


class AnnouncementWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=180)
    body = serializers.CharField(max_length=5000)
    target_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=("student", "faculty", "dept_admin", "hod")),
        min_length=1)
    target_programmes = serializers.ListField(
        child=serializers.CharField(max_length=80), min_length=1)
    target_academic_years = serializers.ListField(
        child=serializers.CharField(max_length=24), min_length=1)


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ("id", "name", "description", "quantity", "updated_at")
        read_only_fields = fields


class InventoryInsertSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=140)
    description = serializers.CharField(max_length=500, required=False,
                                        allow_blank=True, default="")
    quantity = serializers.IntegerField(min_value=1)


class StockRequestSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = StockRequest
        fields = ("id", "item", "item_name", "faculty_user_id", "quantity",
                  "status", "decision_note", "created_at")
        read_only_fields = fields


class StockRequestWriteSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approve", "reject"))
    note = serializers.CharField(max_length=300, required=False,
                                 allow_blank=True, default="")


class DepartmentChangeDecisionSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=300, required=False,
                                 allow_blank=True, default="")


class StockMovementSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = StockMovement
        fields = ("id", "item_name", "movement", "quantity", "actor_user_id",
                  "created_at")
        read_only_fields = fields


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ("id", "submitter_user_id", "body", "category", "status",
                  "initial_reviewed_by_user_id", "initial_reviewed_at",
                  "handled_by_user_id", "created_at")
        read_only_fields = fields


class FeedbackWriteSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=5000)


class FeedbackReviewSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=80)
    disposition = serializers.ChoiceField(
        choices=("", "resolved", "closed"), required=False, default="")


class FeedbackDispositionSerializer(serializers.Serializer):
    disposition = serializers.ChoiceField(choices=("resolved", "closed"))


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceProfile
        fields = ("id", "name", "description", "location", "equipment",
                  "updated_at")
        read_only_fields = fields


class ResourceWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=140)
    description = serializers.CharField(max_length=1000, required=False,
                                        allow_blank=True, default="")
    location = serializers.CharField(max_length=180, required=False,
                                     allow_blank=True, default="")
    equipment = serializers.ListField(
        child=serializers.CharField(max_length=120), required=False, default=list)


class TimetableSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimetableEntry
        fields = ("id", "programme", "academic_year", "course", "day",
                  "starts_at", "ends_at", "room", "updated_at")
        read_only_fields = fields


class TimetableWriteSerializer(serializers.Serializer):
    programme = serializers.CharField(max_length=80, required=False,
                                      allow_blank=True, default="")
    academic_year = serializers.CharField(max_length=24, required=False,
                                          allow_blank=True, default="")
    course = serializers.CharField(max_length=120)
    day = serializers.IntegerField(min_value=1, max_value=7)
    starts_at = serializers.TimeField()
    ends_at = serializers.TimeField()
    room = serializers.CharField(max_length=100)

    def validate(self, attrs):
        if attrs["ends_at"] <= attrs["starts_at"]:
            raise serializers.ValidationError(
                {"ends_at": "End time must be later than start time."})
        return attrs


class DepartmentDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentDetails
        fields = ("general", "official", "updated_at")
        read_only_fields = fields


class GeneralDetailsWriteSerializer(serializers.Serializer):
    general = serializers.DictField()


class OfficialChangeWriteSerializer(serializers.Serializer):
    field_name = serializers.CharField(max_length=80)
    proposed_value = serializers.JSONField()

    def validate_field_name(self, value):
        normalized = "".join(char for char in value.casefold() if char.isalnum())
        if normalized in {"headship", "hod", "headofdepartment", "departmenthead"}:
            raise serializers.ValidationError(
                "Headship comes from the central HOD assignment.")
        return value.strip()


class DepartmentChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentChange
        fields = ("id", "field_name", "proposed_value", "status",
                  "proposed_by_user_id", "decision_note", "created_at")
        read_only_fields = fields
