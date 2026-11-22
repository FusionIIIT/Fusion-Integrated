from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ComplaintViewSet, EstimateViewSet, FinalBillViewSet

router = DefaultRouter()
router.register(r"complaints", ComplaintViewSet, basename="complaint")
router.register(r"estimates", EstimateViewSet, basename="estimate")
router.register(r"bills", FinalBillViewSet, basename="bill")

urlpatterns = [
    path("", include(router.urls)),
]
