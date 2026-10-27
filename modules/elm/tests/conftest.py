from datetime import date

import pytest

from conftest import make_principal
from modules.directory.contracts import UserDTO
from modules.elm.models import EmployeeConfiguration, HolidayCalendar, Policy
from modules.elm.services import workflow as w


@pytest.fixture
def elm(monkeypatch, db):
    today = [date(2026, 10, 27)]
    monkeypatch.setattr(w.timezone, "localdate", lambda *a, **kw: today[0])
    people = {i: UserDTO(i, f"u{i}", f"Employee {i}", "staff") for i in range(1, 8)}
    people[6] = UserDTO(6, "u6", "Faculty", "faculty")
    monkeypatch.setattr(
        w.directory, "get_users", lambda ids: {i: people[i] for i in ids if i in people}
    )
    monkeypatch.setattr(w.directory, "get_employees", lambda: list(people.values()))
    Policy.objects.create(pk=1, non_working_weekdays=[5, 6], reminder_hours=24, escalation_hours=48)
    for year in (2025, 2026, 2027):
        HolidayCalendar.objects.create(
            year=year,
            published=True,
            holidays=[f"{year}-12-25"],
            restricted_holidays=[f"{year}-11-02", f"{year}-11-03", f"{year}-11-04"],
        )
    for user_id in people:
        routes = {}
        for category in w.rules.CATEGORIES:
            head = {"stage": "unit_head", "user_id": 2, "role": "Unit Head"}
            authority = {"stage": "sanction", "user_id": 3, "role": "Registrar"}
            routes[category] = [head] if category in ("CL", "RH") else [head, authority]
        EmployeeConfiguration.objects.create(
            user_id=user_id,
            unit="CSE",
            designation="Employee",
            eligible_categories=list(w.rules.CATEGORIES),
            routes=routes,
        )

    def actor(user_id=1, role="staff", permissions=None, modules=("elm",)):
        if permissions is None:
            permissions = ("elm.application.self", "elm.task.act", "elm.notification.self")
        return make_principal(
            user_id=user_id,
            kind=people[user_id].kind,
            active_role=role,
            roles=(role,),
            modules=modules,
            permissions=permissions,
        )

    def payload(category="CL", start=date(2026, 11, 2), end=None, **overrides):
        return {
            "category": category,
            "start_date": start,
            "end_date": end or start,
            "half": "full",
            "reason": "Leave required",
            "station_leave": False,
            "station_details": "",
            "medical_reference": "",
            "substitute_id": None,
            **overrides,
        }

    def submit(**kw):
        return w.submit(actor=actor(), data=payload(**kw))

    def decide(app, action="approve", user_id=2, role="Unit Head", reason=""):
        app.refresh_from_db()
        return w.act(
            actor=actor(user_id, role),
            application_id=app.pk,
            action=action,
            revision=app.revision,
            reason=reason,
        )

    def approved(**kw):
        app = submit(**kw)
        if app.category in ("CL", "RH"):
            return decide(app)
        decide(app, "recommend")
        return decide(app, user_id=3, role="Registrar")

    return {
        "today": today,
        "people": people,
        "actor": actor,
        "payload": payload,
        "submit": submit,
        "decide": decide,
        "approved": approved,
    }
