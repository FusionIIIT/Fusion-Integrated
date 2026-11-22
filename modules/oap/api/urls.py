from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modules.oap.api.views import (
    BonafideViewSet,
    BranchChangeViewSet,
    NoDuesViewSet,
    StudentLeaveViewSet,
)

router = DefaultRouter()
router.register(r"leave", StudentLeaveViewSet, basename="leave")
router.register(r"bonafide", BonafideViewSet, basename="bonafide")
router.register(r"no-dues", NoDuesViewSet, basename="no-dues")
router.register(r"branch-change", BranchChangeViewSet, basename="branch-change")

urlpatterns = [
    path("", include(router.urls)),
]
