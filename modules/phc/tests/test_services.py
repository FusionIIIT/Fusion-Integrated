from datetime import date, time, timedelta

import pytest
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import ConflictError
from modules.phc.models import (
    Appointment,
    Doctor,
    DoctorSchedule,
    InventoryTransaction,
    Medicine,
    Patient,
)
from modules.phc.services.phc import book_appointment, stock

pytestmark = pytest.mark.django_db


def test_stock_addition_and_dispensing_are_audited_atomically():
    actor = make_principal(user_id=44)
    Patient.objects.create(user_id=44, patient_number="PHC-00000044", registered_by=44)
    medicine = Medicine.objects.create(name="Test medicine", unit="tablet")
    stock(medicine_id=medicine.pk, quantity=10, action="addition", actor=actor)
    stock(medicine_id=medicine.pk, quantity=3, action="dispense", actor=actor, patient_id=44)
    medicine.refresh_from_db()
    assert medicine.quantity == 7
    assert InventoryTransaction.objects.filter(medicine=medicine).count() == 2


def test_insufficient_or_expired_stock_cannot_be_dispensed():
    actor = make_principal(user_id=44)
    medicine = Medicine.objects.create(
        name="Expired medicine",
        unit="tablet",
        quantity=5,
        expires_on=timezone.localdate() - date.resolution,
    )
    with pytest.raises(ConflictError):
        stock(medicine_id=medicine.pk, quantity=1, action="dispense", actor=actor)
    medicine.expires_on = None
    medicine.quantity = 0
    medicine.save()
    with pytest.raises(ConflictError):
        stock(medicine_id=medicine.pk, quantity=1, action="dispense", actor=actor)
    assert InventoryTransaction.objects.filter(medicine=medicine).count() == 0


def test_future_bookings_need_a_schedule_and_cannot_double_book():
    patient = Patient.objects.create(user_id=1, patient_number="PHC-00000001", registered_by=1)
    doctor = Doctor.objects.create(user_id=2)
    local = timezone.localtime(timezone.now() + timedelta(days=14)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    DoctorSchedule.objects.create(
        doctor=doctor,
        weekday=local.weekday(),
        starts_at=time(9),
        ends_at=time(12),
        effective_from=local.date(),
    )
    booked = book_appointment(
        patient_id=patient.pk,
        doctor_id=doctor.pk,
        starts_at=local,
        actor_user_id=patient.user_id,
        reason="Routine visit",
    )
    assert booked.status == "pending"
    with pytest.raises(ConflictError):
        book_appointment(
            patient_id=patient.pk,
            doctor_id=doctor.pk,
            starts_at=local,
            actor_user_id=patient.user_id,
            reason="Second request",
        )
    assert Appointment.objects.count() == 1
