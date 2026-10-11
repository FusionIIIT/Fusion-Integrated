from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LeaveRequestViewSet

router = DefaultRouter()
router.register("leave-requests", LeaveRequestViewSet, basename="elm-leave-request")

urlpatterns = [path("", include(router.urls))]
