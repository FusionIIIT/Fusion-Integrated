from rest_framework import serializers
from modules.phc.models import InventoryItem, Requisition, RequisitionLine

class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = [
            "id", "name", "unit", "quantity", "reorder_threshold"
        ]
        read_only_fields = ["id"]

class RequisitionLineSerializer(serializers.Serializer):
    inventory_item = serializers.PrimaryKeyRelatedField(queryset=InventoryItem.objects.all())
    quantity = serializers.IntegerField(min_value=1)

class RequisitionSerializer(serializers.ModelSerializer):
    lines = RequisitionLineSerializer(many=True, required=False)
    
    class Meta:
        model = Requisition
        fields = [
            "id", "requested_by_user_id", "status", "created_at", "decided_by_user_id", "decided_at", "lines"
        ]
        read_only_fields = ["id", "created_at"]

class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=[RequisitionState.APPROVED.value, RequisitionState.REJECTED.value])
