"""Patent application queries and detail lookups."""
from __future__ import annotations

from django.db.models import QuerySet

from core.api.exceptions import NotFoundError
from modules.patents.domain import state_machine as sm
from modules.patents.models import (
    ApplicationDocument,
    OfficeActionRecord,
    PatentApplication,
)
from modules.patents.selectors import scoping


def visible_applications(actor) -> QuerySet[PatentApplication]:
    """Return all applications visible to the given actor."""
    return scoping.applications_for(actor)


def get_application(actor, application_id: int) -> PatentApplication | None:
    """Fetch an application within the actor's scope or return None."""
    return scoping.applications_for(actor).filter(pk=application_id).first()


def get_application_or_404(actor, application_id: int) -> PatentApplication:
    """Fetch an application within actor's scope or raise NotFoundError (404)."""
    app = get_application(actor, application_id)
    if app is None:
        raise NotFoundError("Patent application not found.")
    return app


def get_document_or_404(actor, document_id: int) -> ApplicationDocument:
    """Fetch a document within actor's scope or raise NotFoundError (404)."""
    doc = scoping.documents_for(actor).filter(pk=document_id).first()
    if doc is None:
        raise NotFoundError("Document not found.")
    return doc


def get_office_action_or_404(actor, office_action_id: int) -> OfficeActionRecord:
    """Fetch an office action record within actor's scope or raise NotFoundError (404)."""
    oa = scoping.office_actions_for(actor).filter(pk=office_action_id).first()
    if oa is None:
        raise NotFoundError("Office action not found.")
    return oa


# -- Query Helpers for Workflow Oversight and Queues ---------------------------

def applications_pending_director_review(actor) -> QuerySet[PatentApplication]:
    """UC-PMS-032 / BR-PMS-006: Applications awaiting review within Director scope."""
    return scoping.applications_for(actor).filter(status=sm.UNDER_REVIEW)


def applications_pending_attorney_response(actor) -> QuerySet[PatentApplication]:
    """Applications offered to attorney awaiting accept/decline."""
    return scoping.applications_for(actor).filter(status=sm.ASSIGNMENT_OFFERED)


def applications_in_assessment(actor) -> QuerySet[PatentApplication]:
    """Applications currently in assessment by attorney."""
    return scoping.applications_for(actor).filter(status=sm.ASSESSMENT_IN_PROGRESS)


def granted_applications(actor) -> QuerySet[PatentApplication]:
    """UC-PMS-017: Granted patents for post-grant maintenance tracking."""
    return scoping.applications_for(actor).filter(status=sm.GRANTED)
