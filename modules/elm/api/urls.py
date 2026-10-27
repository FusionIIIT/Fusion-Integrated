"""URL routes for ELM module."""
from django.urls import path
from modules.elm.api.views import (
    LeaveBalanceView,
    LeaveRequestViewSet,
    SubstituteQueueView,
    ApprovalQueueView,
    ExtensionQueueView,
    ResumptionQueueView,
    ProcessSLAView,
    AdminLeaveView,
    YearEndRolloverView,
    HolidayCalendarView,
    AcademicVacationView,
)

leave_list = LeaveRequestViewSet.as_view({"get": "list", "post": "create"})
leave_detail = LeaveRequestViewSet.as_view({"get": "retrieve"})
leave_withdraw = LeaveRequestViewSet.as_view({"post": "withdraw"})
leave_request_cancellation = LeaveRequestViewSet.as_view({"post": "request_cancellation"})
leave_decide_cancellation = LeaveRequestViewSet.as_view({"post": "decide_cancellation"})
leave_extend = LeaveRequestViewSet.as_view({"post": "extend"})
leave_resume = LeaveRequestViewSet.as_view({"post": "resume"})

urlpatterns = [
    path("balances/mine/", LeaveBalanceView.as_view(), name="elm-balances-mine"),
    path("leaves/", leave_list, name="elm-leaves-list"),
    path("leaves/<int:pk>/", leave_detail, name="elm-leaves-detail"),
    path("leaves/<int:pk>/withdraw/", leave_withdraw, name="elm-leaves-withdraw"),
    path(
        "leaves/<int:pk>/request-cancellation/",
        leave_request_cancellation,
        name="elm-leaves-req-cancellation",
    ),
    path(
        "leaves/<int:pk>/decide-cancellation/",
        leave_decide_cancellation,
        name="elm-leaves-decide-cancellation",
    ),
    path("leaves/<int:pk>/extend/", leave_extend, name="elm-leaves-extend"),
    path("leaves/<int:pk>/resume/", leave_resume, name="elm-leaves-resume"),
    path("substitute/queue/", SubstituteQueueView.as_view(), name="elm-substitute-queue"),
    path(
        "substitute/<int:pk>/respond/",
        SubstituteQueueView.as_view(),
        name="elm-substitute-respond",
    ),
    path("approvals/queue/", ApprovalQueueView.as_view(), name="elm-approvals-queue"),
    path("approvals/<int:pk>/", ApprovalQueueView.as_view(), name="elm-approvals-action"),
    path("extensions/queue/", ExtensionQueueView.as_view(), name="elm-extensions-queue"),
    path("extensions/<int:pk>/review/", ExtensionQueueView.as_view(), name="elm-extensions-review"),
    path("resumptions/queue/", ResumptionQueueView.as_view(), name="elm-resumptions-queue"),
    path("resumptions/<int:pk>/review/", ResumptionQueueView.as_view(), name="elm-resumptions-review"),
    path("admin/process-sla/", ProcessSLAView.as_view(), name="elm-admin-process-sla"),
    path("admin/offline-leave/", AdminLeaveView.as_view(), name="elm-admin-offline-leave"),
    path(
        "admin/year-end-rollover/",
        YearEndRolloverView.as_view(),
        name="elm-admin-year-end-rollover",
    ),
    path("calendar/holidays/", HolidayCalendarView.as_view(), name="elm-calendar-holidays"),
    path("calendar/vacations/", AcademicVacationView.as_view(), name="elm-calendar-vacations"),
]
