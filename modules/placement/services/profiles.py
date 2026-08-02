"""Student placement profiles and resume generation (PC-UC-001, PC-UC-002)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import NotFoundError
from modules.directory import contracts as directory
from modules.placement.domain import profile_completeness as pc
from modules.placement.models import ProfileDocument, StudentProfile

EDITABLE = ("headline", "about", "phone", "alternate_email", "skills",
            "achievements", "certifications", "experience", "projects",
            "education", "github_url", "linkedin_url", "portfolio_url")


def _recompute(profile: StudentProfile) -> StudentProfile:
    has_resume = ProfileDocument.objects.filter(
        profile=profile, kind="resume", is_active=True).exists()
    data = {k: getattr(profile, k) for k in EDITABLE}
    data["resume"] = has_resume
    result = pc.evaluate(data)
    profile.completeness_percent = result.percent
    profile.is_complete = result.is_complete
    profile.missing_fields = result.missing
    return profile


@transaction.atomic
def upsert(*, user_id: int, data: dict) -> StudentProfile:
    """Create or update. Only whitelisted fields are writable — a client cannot
    set completeness, and above all cannot set an academic figure: CPI is owned
    by the ERP and read through the IAM, never accepted from the browser."""
    profile, _ = StudentProfile.objects.get_or_create(user_id=user_id)
    for key in EDITABLE:
        if key in data:
            setattr(profile, key, data[key])
    _recompute(profile)
    profile.save()
    return profile


@transaction.atomic
def recompute(*, user_id: int) -> StudentProfile:
    profile = StudentProfile.objects.filter(user_id=user_id).first()
    if profile is None:
        raise NotFoundError("No placement profile yet.")
    _recompute(profile)
    profile.save(update_fields=["completeness_percent", "is_complete",
                                "missing_fields", "updated_at"])
    return profile


def build_resume(*, user_id: int, standing: dict | None = None) -> dict:
    """A structured resume derived from the profile (PC-UC-002).

    Returns data, not a PDF: rendering is a presentation concern and keeping it
    out of here means the same payload drives the web view, a download and a
    recruiter's export without three sources of truth.

    Academic figures are injected by the caller from the IAM projection — this
    function never reads them from the profile, because they are not there.
    """
    profile = StudentProfile.objects.filter(user_id=user_id).first()
    if profile is None:
        raise NotFoundError("No placement profile yet.")

    person = directory.get_users([user_id]).get(user_id)
    return {
        "identity": {
            "name": getattr(person, "display_name", "") or "",
            "roll_no": getattr(person, "username", "") or "",
            "email": getattr(person, "email", "") or profile.alternate_email,
            "phone": profile.phone,
            "programme": getattr(person, "programme", "") or "",
            "discipline": getattr(person, "discipline", "") or "",
            "batch_year": getattr(person, "batch_year", None),
        },
        "headline": profile.headline,
        "about": profile.about,
        # Rendered as "8.1 · Sem 5 (Odd)" — a CPI without its provenance is
        # what starts the "my CPI is wrong" support queue.
        "academic": standing or None,
        "skills": profile.skills,
        "education": profile.education,
        "experience": profile.experience,
        "projects": profile.projects,
        "certifications": profile.certifications,
        "achievements": profile.achievements,
        "links": {"github": profile.github_url, "linkedin": profile.linkedin_url,
                  "portfolio": profile.portfolio_url},
        "completeness": {"percent": profile.completeness_percent,
                         "missing": profile.missing_fields},
    }
