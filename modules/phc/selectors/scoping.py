from modules.phc.models import (
    AmbulanceUsage,
    DoctorScheduleSlot,
    HealthAdvisory,
    InventoryRequisition,
    Notification,
    PatientVisit,
    Prescription,
    ReimbursementClaim,
)


def active_role(actor) -> str:
    return getattr(actor, "active_role", None) or ""


def is_compounder(actor) -> bool:
    return active_role(actor) == "Compounder"


def is_accounts_admin(actor) -> bool:
    return active_role(actor) == "Accounts Admin"


def is_registrar(actor) -> bool:
    return active_role(actor) == "Registrar"


def visits_for(actor):
    base = PatientVisit.objects.prefetch_related("prescriptions")
    if is_compounder(actor):
        return base
    return base.filter(patient_user_id=actor.user_id)


def prescriptions_for(actor):
    base = Prescription.objects.select_related("visit")
    if is_compounder(actor):
        return base
    return base.filter(visit__patient_user_id=actor.user_id)


def visits_by_patient(patient_user_id: int):
    return PatientVisit.objects.filter(patient_user_id=patient_user_id)


def schedules_for_patients():
    return DoctorScheduleSlot.objects.filter(
        publication=DoctorScheduleSlot.Publication.PUBLISHED,
        doctor__is_active=True,
    ).select_related("doctor")


def staff_schedules():
    return DoctorScheduleSlot.objects.select_related("doctor")


def claims_for(actor):
    base = ReimbursementClaim.objects.select_related(
        "prescription", "prescription__visit").prefetch_related("actions")
    if is_compounder(actor):
        return base.filter(state=ReimbursementClaim.State.PENDING_PHC).exclude(
            claimant_user_id=actor.user_id)
    if is_accounts_admin(actor):
        return base.filter(state__in=(ReimbursementClaim.State.PENDING_ACCOUNTS,
                                      ReimbursementClaim.State.APPROVED_PAYMENT)).exclude(
            claimant_user_id=actor.user_id)
    if is_registrar(actor):
        return base.filter(state=ReimbursementClaim.State.PENDING_SANCTION).exclude(
            claimant_user_id=actor.user_id)
    return base.filter(claimant_user_id=actor.user_id)


def requisitions_for(actor):
    base = InventoryRequisition.objects.prefetch_related("lines", "lines__item")
    if is_registrar(actor):
        return base.filter(state=InventoryRequisition.State.PENDING).exclude(
            originator_user_id=actor.user_id)
    if is_compounder(actor):
        return base
    return base.none()


def notifications_for(actor):
    return Notification.objects.filter(recipient_user_id=actor.user_id)


def advisories_for_patients():
    return HealthAdvisory.objects.filter(published_at__isnull=False)


def advisories_for_staff():
    return HealthAdvisory.objects.all()


def ambulance_logs():
    return AmbulanceUsage.objects.all()
