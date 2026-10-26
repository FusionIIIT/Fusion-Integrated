"""The printable/exportable leave application (EL-UC-013), rendered with autoescaping."""
from __future__ import annotations

from django.template.loader import render_to_string
from django.utils import timezone

from modules.directory import contracts as directory
from modules.leave.domain import categories as cat
from modules.leave.models import LeaveRequest


def render(req: LeaveRequest) -> str:
    person = directory.get_users([req.user_id]).get(req.user_id)
    return render_to_string("leave/application.html", {
        "req": req, "person": person, "category_label": cat.LABELS.get(req.category, req.category),
        "events": list(req.events.all()), "substitutions": list(req.substitutions.all()),
        "generated_at": timezone.localtime(),
    })
