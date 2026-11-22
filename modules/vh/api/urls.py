# URL routing for VHMS REST API endpoints.
from django.urls import path

from modules.vh.api import views

app_name = "vh"

urlpatterns = [
    path("bookings/", views.BookingListCreateView.as_view(), name="booking-list-create"),
    path(
        "bookings/offline/", views.OfflineBookingCreateView.as_view(), name="booking-offline-create"
    ),
    path("bookings/<int:booking_id>/", views.BookingDetailView.as_view(), name="booking-detail"),
    path(
        "bookings/<int:booking_id>/route/", views.BookingRouteView.as_view(), name="booking-route"
    ),
    path(
        "bookings/<int:booking_id>/decide/",
        views.BookingDecideView.as_view(),
        name="booking-decide",
    ),
    path(
        "bookings/<int:booking_id>/cancel/",
        views.BookingCancelView.as_view(),
        name="booking-cancel",
    ),
    path(
        "bookings/<int:booking_id>/confirm-cancellation/",
        views.BookingConfirmCancellationView.as_view(),
        name="booking-confirm-cancellation",
    ),
    path(
        "bookings/<int:booking_id>/modify/",
        views.BookingModifyView.as_view(),
        name="booking-modify",
    ),
    path(
        "bookings/<int:booking_id>/allot-rooms/",
        views.RoomAllotmentView.as_view(),
        name="booking-allot-rooms",
    ),
    path("bookings/<int:booking_id>/checkin/", views.CheckInView.as_view(), name="booking-checkin"),
    path(
        "bookings/<int:booking_id>/checkout/", views.CheckOutView.as_view(), name="booking-checkout"
    ),
    path(
        "bookings/<int:booking_id>/meals/",
        views.BookingMealsListCreateView.as_view(),
        name="booking-meals",
    ),
    path(
        "bookings/<int:booking_id>/bill/",
        views.BillDetailGenerateView.as_view(),
        name="booking-bill",
    ),
    path("rooms/availability/", views.RoomAvailabilityView.as_view(), name="room-availability"),
    path("bills/<int:bill_id>/settle/", views.BillSettlementView.as_view(), name="bill-settle"),
    path("inventory/", views.InventoryListCreateView.as_view(), name="inventory-list-create"),
    path(
        "inventory/<int:item_id>/replenish/",
        views.InventoryReplenishRequestView.as_view(),
        name="inventory-replenish-request",
    ),
    path(
        "inventory/replenishments/<int:replenishment_id>/approve/",
        views.InventoryReplenishApproveView.as_view(),
        name="inventory-replenish-approve",
    ),
    path("tariffs/", views.TariffListCreateView.as_view(), name="tariff-list-create"),
    path("reports/caretaker/", views.CaretakerReportsView.as_view(), name="caretaker-reports"),
    path("reports/incharge/", views.InchargeReportsView.as_view(), name="incharge-reports"),
    path("roles/reassign/", views.RoleReassignmentView.as_view(), name="role-reassign"),
]
