from django.urls import path

from iam.views.academics import (AcademicDirectoryView,
                                 AcademicFiltersView,
                                 AcademicStandingsView)
from iam.views.auth import LoginView, LogoutView, MeView
from iam.views.directory import DirectoryUsersView

urlpatterns = [
    path("v1/auth/login", LoginView.as_view(), name="iam-login"),
    path("v1/auth/logout", LogoutView.as_view(), name="iam-logout"),
    path("v1/me", MeView.as_view(), name="iam-me"),
    path("v1/directory/users", DirectoryUsersView.as_view(), name="iam-directory"),
    path("v1/academics/standings", AcademicStandingsView.as_view(),
         name="iam-academics"),
    path("v1/academics/directory", AcademicDirectoryView.as_view(),
         name="iam-academic-directory"),
    path("v1/academics/filters", AcademicFiltersView.as_view(),
         name="iam-academic-filters"),
]
