from django.urls import path

from modules.vms.api.admin import views

urlpatterns = [
    path("blacklist", views.BlacklistView.as_view(), name="vms-blacklist"),
    path("policies", views.PolicyListView.as_view(), name="vms-policies"),
    path("policies/<int:pk>/publish", views.PolicyPublishView.as_view(),
         name="vms-policy-publish"),
]
