from django.urls import path

from modules.visitors_hostel.api import views

urlpatterns = [
    path("bookings", views.BookingListCreateView.as_view(), name="vh-bookings"),
    path("bookings/offline", views.OfflineBookingView.as_view(), name="vh-booking-offline"),
    path("bookings/<int:pk>/<str:action>", views.BookingActionView.as_view(),
         name="vh-booking-action"),
    path("rooms", views.RoomListView.as_view(), name="vh-rooms"),
    path("rooms/availability", views.RoomAvailabilityView.as_view(),
         name="vh-room-availability"),
    path("tariffs", views.TariffListCreateView.as_view(), name="vh-tariffs"),
    path("bills", views.BillView.as_view(), name="vh-bills"),
    path("meals", views.MealBookingView.as_view(), name="vh-meals"),
    path("bills/<int:bill_id>/settlements", views.CashSettlementView.as_view(),
         name="vh-cash-settlement"),
    path("inventory", views.InventoryView.as_view(), name="vh-inventory"),
    path("inventory/<int:item_id>/changes", views.InventoryChangeView.as_view(),
         name="vh-inventory-change"),
    path("replenishments", views.ReplenishmentView.as_view(), name="vh-replenishments"),
    path("replenishments/<int:pk>/review", views.ReplenishmentReviewView.as_view(),
         name="vh-replenishment-review"),
    path("reports", views.ReportView.as_view(), name="vh-reports"),
    path("notifications", views.NotificationListView.as_view(), name="vh-notifications"),
    path("roles", views.OperationalRoleView.as_view(), name="vh-role-assignments"),
]
