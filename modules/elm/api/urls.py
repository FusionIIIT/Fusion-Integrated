from django.urls import path, include
from rest_framework import routers
from elm.api import views

router = routers.DefaultRouter()
router.register(r'leaves', views.LeaveViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
