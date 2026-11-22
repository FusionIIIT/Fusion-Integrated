from django.urls import path

from modules.department.api import administration as d
from modules.department.api import announcements as a
from modules.department.api import operations as o
from modules.department.api.common import DepartmentAccessView

urlpatterns = [
    path("access", DepartmentAccessView.as_view(), name="department-access"),
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
    path("labs", d.LabResourcesView.as_view(), name="department-labs"),
    path("timetable", d.TimetableView.as_view(), name="department-timetable"),
    path("timetable/<int:pk>", d.TimetableSlotView.as_view(), name="department-timetable-slot"),
    path("academic-context", d.AcademicContextView.as_view(), name="department-academic-context"),
    path("details", d.DepartmentDetailsView.as_view(), name="department-details"),
    path("proposals", d.DepartmentProposalView.as_view(), name="department-proposals"),
    path("proposals/<int:pk>/action", d.ProposalDecisionView.as_view(),
         name="department-proposal-action"),
]
