"""Ambulance usage selectors (CFR-PHC-008, AFR-PHC-032)."""
from modules.phc.models.ambulance import AmbulanceLog


def list_ambulance_logs() -> list[AmbulanceLog]:
    return list(AmbulanceLog.objects.all().order_by("-departure_time"))
