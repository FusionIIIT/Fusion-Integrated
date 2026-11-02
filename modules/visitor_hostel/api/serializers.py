from rest_framework import serializers
from modules.visitor_hostel.models import (
    VisitorDetail, RoomDetail, Tariff, BookingDetail, RoomAllotment,
    MealBooking, Bill, InventoryItem, InventoryReplenishment,
    VHRoleAssignment, StayException
)

class VisitorDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorDetail
        fields = '__all__'

class RoomDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomDetail
        fields = '__all__'

class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        fields = '__all__'

class RoomAllotmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomAllotment
        fields = '__all__'

class BookingDetailSerializer(serializers.ModelSerializer):
    visitor_details = VisitorDetailSerializer(read_only=True)
    allotments = RoomAllotmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = BookingDetail
        fields = '__all__'

class MealBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealBooking
        fields = '__all__'

class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = '__all__'

class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = '__all__'

class InventoryReplenishmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryReplenishment
        fields = '__all__'

class VHRoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VHRoleAssignment
        fields = '__all__'

class StayExceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StayException
        fields = '__all__'
