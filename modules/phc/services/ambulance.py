"""Ambulance usage logging service (CFR-PHC-008, AFR-PHC-032; UC-PHC-11)."""
from datetime import datetime

from modules.phc.models.ambulance import AmbulanceLog


def log_ambulance_usage(
    patient_name: str,
    destination: str,
    departure_time: datetime,
    driver_name: str,
    recorded_by_user_id: int,
    patient_user_id: int | None = None,
    return_time: datetime | None = None,
    reason: str = "",
    log_id: int | None = None,
) -> AmbulanceLog:
    if log_id:
        log = AmbulanceLog.objects.get(id=log_id)
        log.patient_name = patient_name.strip()
        log.destination = destination.strip()
        log.departure_time = departure_time
        log.driver_name = driver_name.strip()
        log.patient_user_id = patient_user_id
        log.return_time = return_time
        log.reason = reason.strip()
        log.save()
        return log

    return AmbulanceLog.objects.create(
        patient_name=patient_name.strip(),
        destination=destination.strip(),
        departure_time=departure_time,
        return_time=return_time,
        driver_name=driver_name.strip(),
        patient_user_id=patient_user_id,
        reason=reason.strip(),
        recorded_by_user_id=recorded_by_user_id,
    )
