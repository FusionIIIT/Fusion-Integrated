"""URL routing for VMS REST API endpoints."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modules.vms.api.views import (
    BlacklistViewSet,
    BulkEventViewSet,
    CampusZoneViewSet,
    EmergencyMusterViewSet,
    GateAlertViewSet,
    GateTerminalViewSet,
    SafeListViewSet,
    VisitorViewSet,
    VisitPassViewSet,
    VisitRequestViewSet,
    ZoneAccessViewSet,
)

router = DefaultRouter()
router.register(r"visitors", VisitorViewSet, basename="visitor")
router.register(r"requests", VisitRequestViewSet, basename="visit-request")
router.register(r"passes", VisitPassViewSet, basename="visit-pass")
router.register(r"gate", GateTerminalViewSet, basename="gate-terminal")
router.register(r"zones", ZoneAccessViewSet, basename="zone-access")
router.register(r"muster", EmergencyMusterViewSet, basename="emergency-muster")
router.register(r"blacklist", BlacklistViewSet, basename="blacklist")
router.register(r"safelist", SafeListViewSet, basename="safelist")
router.register(r"campus-zones", CampusZoneViewSet, basename="campus-zones")
router.register(r"alerts", GateAlertViewSet, basename="gate-alerts")
router.register(r"events", BulkEventViewSet, basename="bulk-events")

urlpatterns = [
    path("", include(router.urls)),
]
