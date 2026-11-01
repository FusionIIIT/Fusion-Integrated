from rest_framework.routers import DefaultRouter

from .views import (
    VisitRequestViewSet,
    VisitorPassViewSet,
    VisitLogViewSet,
)

router = DefaultRouter()

router.register(
    "visit-requests",
    VisitRequestViewSet,
    basename="visit-request",
)

router.register(
    "visitor-passes",
    VisitorPassViewSet,
    basename="visitor-pass",
)

router.register(
    "visit-logs",
    VisitLogViewSet,
    basename="visit-log",
)

urlpatterns = router.urls