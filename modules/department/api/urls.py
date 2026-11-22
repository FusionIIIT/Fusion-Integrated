from django.urls import path

from modules.department.api import views as v

urlpatterns = [
    path("departments", v.DepartmentListView.as_view(), name="department-departments"),
    path("departments/<str:code>", v.DepartmentDetailView.as_view(), name="department-detail"),
    path(
        "official-changes", v.OfficialChangeListView.as_view(), name="department-official-changes"
    ),
    path(
        "official-changes/<int:pk>/decide",
        v.OfficialChangeDecideView.as_view(),
        name="department-official-change-decide",
    ),
    path("announcements", v.AnnouncementListView.as_view(), name="department-announcements"),
    path(
        "announcements/<int:pk>", v.AnnouncementDetailView.as_view(), name="department-announcement"
    ),
    path(
        "announcements/<int:pk>/hide",
        v.AnnouncementHideView.as_view(),
        name="department-announcement-hide",
    ),
    path("inventory-items", v.InventoryItemListView.as_view(), name="department-inventory-items"),
    path(
        "inventory-items/<int:pk>/receipts",
        v.InventoryReceiptView.as_view(),
        name="department-receipts",
    ),
    path("stock-movements", v.StockMovementListView.as_view(), name="department-stock-movements"),
    path("stock-requests", v.StockRequestListView.as_view(), name="department-stock-requests"),
    path(
        "stock-requests/<int:pk>/decide",
        v.StockRequestDecideView.as_view(),
        name="department-stock-decide",
    ),
    path(
        "stock-requests/<int:pk>/issue",
        v.StockRequestIssueView.as_view(),
        name="department-stock-issue",
    ),
    path("feedback", v.FeedbackListView.as_view(), name="department-feedback"),
    path("feedback/<int:pk>", v.FeedbackDetailView.as_view(), name="department-feedback-detail"),
    path(
        "feedback/<int:pk>/review",
        v.FeedbackReviewView.as_view(),
        name="department-feedback-review",
    ),
    path(
        "feedback/<int:pk>/dispose",
        v.FeedbackDisposeView.as_view(),
        name="department-feedback-dispose",
    ),
    path("feedback/<int:pk>/notes", v.FeedbackNoteView.as_view(), name="department-feedback-notes"),
    path("timetable-slots", v.TimetableListView.as_view(), name="department-timetable"),
    path(
        "timetable-slots/<int:pk>",
        v.TimetableDetailView.as_view(),
        name="department-timetable-slot",
    ),
    path("lab-resources", v.LabListView.as_view(), name="department-labs"),
    path("lab-resources/<int:pk>", v.LabDetailView.as_view(), name="department-lab"),
    path("profiles", v.ProfileListView.as_view(), name="department-profiles"),
    path("profiles/<int:pk>", v.ProfileDetailView.as_view(), name="department-profile"),
    path("role-assignments", v.RoleTenureListView.as_view(), name="department-role-assignments"),
    path(
        "role-assignments/<int:pk>",
        v.RoleTenureDetailView.as_view(),
        name="department-role-assignment",
    ),
]
