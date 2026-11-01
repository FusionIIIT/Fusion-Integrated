from enum import StrEnum


class AppointmentStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    NO_SHOW = "no_show"


TRANSITIONS = {
    AppointmentStatus.PENDING: {
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.REJECTED,
    },
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    },
    AppointmentStatus.COMPLETED: set(),
    AppointmentStatus.CANCELLED: set(),
    AppointmentStatus.REJECTED: set(),
    AppointmentStatus.NO_SHOW: set(),
}


def validate_transition(current: str, target: str) -> None:
    if target not in TRANSITIONS.get(AppointmentStatus(current), set()):
        raise ValueError(f"Appointment cannot transition from {current} to {target}.")
