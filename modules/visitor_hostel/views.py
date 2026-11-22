from decimal import Decimal
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

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
from .serializers import (
    VisitorCategoryTariffSerializer,
    RoomSerializer,
    BookingRequestSerializer,
    MealBookingSerializer,
    BillSerializer,
    InventoryItemSerializer,
    InventoryReplenishmentSerializer,
)


class BookingListCreateView(generics.ListCreateAPIView):
    serializer_class = BookingRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return BookingRequest.objects.all().order_by('-created_at')
        return BookingRequest.objects.filter(indenter=user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(indenter=self.request.user, is_offline=False, status='pending')


class OfflineBookingCreateView(generics.CreateAPIView):
    serializer_class = BookingRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(indenter=None, is_offline=True, status='pending')


class BookingDetailView(generics.RetrieveUpdateAPIView):
    queryset = BookingRequest.objects.all()
    serializer_class = BookingRequestSerializer
    permission_classes = [permissions.IsAuthenticated]


class CaretakerRouteBookingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = BookingRequest.objects.get(pk=pk)
        except BookingRequest.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')  # 'forward' or 'reject'
        reason = request.data.get('reason', '')

        if action == 'forward':
            booking.status = 'forwarded'
            booking.save()
            return Response({'message': 'Booking forwarded to VH In-Charge'})
        elif action == 'reject':
            booking.status = 'rejected'
            booking.rejection_reason = reason
            booking.save()
            return Response({'message': 'Booking rejected by Caretaker'})

        return Response({'error': 'Invalid action. Choose forward or reject.'}, status=status.HTTP_400_BAD_REQUEST)


class InChargeApproveBookingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = BookingRequest.objects.get(pk=pk)
        except BookingRequest.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        decision = request.data.get('decision')  # 'approve' or 'reject'
        reason = request.data.get('reason', '')

        if decision == 'approve':
            booking.status = 'approved'
            booking.save()
            return Response({'message': 'Booking approved by VH In-Charge'})
        elif decision == 'reject':
            booking.status = 'rejected'
            booking.rejection_reason = reason
            booking.save()
            return Response({'message': 'Booking rejected by VH In-Charge'})

        return Response({'error': 'Invalid decision. Choose approve or reject.'}, status=status.HTTP_400_BAD_REQUEST)


class RoomAllotmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            booking = BookingRequest.objects.get(pk=pk)
        except BookingRequest.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        if booking.status != 'approved':
            return Response({'error': 'Rooms can only be allotted to approved bookings.'}, status=status.HTTP_400_BAD_REQUEST)

        room_ids = request.data.get('room_ids', [])
        for r_id in room_ids:
            room = Room.objects.get(id=r_id)
            RoomAllotment.objects.create(booking=booking, room=room)
            room.status = 'occupied'
            room.save()

        return Response({'message': f'Allocated {len(room_ids)} rooms to booking #{booking.id}'})


class CheckInView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        booking = BookingRequest.objects.get(pk=pk)
        booking.status = 'checked_in'
        booking.save()
        RoomAllotment.objects.filter(booking=booking).update(actual_check_in=timezone.now())
        return Response({'message': 'Check-in recorded.'})


class CheckOutAndBillView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        booking = BookingRequest.objects.get(pk=pk)
        booking.status = 'checked_out'
        booking.save()

        allotments = RoomAllotment.objects.filter(booking=booking)
        allotments.update(actual_check_out=timezone.now())
        for a in allotments:
            a.room.status = 'available'
            a.room.save()

        # Compute bill
        days = max(1, (booking.check_out_date - booking.check_in_date).days)
        tariff = VisitorCategoryTariff.objects.filter(
            category=booking.visitor_category,
            room_type=booking.room_type,
            occupancy=booking.occupancy
        ).first()

        rate = tariff.daily_rate if tariff else Decimal('500.00')
        room_charge = rate * days * booking.number_of_rooms

        meal_bookings = MealBooking.objects.filter(booking=booking)
        meal_charge = sum(m.rate * m.quantity for m in meal_bookings)

        total = room_charge + meal_charge

        bill, _ = Bill.objects.get_or_create(booking=booking)
        bill.room_charge = room_charge
        bill.meal_charge = meal_charge
        bill.total_amount = total
        bill.save()

        return Response({'message': 'Check-out completed and bill generated.', 'total': total})


class BookingCancellationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        booking = BookingRequest.objects.get(pk=pk)
        today = timezone.now().date()
        days_until_arrival = (booking.check_in_date - today).days

        tariff = VisitorCategoryTariff.objects.filter(
            category=booking.visitor_category,
            room_type=booking.room_type,
            occupancy=booking.occupancy
        ).first()
        one_day_rate = tariff.daily_rate if tariff else Decimal('500.00')

        if days_until_arrival >= 7:
            cancellation_charge = Decimal('0.00')
        elif 0 < days_until_arrival < 7:
            cancellation_charge = one_day_rate * Decimal('0.25')
        else:
            cancellation_charge = one_day_rate * Decimal('0.50')

        booking.status = 'cancelled'
        booking.save()

        bill, _ = Bill.objects.get_or_create(booking=booking)
        bill.cancellation_charge = cancellation_charge
        bill.total_amount = cancellation_charge
        bill.remarks = f'Cancelled with {days_until_arrival} days notice.'
        bill.save()

        return Response({
            'message': 'Booking cancelled successfully.',
            'cancellation_charge': cancellation_charge
        })


class InventoryListView(generics.ListCreateAPIView):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [permissions.IsAuthenticated]


class InventoryReplenishView(generics.ListCreateAPIView):
    queryset = InventoryReplenishment.objects.all()
    serializer_class = InventoryReplenishmentSerializer
    permission_classes = [permissions.IsAuthenticated]
