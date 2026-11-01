from django.urls import path
from modules.iwd.api.views import RequestListCreateView
urlpatterns = [path("requests", RequestListCreateView.as_view(), name="iwd-requests")]
