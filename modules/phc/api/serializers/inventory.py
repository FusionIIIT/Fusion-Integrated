from rest_framework import serializers
from modules.phc.models import InventoryItem, StockAdjustment, Requisition, RequisitionLine

class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ["id", "name", "unit", "quantity", "reorder_threshold"]
        read_only_fields = ["id", "quantity"]

class StockAdjustmentSerializer(serializers.Serializer):
    delta = serializers.IntegerField()
    reason = serializers.CharField(max_length=200)

class RequisitionLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequisitionLine
        fields = ["id", "item", "quantity"]
        read_only_fields = ["id"]

class RequisitionSerializer(serializers.ModelSerializer):
    lines = RequisitionLineSerializer(many=True, read_only=True)
    
    class Meta:
        model = Requisition
        fields = [
            "id", "requested_by_user_id", "status", "created_at",
            "decided_by_user_id", "decided_at", "lines"
        ]
        read_only_fields = ["id", "requested_by_user_id", "status", "created_at", "decided_by_user_id", "decided_at"]

class RequisitionCreateSerializer(serializers.Serializer):
    lines = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField()),
        min_length=1
    )

class RequisitionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
