"""URL routes for Visitor Hostel Management API."""
from django.urls import path
from . import views

urlpatterns = [
    path("bookings/", views.BookingListCreateView.as_view(), name="vh-booking-list-create"),
    path("bookings/mine/", views.MyBookingsView.as_view(), name="vh-my-bookings"),
    path("bookings/<int:pk>/", views.BookingDetailView.as_view(), name="vh-booking-detail"),
    path("bookings/<int:pk>/review/", views.BookingReviewView.as_view(), name="vh-booking-review"),
    path("bookings/<int:pk>/decision/", views.BookingDecisionView.as_view(), name="vh-booking-decision"),
    path("bookings/<int:pk>/cancel/", views.BookingCancelView.as_view(), name="vh-booking-cancel"),
    path("bookings/<int:pk>/allot/", views.BookingAllotView.as_view(), name="vh-booking-allot"),
    path("bookings/<int:pk>/checkin/", views.BookingCheckInView.as_view(), name="vh-booking-checkin"),
    path("bookings/<int:pk>/checkout/", views.BookingCheckOutView.as_view(), name="vh-booking-checkout"),
    path("bookings/<int:pk>/meals/", views.MealBookingView.as_view(), name="vh-meal-booking"),
    path("bills/<int:pk>/settle/", views.BillSettleView.as_view(), name="vh-bill-settle"),
    path("inventory/", views.InventoryView.as_view(), name="vh-inventory-list"),
    path("inventory/<int:pk>/replenish/", views.InventoryReplenishView.as_view(), name="vh-inventory-replenish"),
    path("inventory/<int:pk>/approve/", views.InventoryApproveView.as_view(), name="vh-inventory-approve"),
    path("roles/reassign/", views.RoleReassignView.as_view(), name="vh-role-reassign"),
    path("tariffs/", views.TariffListView.as_view(), name="vh-tariffs"),
    path("rooms/", views.RoomListView.as_view(), name="vh-rooms"),
    path("notifications/", views.NotificationListView.as_view(), name="vh-notifications"),
    path("reports/caretaker/", views.CaretakerReportsView.as_view(), name="vh-caretaker-reports"),
    path("reports/incharge/", views.InchargeReportsView.as_view(), name="vh-incharge-reports"),
]
