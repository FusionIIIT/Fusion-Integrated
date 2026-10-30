from django.urls import path
from modules.elm.api import views as v

urlpatterns = [
    # Employee self service
    path("my-leaves", v.MyLeavesView.as_view(), name="elm-my-leaves"),
    path("apply", v.ApplyLeaveView.as_view(), name="elm-apply"),
    path("applications/<int:pk>", v.ApplicationDetailView.as_view(), name="elm-detail"),
    path("applications/<int:pk>/withdraw", v.ApplicationWithdrawView.as_view(), name="elm-withdraw"),
    path("applications/<int:pk>/cancel", v.CancellationRequestView.as_view(), name="elm-cancel"),
    path("applications/<int:pk>/extend", v.ExtensionRequestView.as_view(), name="elm-extend"),
    path("applications/<int:pk>/resume", v.ResumptionSubmitView.as_view(), name="elm-resume"),
    path("applications/<int:pk>/export", v.PrintableApplicationView.as_view(), name="elm-export"),

    # Substitute
    path("substitutions", v.SubstituteRequestsView.as_view(), name="elm-substitutions"),
    path("applications/<int:pk>/substitute", v.SubstituteRespondView.as_view(), name="elm-substitute-respond"),

    # Approvals & Sanctions
    path("approvals/pending", v.PendingApprovalsView.as_view(), name="elm-pending-approvals"),
    path("applications/<int:pk>/recommend", v.UnitHeadRecommendView.as_view(), name="elm-recommend"),
    path("applications/<int:pk>/sanction", v.SanctionDecisionView.as_view(), name="elm-sanction"),
    path("applications/<int:pk>/cancellation-decision", v.CancellationDecisionView.as_view(), name="elm-cancellation-decision"),
    path("applications/<int:pk>/resumption-review", v.ResumptionReviewView.as_view(), name="elm-resumption-review"),

    # Calendars
    path("calendars/holidays", v.HolidayCalendarView.as_view(), name="elm-holidays"),

    # Admin
    path("admin/offline-record", v.OfflineLeaveRecordView.as_view(), name="elm-admin-offline-record"),
]
