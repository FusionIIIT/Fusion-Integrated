from rest_framework import serializers
from .models import IwdRequest, RequestTransition, Proposal, WorkOrder, Vendor, Bill, InventoryItem, Feedback

class IwdRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = IwdRequest
        fields = "__all__"

class RequestTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestTransition
        fields = "__all__"

class ProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposal
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

class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = "__all__"

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = "__all__"
