"""Factories are the only way tests create MMS rows (testing-strategy.md).

Traits express states, so a test reads as intent: `RegistrationFactory(approved=True)`.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from modules.mms import models as m
from modules.mms.tests.helpers import CARETAKER_ID, STUDENT_ID, TODAY, days_from_today


class RegistrationWindowFactory(DjangoModelFactory):
    class Meta:
        model = m.MessRegistrationWindow

    academic_year = "2026-27"
    semester = "Autumn"
    start_date = TODAY
    end_date = days_from_today(14)
    status = "open"
    opened_by_user_id = CARETAKER_ID

    class Params:
        closed = factory.Trait(status="closed")


class RegistrationFactory(DjangoModelFactory):
    class Meta:
        model = m.MessRegistration

    user_id = STUDENT_ID
    window = factory.SubFactory(RegistrationWindowFactory)
    status = "submitted"
    reason = "Staying in hostel"

    class Params:
        approved = factory.Trait(
            status="approved",
            reviewed_by_user_id=CARETAKER_ID,
            reviewed_at=factory.LazyFunction(timezone.now),
        )
        rejected = factory.Trait(
            status="rejected",
            reviewed_by_user_id=CARETAKER_ID,
            reviewed_at=factory.LazyFunction(timezone.now),
        )


class DeregistrationFactory(DjangoModelFactory):
    class Meta:
        model = m.MessDeregistration

    user_id = STUDENT_ID
    registration = factory.SubFactory(RegistrationFactory, approved=True)
    status = "submitted"
    reason = "Moving off campus"

    class Params:
        approved = factory.Trait(status="approved", effective_date=days_from_today(1))


class RebateFactory(DjangoModelFactory):
    class Meta:
        model = m.MessRebate

    user_id = STUDENT_ID
    start_date = days_from_today(5)
    end_date = days_from_today(8)
    duration_days = 4
    reason = "medical"
    status = "submitted"

    class Params:
        approved = factory.Trait(status="approved")
        rejected = factory.Trait(status="rejected")


class VacationSurveyFactory(DjangoModelFactory):
    class Meta:
        model = m.VacationFoodSurvey

    title = "Winter break"
    vacation_start_date = date(2026, 12, 20)
    vacation_end_date = date(2027, 1, 5)
    response_deadline = factory.LazyFunction(lambda: timezone.now() + timedelta(days=3))
    status = "open"
    created_by_user_id = CARETAKER_ID

    class Params:
        closed = factory.Trait(status="closed")


class SpecialFoodFactory(DjangoModelFactory):
    class Meta:
        model = m.SpecialFoodRequest

    user_id = STUDENT_ID
    requested_date = days_from_today(3)
    meal_type = "dinner"
    food_details = "Khichdi"
    reason = "Fever"
    cost = Decimal("50.00")
    status = "requested"

    class Params:
        approved = factory.Trait(status="approved")
        served = factory.Trait(status="served")
        cancelled = factory.Trait(status="cancelled")
        rejected = factory.Trait(status="rejected")


class BillFactory(DjangoModelFactory):
    class Meta:
        model = m.MessBill

    user_id = STUDENT_ID
    billing_month = date(2026, 4, 1)
    base_amount = Decimal("3000.00")
    total_amount = Decimal("3000.00")
    status = "generated"

    class Params:
        published = factory.Trait(status="published", published_at=factory.LazyFunction(timezone.now))


class MenuFactory(DjangoModelFactory):
    class Meta:
        model = m.MessMenu
        django_get_or_create = ("day_of_week", "meal_type")

    day_of_week = "monday"
    meal_type = "lunch"
    items = factory.LazyFunction(lambda: ["Dal", "Rice"])


class AnnouncementFactory(DjangoModelFactory):
    class Meta:
        model = m.MessAnnouncement

    title = "Mess closed Sunday"
    content = "Deep cleaning."
    published_by_user_id = CARETAKER_ID
    published_by_role = "mess_caretaker"


class FeedbackFactory(DjangoModelFactory):
    class Meta:
        model = m.MessFeedback

    user_id = STUDENT_ID
    description = "Rice was cold."
