from django.urls import path
from . import views

app_name = "leave_management"
urlpatterns = [
    path("apply/", views.apply_leave, name="apply_leave"),
]
