from rest_framework import serializers

from modules.iwd.models import Contractor, InventoryItem, WorkRequest, WorkRequestLog


class WorkRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkRequest
        fields = [
            "id", "title", "description", "location", "category",
            "priority", "status", "requester_username", "assigned_to",
            "estimated_cost", "actual_cost", "required_by",
            "submitted_at", "completed_at", "created_at", "updated_at", "remarks",
        ]
        read_only_fields = ["id", "status", "submitted_at", "completed_at", "created_at", "updated_at"]


class WorkRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkRequest
        fields = [
            "id", "title", "description", "location", "category",
            "priority", "status", "estimated_cost", "required_by",
        ]
        read_only_fields = ["id", "status"]

    def validate_title(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Title must be at least 5 characters.")
        return value

    def validate_description(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Description must be at least 10 characters.")
        return value

    def validate_estimated_cost(self, value):
        if value < 0:
            raise serializers.ValidationError("Estimated cost cannot be negative.")
        return value


class ContractorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contractor
        fields = "__all__"
        read_only_fields = ["id", "registered_on"]


class InventoryItemSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id", "name", "unit", "quantity_available",
            "unit_cost", "minimum_stock", "last_restocked",
            "created_at", "is_low_stock",
        ]
        read_only_fields = ["id", "created_at", "is_low_stock"]


class WorkRequestLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkRequestLog
        fields = ["id", "from_status", "to_status", "actor_username", "note", "changed_at"]
        read_only_fields = fields

