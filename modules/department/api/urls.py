from django.urls import path

from modules.department.api import announcements_views as an
from modules.department.api import feedback_views as fb
from modules.department.api import inventory_stock_views as st
from modules.department.api import profiles_views as pr
from modules.department.api import role_assignments_views as ra
from modules.department.api import timetable_views as tt
from modules.department.api import views as v

urlpatterns = [
    path("departments", v.DepartmentListView.as_view(), name="department-departments"),
    path("assignments", ra.RoleAssignmentListView.as_view(), name="department-assignments"),
    path("announcements", an.AnnouncementListView.as_view(), name="department-announcements"),
    path("announcements/<int:pk>", an.AnnouncementDetailView.as_view(), name="department-announcements-detail"),
    path("announcements/<int:pk>/hide", an.AnnouncementHideView.as_view(), name="department-announcements-hide"),
    path("inventory", st.InventoryListView.as_view(), name="department-inventory"),
    path("stock-requests", st.StockRequestListView.as_view(), name="department-stock-requests"),
    path("stock-requests/<int:pk>/decide", st.StockRequestDecideView.as_view(), name="department-stock-requests-decide"),
    path("stock-requests/<int:pk>/issue", st.StockRequestIssueView.as_view(), name="department-stock-requests-issue"),
    path("stock-history", st.StockHistoryView.as_view(), name="department-stock-history"),
    path("stock-movements", st.StockMovementListView.as_view(), name="department-stock-movements"),
    path("feedback", fb.FeedbackListView.as_view(), name="department-feedback"),
    path("feedback/<int:pk>/review", fb.FeedbackReviewView.as_view(), name="department-feedback-review"),
    path("feedback/<int:pk>/dispose", fb.FeedbackDisposeView.as_view(), name="department-feedback-dispose"),
    path("timetable", tt.TimetableListView.as_view(), name="department-timetable"),
    path("timetable/<int:pk>", tt.TimetableDetailView.as_view(), name="department-timetable-detail"),
    path("labs", tt.LabListView.as_view(), name="department-labs"),
    path("labs/<int:pk>", tt.LabDetailView.as_view(), name="department-labs-detail"),
    path("programs", tt.ProgramListView.as_view(), name="department-programs"),
    path("programs/<int:pk>", tt.ProgramDetailView.as_view(), name="department-programs-detail"),
    path("profiles", pr.ProfileListView.as_view(), name="department-profiles"),
    path("profiles/<int:pk>", pr.ProfileDetailView.as_view(), name="department-profiles-detail"),
    path("profiles/<int:pk>/deactivate", pr.ProfileDeactivateView.as_view(), name="department-profiles-deactivate"),
    path("rosters", pr.RosterListView.as_view(), name="department-rosters"),
    path("departments/<int:pk>", pr.DepartmentDetailsView.as_view(), name="department-departments-detail"),
    path("official-changes", pr.OfficialChangeListView.as_view(), name="department-official-changes"),
    path("official-changes/<int:pk>/decide", pr.OfficialChangeDecideView.as_view(), name="department-official-changes-decide"),
]
