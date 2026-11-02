from rest_framework import serializers
from modules.iwd.models import (
    Request,
    WorkOrder,
    Vendor,
    Bill,
    BillItem,
    Budget,
    Proposal,
    ProposalItem,
    InventoryItem,
    InventoryTransaction,
    Feedback,
    SLAEscalation,
)

class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = "__all__"

class WorkOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkOrder
        fields = "__all__"

class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = "__all__"

class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = "__all__"

class BillItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillItem
        fields = "__all__"

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = "__all__"

class ProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposal
        fields = "__all__"

class ProposalItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalItem
        fields = "__all__"

class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = "__all__"

class InventoryTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryTransaction
        fields = "__all__"

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = "__all__"

class SLAEscalationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLAEscalation
        fields = "__all__"
