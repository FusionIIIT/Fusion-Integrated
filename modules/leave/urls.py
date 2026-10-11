from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeaveApplicationViewSet

router = DefaultRouter()
router.register(r'leave-applications', LeaveApplicationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
