from rest_framework import serializers

from modules.department.models import InventoryItem, StockMovement, StockRequest


class DeptInventoryItemSerializer(serializers.ModelSerializer):
    """Serializes an InventoryItem model instance."""
    class Meta:
        model = InventoryItem
        fields = ["id", "department", "name", "unit", "quantity"]


class DeptInventoryWriteSerializer(serializers.Serializer):
    """Serializes data for creating or updating an InventoryItem."""
    department = serializers.IntegerField()
    name = serializers.CharField()
    unit = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)


class DeptStockRequestSerializer(serializers.ModelSerializer):
    """Serializes a StockRequest model instance."""
    class Meta:
        model = StockRequest
        fields = [
            "id",
            "department",
            "item",
            "requester_user_id",
            "quantity",
            "state",
            "decided_by_user_id",
            "decided_at",
            "issued_by_user_id",
            "issued_at",
        ]


class DeptStockRequestWriteSerializer(serializers.Serializer):
    """Serializes data for creating a StockRequest."""
    item = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class DeptStockDecisionSerializer(serializers.Serializer):
    """Serializes data for making a stock decision."""
    outcome = serializers.ChoiceField(choices=[
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ])


class DeptStockMovementSerializer(serializers.ModelSerializer):
    """Serializes a StockMovement model instance."""
    class Meta:
        model = StockMovement
        fields = [
            "id",
            "item",
            "kind",
            "quantity",
            "request",
            "actor_user_id",
            "created_at",
        ]
