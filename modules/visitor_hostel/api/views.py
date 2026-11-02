from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from modules.visitor_hostel.models import (
    VisitorDetail, RoomDetail, Tariff, BookingDetail, RoomAllotment,
    MealBooking, Bill, InventoryItem, InventoryReplenishment
)
from modules.visitor_hostel.api.serializers import (
    VisitorDetailSerializer, RoomDetailSerializer, TariffSerializer,
    BookingDetailSerializer, RoomAllotmentSerializer, MealBookingSerializer,
    BillSerializer, InventoryItemSerializer, InventoryReplenishmentSerializer
)
from modules.visitor_hostel import services

class VisitorViewSet(viewsets.ModelViewSet):
    queryset = VisitorDetail.objects.all()
    serializer_class = VisitorDetailSerializer

class RoomViewSet(viewsets.ModelViewSet):
    queryset = RoomDetail.objects.all()
    serializer_class = RoomDetailSerializer

    @action(detail=False, methods=['get'])
    def available(self, request):
        rooms = RoomDetail.objects.filter(status='Available', is_operational=True)
        return Response(RoomDetailSerializer(rooms, many=True).data)

class TariffViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tariff.objects.all()
    serializer_class = TariffSerializer

class BookingViewSet(viewsets.ModelViewSet):
    queryset = BookingDetail.objects.all()
    serializer_class = BookingDetailSerializer

    @action(detail=True, methods=['post'])
    def forward(self, request, pk=None):
        actor = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'caretaker'
        booking = services.caretaker_forward_booking(pk, actor)
        return Response(BookingDetailSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        actor = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'incharge'
        booking = services.incharge_approve_booking(pk, actor)
        return Response(BookingDetailSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        actor = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'caretaker'
        reason = request.data.get('reason', '')
        booking = services.caretaker_reject_booking(pk, actor, reason)
        return Response(BookingDetailSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        actor = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'indenter'
        reason = request.data.get('reason', '')
        booking = services.request_cancellation(pk, actor, reason)
        return Response(BookingDetailSerializer(booking).data)

class StayViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def allot(self, request):
        actor = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'caretaker'
        allotment = services.allot_room(request.data['booking_id'], request.data['room_number'], actor)
        return Response(RoomAllotmentSerializer(allotment).data)

    @action(detail=False, methods=['post'])
    def check_in(self, request):
        actor = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'caretaker'
        allotment = services.check_in_guest(request.data['booking_id'], actor)
        return Response(RoomAllotmentSerializer(allotment).data)

    @action(detail=False, methods=['post'])
    def check_out(self, request):
        actor = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'caretaker'
        allotment = services.check_out_guest(request.data['booking_id'], actor)
        return Response(RoomAllotmentSerializer(allotment).data)

class MealViewSet(viewsets.ModelViewSet):
    queryset = MealBooking.objects.all()
    serializer_class = MealBookingSerializer

class BillingViewSet(viewsets.ModelViewSet):
    queryset = Bill.objects.all()
    serializer_class = BillSerializer

    @action(detail=True, methods=['post'])
    def settle(self, request, pk=None):
        actor = request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'caretaker'
        amount = request.data.get('amount')
        bill = services.settle_cash_bill(pk, actor, amount)
        return Response(BillSerializer(bill).data)

class InventoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        items = services.check_low_stock_items()
        return Response(InventoryItemSerializer(items, many=True).data)
