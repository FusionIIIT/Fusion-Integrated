from django.urls import path

from ..views import directory

urlpatterns = [
    path("departments/", directory.get_all_departments, name="get_all_departments"),
    path("batches/", directory.get_all_batches, name="get_all_batches"),
    path("programmes/", directory.get_all_programmes, name="get_all_programmes"),
    path("users/", directory.UserListView.as_view(), name="user-list"),
]
