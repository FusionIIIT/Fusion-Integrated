"""URL routing for Department API."""

from django.urls import path

from modules.dept.api import views

urlpatterns = [
    # Announcements
    path("announcements/", views.AnnouncementListCreateView.as_view(), name="announcement-list"),
    path(
        "announcements/<uuid:pk>/",
        views.AnnouncementDetailView.as_view(),
        name="announcement-detail",
    ),
    # Inventory & Stock
    path("inventory/", views.InventoryItemListCreateView.as_view(), name="inventory-list"),
    path(
        "inventory/<uuid:pk>/add-stock/",
        views.InventoryItemAddStockView.as_view(),
        name="inventory-add-stock",
    ),
    path(
        "inventory/<uuid:pk>/transactions/",
        views.InventoryItemTransactionsView.as_view(),
        name="inventory-transactions",
    ),
    path("stock-requests/", views.StockRequestListCreateView.as_view(), name="stock-request-list"),
    path(
        "stock-requests/<uuid:pk>/decision/",
        views.StockRequestDecisionView.as_view(),
        name="stock-request-decision",
    ),
    path(
        "stock-requests/<uuid:pk>/issue/",
        views.StockRequestIssueView.as_view(),
        name="stock-request-issue",
    ),
    # Feedback
    path("feedback/", views.FeedbackListCreateView.as_view(), name="feedback-list"),
    path("feedback/<uuid:pk>/review/", views.FeedbackReviewView.as_view(), name="feedback-review"),
    path(
        "feedback/<uuid:pk>/resolve/",
        views.FeedbackResolveView.as_view(),
        name="feedback-resolve",
    ),
    # Timetables
    path("timetables/", views.TimetableListCreateView.as_view(), name="timetable-list"),
    path("timetables/<uuid:pk>/", views.TimetableDetailView.as_view(), name="timetable-detail"),
    # Labs
    path("labs/", views.LabResourceListCreateView.as_view(), name="lab-list"),
    path("labs/<uuid:pk>/", views.LabResourceDetailView.as_view(), name="lab-detail"),
    # Profiles
    path("profiles/", views.ProfileListCreateView.as_view(), name="profile-list"),
    # Details & Official changes
    path("details/", views.DepartmentDetailView.as_view(), name="department-detail"),
    path(
        "details/propose-change/",
        views.OfficialChangeProposeView.as_view(),
        name="propose-change",
    ),
    path(
        "details/pending-changes/",
        views.OfficialChangePendingListView.as_view(),
        name="pending-changes",
    ),
    path(
        "details/pending-changes/<uuid:pk>/decision/",
        views.OfficialChangeDecisionView.as_view(),
        name="change-decision",
    ),
    # Roles
    path("roles/", views.RoleAssignmentListCreateView.as_view(), name="role-assignment-list"),
    path(
        "roles/<uuid:pk>/revoke/",
        views.RoleAssignmentRevokeView.as_view(),
        name="role-assignment-revoke",
    ),
]
