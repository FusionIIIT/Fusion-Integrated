from django.urls import path

from modules.directory.api.views import UserSearchView

urlpatterns = [path("users", UserSearchView.as_view(), name="directory-users")]
