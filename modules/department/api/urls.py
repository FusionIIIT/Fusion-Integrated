from django.urls import path

from modules.department.api import views

urlpatterns = [
    path("announcements", views.AnnouncementListView.as_view(),
         name="department-announcements"),
    path("announcements/<int:pk>/<str:action>",
         views.AnnouncementActionView.as_view(), name="department-announcement-action"),
    path("inventory", views.InventoryView.as_view(), name="department-inventory"),
    path("stock-requests", views.StockRequestView.as_view(),
         name="department-stock-requests"),
    path("stock-requests/<int:pk>/<str:action>",
         views.StockRequestActionView.as_view(), name="department-stock-request-action"),
    path("feedback", views.FeedbackView.as_view(), name="department-feedback"),
    path("feedback/<int:pk>/review", views.FeedbackReviewView.as_view(),
         name="department-feedback-review"),
    path("resources", views.ResourceView.as_view(), name="department-resources"),
    path("resources/<int:pk>", views.ResourceDetailView.as_view(),
         name="department-resource"),
    path("timetables", views.TimetableView.as_view(), name="department-timetables"),
    path("timetables/<int:pk>", views.TimetableDetailView.as_view(),
         name="department-timetable"),
    path("details", views.DepartmentDetailsView.as_view(), name="department-details"),
    path("details/changes/<int:pk>/<str:action>",
         views.DepartmentChangeActionView.as_view(), name="department-change-action"),
]
