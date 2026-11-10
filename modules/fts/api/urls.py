"""Fusion Clean Architecture - File Tracking System (FTS) API Routing."""

from rest_framework.routers import DefaultRouter

from modules.fts.api.views import FTSFileViewSet

router = DefaultRouter()
router.register("files", FTSFileViewSet, basename="fts-files")

urlpatterns = router.urls

