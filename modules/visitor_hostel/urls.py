from django.urls import path
from .views import (
    BookingListCreateView,
    OfflineBookingCreateView,
    BookingDetailView,
    CaretakerRouteBookingView,
    InChargeApproveBookingView,
    RoomAllotmentView,
    CheckInView,
    CheckOutAndBillView,
    BookingCancellationView,
    InventoryListView,
    InventoryReplenishView,
)

urlpatterns = [
    path('bookings/', BookingListCreateView.as_view(), name='vh-booking-list-create'),
    path('bookings/offline/', OfflineBookingCreateView.as_view(), name='vh-booking-offline'),
    path('bookings/<int:pk>/', BookingDetailView.as_view(), name='vh-booking-detail'),
    path('bookings/<int:pk>/route/', CaretakerRouteBookingView.as_view(), name='vh-booking-route'),
    path('bookings/<int:pk>/decision/', InChargeApproveBookingView.as_view(), name='vh-booking-decision'),
    path('bookings/<int:pk>/allot/', RoomAllotmentView.as_view(), name='vh-room-allotment'),
    path('bookings/<int:pk>/check-in/', CheckInView.as_view(), name='vh-check-in'),
    path('bookings/<int:pk>/check-out/', CheckOutAndBillView.as_view(), name='vh-check-out'),
    path('bookings/<int:pk>/cancel/', BookingCancellationView.as_view(), name='vh-booking-cancel'),
    path('inventory/', InventoryListView.as_view(), name='vh-inventory-list'),
    path('inventory/replenish/', InventoryReplenishView.as_view(), name='vh-inventory-replenish'),
]
