"""Mounted at /api/v1/visitorhostel/ by config/urls.py."""
from django.urls import path

from modules.visitor_hostel.api import views as v

urlpatterns = [
    # bookings
    path("bookings", v.BookingListView.as_view(), name="vh-bookings"),
    path("bookings/offline", v.OfflineBookingView.as_view(), name="vh-booking-offline"),
    path("bookings/<int:pk>", v.BookingDetailView.as_view(), name="vh-booking"),
    path("bookings/<int:pk>/review", v.BookingReviewView.as_view(), name="vh-booking-review"),
    path("bookings/<int:pk>/decision", v.BookingDecisionView.as_view(),
         name="vh-booking-decision"),
    path("bookings/<int:pk>/availability", v.BookingAvailabilityView.as_view(),
         name="vh-booking-availability"),
    path("bookings/<int:pk>/allot", v.BookingAllotView.as_view(), name="vh-booking-allot"),
    path("bookings/<int:pk>/check-in", v.BookingCheckInView.as_view(),
         name="vh-booking-check-in"),
    path("bookings/<int:pk>/check-out", v.BookingCheckOutView.as_view(),
         name="vh-booking-check-out"),
    path("bookings/<int:pk>/cancellation", v.CancellationRequestView.as_view(),
         name="vh-booking-cancellation"),
    path("bookings/<int:pk>/cancellation/confirm", v.CancellationConfirmView.as_view(),
         name="vh-booking-cancellation-confirm"),
    path("bookings/<int:pk>/modifications", v.ModificationRequestView.as_view(),
         name="vh-booking-modifications"),
    path("bookings/<int:pk>/meals", v.BookingMealsView.as_view(), name="vh-booking-meals"),
    path("bookings/<int:pk>/bill", v.BookingBillView.as_view(), name="vh-booking-bill"),

    path("modifications", v.ModificationListView.as_view(), name="vh-modifications"),
    path("modifications/<int:pk>/confirm", v.ModificationConfirmView.as_view(),
         name="vh-modification-confirm"),

    # bills
    path("bills", v.BillListView.as_view(), name="vh-bills"),
    path("bills/<int:pk>/settle", v.BillSettleView.as_view(), name="vh-bill-settle"),
    path("bills/<int:pk>/verify", v.BillVerifyView.as_view(), name="vh-bill-verify"),

    # rooms, tariffs, duty
    path("rooms", v.RoomListView.as_view(), name="vh-rooms"),
    path("rooms/<int:pk>/active", v.RoomActiveView.as_view(), name="vh-room-active"),
    path("tariffs", v.TariffListView.as_view(), name="vh-tariffs"),
    path("duty", v.DutyView.as_view(), name="vh-duty"),

    # inventory
    path("inventory", v.InventoryListView.as_view(), name="vh-inventory"),
    path("inventory/<int:pk>/adjust", v.InventoryAdjustView.as_view(),
         name="vh-inventory-adjust"),
    path("inventory/<int:pk>/threshold", v.InventoryThresholdView.as_view(),
         name="vh-inventory-threshold"),
    path("replenishments", v.ReplenishmentListView.as_view(), name="vh-replenishments"),
    path("replenishments/<int:pk>/approve", v.ReplenishmentApproveView.as_view(),
         name="vh-replenishment-approve"),

    # alerts and reports
    path("alerts", v.StayAlertListView.as_view(), name="vh-alerts"),
    path("reports/incharge/<str:kind>", v.InChargeReportView.as_view(),
         name="vh-report-incharge"),
    path("reports/operations/<str:kind>", v.OperationsReportView.as_view(),
         name="vh-report-operations"),
]
