from django.urls import path

from modules.dept.api import views as v

urlpatterns = [
    path("announcements", v.AnnouncementListView.as_view(),
         name="dept-announcements"),
    path("announcements/<int:pk>", v.AnnouncementDetailView.as_view(),
         name="dept-announcement"),
    path("announcements/<int:pk>/status", v.AnnouncementStatusView.as_view(),
         name="dept-announcement-status"),

    path("inventory", v.InventoryListView.as_view(), name="dept-inventory"),
    path("stock-requests", v.StockRequestListView.as_view(),
         name="dept-stock-requests"),
    path("stock-requests/issued", v.IssuedHistoryView.as_view(),
         name="dept-stock-issued"),
    path("stock-requests/<int:pk>/decision", v.StockRequestDecisionView.as_view(),
         name="dept-stock-decision"),
    path("stock-requests/<int:pk>/issue", v.StockRequestIssueView.as_view(),
         name="dept-stock-issue"),
    path("stock-log", v.StockLogView.as_view(), name="dept-stock-log"),

    path("feedback", v.FeedbackListView.as_view(), name="dept-feedback"),
    path("feedback/<int:pk>/transition", v.FeedbackMoveView.as_view(),
         name="dept-feedback-transition"),
]
