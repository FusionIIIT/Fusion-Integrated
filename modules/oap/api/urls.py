from django.urls import path
from . import views
urlpatterns = [path("leave", views.LeaveList.as_view()), path("bonafide", views.BonafideList.as_view()), path("no-dues", views.NoDuesList.as_view()), path("claims", views.ClaimList.as_view()), path("seminars", views.SeminarList.as_view())]
