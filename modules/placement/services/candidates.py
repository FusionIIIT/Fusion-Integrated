"""What a recruiter or the TPO may read about a person.

Assembled, never stored: identity and the resume come from the ERP portal via
the directory projection, academic figures from the IAM. Placement holding its
own copy is what made a student maintain two profiles.
"""
from __future__ import annotations

from core.api.exceptions import NotFoundError
from modules.directory import contracts as directory


def candidate_record(*, user_id: int, standing: dict | None = None) -> dict:
    """One person's candidate record, as the portal and the IAM describe them."""
    person = directory.get_users([user_id]).get(user_id)
    if person is None:
        raise NotFoundError("No such person.")
    return {
        "user_id": user_id,
        "name": person.display_name,
        "roll_no": person.username,
        "email": person.email,
        "programme": person.programme,
        "discipline": person.discipline,
        "batch_year": person.batch_year,
        # The link the student maintains on the portal's own profile page.
        "resume_link": person.resume_link,
        "profile_completed": person.profile_completed,
        # Rendered with its provenance; a bare CPI starts the support queue.
        "academic": standing or None,
    }
