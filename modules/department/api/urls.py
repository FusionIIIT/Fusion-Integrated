from django.urls import path, register_converter

from modules.department.api import views as v


class RowId:
    """A row id that fits the column; a longer one is a 404, not a database error."""

    regex = "[0-9]{1,9}"

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return str(value)


register_converter(RowId, "rowid")

urlpatterns = [
    path("context", v.ActingContextView.as_view(), name="department-context"),
    path("departments", v.DepartmentListView.as_view(), name="department-departments"),
    path("departments/<str:code>", v.DepartmentDetailView.as_view(), name="department-detail"),
    path(
        "official-changes", v.OfficialChangeListView.as_view(), name="department-official-changes"
    ),
    path(
        "official-changes/<rowid:pk>/decide",
        v.OfficialChangeDecideView.as_view(),
        name="department-official-change-decide",
    ),
    path("announcements", v.AnnouncementListView.as_view(), name="department-announcements"),
    path(
        "announcements/<rowid:pk>",
        v.AnnouncementDetailView.as_view(),
        name="department-announcement",
    ),
    path(
        "announcements/<rowid:pk>/hide",
        v.AnnouncementHideView.as_view(),
        name="department-announcement-hide",
    ),
    path("inventory-items", v.InventoryItemListView.as_view(), name="department-inventory-items"),
    path(
        "inventory-items/<rowid:pk>/receipts",
        v.InventoryReceiptView.as_view(),
        name="department-receipts",
    ),
    path("stock-movements", v.StockMovementListView.as_view(), name="department-stock-movements"),
    path("stock-requests", v.StockRequestListView.as_view(), name="department-stock-requests"),
    path(
        "stock-requests/<rowid:pk>/decide",
        v.StockRequestDecideView.as_view(),
        name="department-stock-decide",
    ),
    path(
        "stock-requests/<rowid:pk>/issue",
        v.StockRequestIssueView.as_view(),
        name="department-stock-issue",
    ),
    path("feedback", v.FeedbackListView.as_view(), name="department-feedback"),
    path("feedback/<rowid:pk>", v.FeedbackDetailView.as_view(), name="department-feedback-detail"),
    path(
        "feedback/<rowid:pk>/review",
        v.FeedbackReviewView.as_view(),
        name="department-feedback-review",
    ),
    path(
        "feedback/<rowid:pk>/dispose",
        v.FeedbackDisposeView.as_view(),
        name="department-feedback-dispose",
    ),
    path(
        "feedback/<rowid:pk>/notes", v.FeedbackNoteView.as_view(), name="department-feedback-notes"
    ),
    path("timetable-slots", v.TimetableListView.as_view(), name="department-timetable"),
    path(
        "timetable-slots/<rowid:pk>",
        v.TimetableDetailView.as_view(),
        name="department-timetable-slot",
    ),
    path("lab-resources", v.LabListView.as_view(), name="department-labs"),
    path("lab-resources/<rowid:pk>", v.LabDetailView.as_view(), name="department-lab"),
    path("profiles", v.ProfileListView.as_view(), name="department-profiles"),
    path("profiles/<rowid:pk>", v.ProfileDetailView.as_view(), name="department-profile"),
    path("role-assignments", v.RoleTenureListView.as_view(), name="department-role-assignments"),
    path(
        "role-assignments/vacancies", v.RoleVacancyView.as_view(), name="department-role-vacancies"
    ),
    path(
        "role-assignments/<rowid:pk>",
        v.RoleTenureDetailView.as_view(),
        name="department-role-assignment",
    ),
]
