from rest_framework.routers import DefaultRouter

from modules.spacs.views import (
    ScholarshipApplicationViewSet,
    SupportingDocumentViewSet,
)

router = DefaultRouter()
router.register(
    "applications",
    ScholarshipApplicationViewSet,
    basename="spacs-application",
)
router.register(
    "documents",
    SupportingDocumentViewSet,
    basename="spacs-document",
)

urlpatterns = router.urls
