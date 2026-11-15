from rest_framework import serializers
from .models import (
    VisitorCategoryTariff,
    Room,
    BookingRequest,
    RoomAllotment,
    MealBooking,
    Bill,
    InventoryItem,
    InventoryReplenishment,
)


class VisitorCategoryTariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorCategoryTariff
        fields = '__all__'


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'


class MealBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealBooking
        fields = '__all__'


class RoomAllotmentSerializer(serializers.ModelSerializer):
    room_details = RoomSerializer(source='room', read_only=True)

    class Meta:
        model = RoomAllotment
        fields = '__all__'


class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = '__all__'


class BookingRequestSerializer(serializers.ModelSerializer):
    allotments = RoomAllotmentSerializer(many=True, read_only=True)
    meal_bookings = MealBookingSerializer(many=True, read_only=True)
    bill = BillSerializer(read_only=True)

    class Meta:
        model = BookingRequest
        fields = '__all__'


class InventoryItemSerializer(serializers.ModelSerializer):
    below_threshold = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = '__all__'

    def get_below_threshold(self, obj):
        return obj.is_below_threshold()


class InventoryReplenishmentSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = InventoryReplenishment
        fields = '__all__'
