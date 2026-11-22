from django.urls import path

from modules.department.api import announcements as a
from modules.department.api import operations as o

urlpatterns = [
    path("announcements", a.AnnouncementListView.as_view(), name="department-announcements"),
    path("announcements/managed", a.ManagedAnnouncementsView.as_view(),
         name="department-managed-announcements"),
    path("announcements/<int:pk>/action", a.AnnouncementMaintenanceView.as_view(),
         name="department-announcement-action"),
    path("inventory", o.InventoryView.as_view(), name="department-inventory"),
    path("stock-requests", o.StockRequestsView.as_view(), name="department-stock-requests"),
    path("stock-requests/<int:pk>/action", o.StockRequestActionView.as_view(),
         name="department-stock-action"),
    path("feedback", o.FeedbackView.as_view(), name="department-feedback"),
    path("feedback/<int:pk>/action", o.FeedbackActionView.as_view(),
         name="department-feedback-action"),
    path("notices", o.NoticesView.as_view(), name="department-notices"),
]
