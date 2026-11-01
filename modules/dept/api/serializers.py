from rest_framework import serializers

from modules.dept.models import (
    Announcement,
    Feedback,
    FeedbackEvent,
    InventoryItem,
    StockMovement,
    StockRequest,
)


# -- announcements -------------------------------------------------------------
class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        ref_name = "DeptAnnouncement"
        fields = ["id", "title", "body", "target_roles", "target_programmes",
                  "target_years", "status", "published_by_user_id",
                  "published_by_role", "created_at", "updated_at"]
        read_only_fields = fields


class AnnouncementWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
    target_roles = serializers.ListField(child=serializers.CharField(),
                                         required=False, default=list)
    target_programmes = serializers.ListField(child=serializers.CharField(),
                                              required=False, default=list)
    target_years = serializers.ListField(child=serializers.IntegerField(),
                                         required=False, default=list)


class AnnouncementEditSerializer(AnnouncementWriteSerializer):
    title = serializers.CharField(max_length=200, required=False)
    body = serializers.CharField(required=False)

    def validate(self, attrs):
        # partial: only fields the caller actually sent
        return {k: v for k, v in attrs.items() if k in self.initial_data}


class AnnouncementStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[c for c, _ in Announcement.STATUS])


# -- stock ---------------------------------------------------------------------
class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ["id", "name", "category", "unit", "quantity"]
        read_only_fields = fields


class InventoryWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    quantity = serializers.IntegerField(min_value=1)
    category = serializers.CharField(max_length=60, required=False, default="")
    unit = serializers.CharField(max_length=20, required=False, default="pcs")


class StockRequestSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    unit = serializers.CharField(source="item.unit", read_only=True)

    class Meta:
        model = StockRequest
        fields = ["id", "item", "item_name", "unit", "requested_by_user_id",
                  "quantity", "purpose", "status", "decided_by_user_id",
                  "decided_at", "decision_note", "issued_by_user_id",
                  "issued_at", "created_at"]
        read_only_fields = fields


class StockRequestWriteSerializer(serializers.Serializer):
    item = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    purpose = serializers.CharField(max_length=300, required=False, default="")


class StockDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    note = serializers.CharField(max_length=300, required=False, default="")


class StockMovementSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = StockMovement
        fields = ["id", "item", "item_name", "kind", "quantity", "request",
                  "recipient_user_id", "actor_user_id", "at"]
        read_only_fields = fields


# -- feedback ------------------------------------------------------------------
class FeedbackEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackEvent
        fields = ["from_status", "to_status", "actor_user_id", "note", "at"]
        read_only_fields = fields


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ["id", "subject", "body", "category", "status",
                  "resolution_note", "submitted_by_role", "created_at",
                  "updated_at"]
        read_only_fields = fields


class FeedbackWriteSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    body = serializers.CharField()


class FeedbackMoveSerializer(serializers.Serializer):
    to_status = serializers.ChoiceField(
        choices=["under_review", "resolved", "closed"])
    category = serializers.CharField(max_length=60, required=False, default="")
    note = serializers.CharField(max_length=500, required=False, default="")
