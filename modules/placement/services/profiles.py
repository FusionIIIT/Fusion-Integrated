"""Student placement profile persistence and generated resume (PC-UC-001/023)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError
from fusion_auth.client import IamUnavailable
from modules.placement.models import ProfileDocument, StudentPlacementProfile
from modules.placement.services import candidates


@transaction.atomic
def save(*, user_id: int, values: dict) -> StudentPlacementProfile:
    """Create or update only the authenticated student's editable sections."""
    profile, _ = StudentPlacementProfile.objects.select_for_update().get_or_create(
        user_id=user_id)
    for name, value in values.items():
        setattr(profile, name, value)
    profile.save(update_fields=[*values.keys(), "updated_at"])
    return profile


def get(*, user_id: int) -> StudentPlacementProfile | None:
    return StudentPlacementProfile.objects.filter(user_id=user_id).first()


def generate_resume(*, user_id: int) -> dict:
    """Return a structured resume, joining externally owned academic facts."""
    profile = get(user_id=user_id)
    if profile is None:
        raise ConflictError("Add placement profile information before generating a resume.",
                            code="resume_profile_missing")
    person = candidates.candidate_record(user_id=user_id)
    if not (profile.summary or profile.skills or profile.projects
            or profile.achievements or profile.certifications):
        raise ConflictError("The saved profile has no resume content yet.",
                            code="resume_content_missing")

    academic = None
    try:
        from modules.placement.services.facts import academic_facts
        standing = academic_facts([user_id]).get(user_id)
        if standing:
            academic = {
                "programme": person["programme"],
                "discipline": person["discipline"],
                "batch_year": person["batch_year"],
                "cpi": str(standing["cpi"]) if standing.get("cpi") is not None else None,
                "earned_credits": (str(standing["earned_credits"])
                                   if standing.get("earned_credits") is not None else None),
                "active_backlogs": standing.get("active_backlogs"),
                "semester": standing.get("semester"),
            }
    except IamUnavailable:
        # Directory identity and saved placement data are still renderable.
        academic = None

    documents = list(ProfileDocument.objects.filter(
        user_id=user_id, is_active=True, kind__in=("certificate", "other")
    ).order_by("created_at").values("kind", "title", "original_filename"))
    return {
        "user_id": user_id,
        "name": person["name"],
        "email": person["email"],
        "roll_no": person["roll_no"],
        "academic": academic,
        "summary": profile.summary,
        "skills": profile.skills,
        "projects": profile.projects,
        "achievements": profile.achievements,
        "certifications": profile.certifications,
        "links": profile.links,
        "documents": documents,
        "generated_at": profile.updated_at.isoformat(),
    }
