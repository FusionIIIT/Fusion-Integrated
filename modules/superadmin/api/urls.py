from __future__ import annotations

from django.urls import re_path

from modules.superadmin.api import views as v

urlpatterns = [
    # Dashboard
    re_path(r"^dashboard/?$", v.DashboardView.as_view(), name="superadmin-dashboard"),
    # User archival
    re_path(
        r"^archival/users/?$", v.ArchivedUserListView.as_view(), name="superadmin-archival-users"
    ),
    re_path(
        r"^archival/users/(?P<user_id>\d+)/?$",
        v.ArchivedUserDetailView.as_view(),
        name="superadmin-archival-user-detail",
    ),
    re_path(
        r"^archival/users/(?P<user_id>\d+)/restore/?$",
        v.ArchivedUserRestoreView.as_view(),
        name="superadmin-archival-user-restore",
    ),
    # Historical dataset archives
    re_path(
        r"^archival/history/?$",
        v.HistoricalArchiveListView.as_view(),
        name="superadmin-archival-history",
    ),
    re_path(
        r"^archival/history/(?P<pk>\d+)/restore/?$",
        v.HistoricalArchiveRestoreView.as_view(),
        name="superadmin-archival-history-restore",
    ),
    re_path(
        r"^archival/datasets/?$",
        v.HistoricalArchiveListView.as_view(),
        name="superadmin-archival-datasets",
    ),
    # Permanent purge dual authorization
    re_path(
        r"^purge/requests/?$", v.PurgeRequestListView.as_view(), name="superadmin-purge-requests"
    ),
    re_path(
        r"^purge/requests/(?P<pk>\d+)/decision/?$",
        v.PurgeRequestDecisionView.as_view(),
        name="superadmin-purge-request-decision",
    ),
    re_path(
        r"^purge/requests/(?P<pk>\d+)/execute/?$",
        v.PurgeRequestExecuteView.as_view(),
        name="superadmin-purge-request-execute",
    ),
    # Effective-dated policies
    re_path(r"^policies/?$", v.PolicyParameterListView.as_view(), name="superadmin-policies"),
    re_path(
        r"^policy/parameters/?$",
        v.PolicyParameterListView.as_view(),
        name="superadmin-policy-parameters",
    ),
    # Compliance audit logs
    re_path(r"^audit/logs/?$", v.AuditLogListView.as_view(), name="superadmin-audit-logs"),
    re_path(r"^audit/export/?$", v.AuditLogExportView.as_view(), name="superadmin-audit-export"),
]
