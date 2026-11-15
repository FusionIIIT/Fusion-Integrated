from datetime import date

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.patents import models as m
from modules.patents import services as svc
from modules.patents.domain import workflow as wf
from modules.patents.selectors import visible as _visible

MODULE = HasModuleGrant("patent_management")


def _row(app: m.Application) -> dict:
    return {
        "id": app.id, "application_no": app.application_no, "title": app.title,
        "status": app.status, "status_label": wf.LABELS.get(app.status, app.status),
        "domain": app.domain, "applicant_user_id": app.applicant_user_id,
        "director_user_id": app.director_user_id, "review_due_on": app.review_due_on,
        "attorney_user_id": app.attorney_user_id, "attorney_status": app.attorney_status,
        "budget_status": app.budget_status,
        "budget_total": None if app.budget_total is None else f"{app.budget_total:.2f}",
        "created_at": app.created_at, "submitted_at": app.submitted_at,
    }


def _detail(app: m.Application) -> dict:
    row = _row(app)
    row.update({
        "abstract": app.abstract, "description": app.description, "claims": app.claims,
        "decision_justification": app.decision_justification, "decision_at": app.decision_at,
        "revision_count": app.revision_count,
        "opinion": {"recommendation": app.opinion_recommendation, "text": app.opinion_text},
        "filing": {"external_filing_id": app.external_filing_id, "filing_date": app.filing_date},
        "events": [
            {"id": e.id, "action": e.action, "actor_user_id": e.actor_user_id,
             "from_state": e.from_state, "to_state": e.to_state, "detail": e.detail,
             "created_at": e.created_at}
            for e in app.events.all()
        ],
    })
    return row


def _get(principal, pk: int) -> m.Application:
    app = _visible(principal).filter(pk=pk).first()
    if app is None:
        raise NotFoundError("Application not found.", code="not_found")
    return app


def _parse_date(raw, field: str) -> date:
    try:
        return date.fromisoformat(str(raw))
    except (TypeError, ValueError):
        raise BadRequestError(f"{field} must be a date (YYYY-MM-DD).", code="validation") from None


class ApplicationListView(APIView):
    permission_classes = [MODULE, HasPermission(
        "patent_management.application.view_own",
        "patent_management.application.view_assigned",
        "patent_management.application.view_all")]

    def get(self, request):
        qs = _visible(request.principal).order_by("-created_at")
        return Response({"results": [_row(a) for a in qs[:200]]})

    def post(self, request):
        app = svc.create_draft(request.principal, request.data)
        return Response(_detail(app), status=status.HTTP_201_CREATED)


class ApplicationDetailView(APIView):
    permission_classes = [MODULE, HasPermission(
        "patent_management.application.view_own",
        "patent_management.application.view_assigned",
        "patent_management.application.view_all")]

    def get(self, request, pk: int):
        return Response(_detail(_get(request.principal, pk)))


def _submit(p, app, d):
    return svc.submit(p, app)


def _revise(p, app, d):
    return svc.revise(p, app, str(d.get("response", "")))


def _withdraw(p, app, d):
    return svc.withdraw(p, app, str(d.get("reason", "")))


def _appeal(p, app, d):
    return svc.appeal(p, app, str(d.get("grounds", "")))


def _assign_director(p, app, d):
    return svc.assign_director(p, app, _int(d.get("director_user_id")))


def _assign_attorney(p, app, d):
    return svc.assign_attorney(p, app, _int(d.get("attorney_user_id")))


def _review(p, app, d):
    return svc.decide_review(p, app, str(d.get("decision", "")), str(d.get("justification", "")))


def _appeal_decision(p, app, d):
    return svc.decide_appeal(p, app, str(d.get("outcome", "")), str(d.get("reasoning", "")))


def _attorney_response(p, app, d):
    return svc.respond_assignment(p, app, bool(d.get("accept")))


def _opinion(p, app, d):
    return svc.record_opinion(p, app, str(d.get("recommendation", "")), str(d.get("text", "")))


def _budget(p, app, d):
    return svc.record_budget(p, app, str(d.get("filing_fee", 0)),
                             str(d.get("attorney_fee", 0)), str(d.get("admin_cost", 0)))


def _budget_decision(p, app, d):
    return svc.decide_budget(p, app, str(d.get("decision", "")))


def _filing(p, app, d):
    return svc.record_filing(p, app, str(d.get("external_filing_id", "")),
                             _parse_date(d.get("filing_date"), "filing_date"))


def _int(raw) -> int | None:
    try:
        return int(raw) if raw not in (None, "") else None
    except (TypeError, ValueError):
        raise BadRequestError("A user id must be a number.", code="validation") from None


#: action -> (permission that gates it, handler). Ownership/assignment checks live in services.
ACTIONS = {
    "submit": ("patent_management.application.submit", _submit),
    "revise": ("patent_management.application.revise", _revise),
    "withdraw": ("patent_management.application.withdraw", _withdraw),
    "appeal": ("patent_management.application.appeal", _appeal),
    "assign-director": ("patent_management.route.manage", _assign_director),
    "assign-attorney": ("patent_management.route.manage", _assign_attorney),
    "review": ("patent_management.review.decide", _review),
    "appeal-decision": ("patent_management.appeal.decide", _appeal_decision),
    "attorney-response": ("patent_management.attorney.respond", _attorney_response),
    "opinion": ("patent_management.attorney.respond", _opinion),
    "budget": ("patent_management.attorney.respond", _budget),
    "budget-decision": ("patent_management.budget.decide", _budget_decision),
    "filing": ("patent_management.attorney.respond", _filing),
}


class ApplicationActionView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk: int, action: str):
        if action not in ACTIONS:
            raise NotFoundError("Unknown action.", code="not_found")
        code, handler = ACTIONS[action]
        if not request.principal.has_permission(code):
            from core.api.exceptions import PermissionDeniedError
            raise PermissionDeniedError(
                "You do not have permission for this action.", code="forbidden"
            )
        app = _get(request.principal, pk)
        result = handler(request.principal, app, request.data)
        return Response(_detail(result or app))


class DocumentUploadView(APIView):
    permission_classes = [MODULE, HasPermission("patent_management.application.submit")]

    def post(self, request, pk: int):
        app = _get(request.principal, pk)
        upload = request.FILES.get("file")
        if upload is None:
            raise BadRequestError("Attach a PDF file.", code="validation")
        kind = str(request.data.get("kind", "")).strip() or "specification"
        sensitivity = str(request.data.get("sensitivity", "internal"))
        version = svc.upload_document(request.principal, app, kind, upload, sensitivity)
        return Response({"id": version.id, "version_no": version.version_no,
                         "sha256": version.sha256, "file_name": version.file_name},
                        status=status.HTTP_201_CREATED)


class InventorsView(APIView):
    permission_classes = [MODULE, HasPermission("patent_management.application.submit")]

    def put(self, request, pk: int):
        app = _get(request.principal, pk)
        svc.set_inventors(request.principal, app, request.data.get("inventors") or [])
        return Response(_detail(app))


class NotificationListView(APIView):
    permission_classes = [MODULE, HasPermission("patent_management.notification.view")]

    def get(self, request):
        rows = m.Notification.objects.filter(recipient_user_id=request.principal.user_id)[:200]
        return Response({"results": [
            {"id": n.id, "kind": n.kind, "message": n.message, "created_at": n.created_at,
             "read": n.read_at is not None, "application_id": n.application_id} for n in rows]})


class NotificationReadView(APIView):
    permission_classes = [MODULE, HasPermission("patent_management.notification.view")]

    def post(self, request, nid: int):
        from django.utils import timezone

        row = m.Notification.objects.filter(
            pk=nid, recipient_user_id=request.principal.user_id).first()
        if row is None:
            raise NotFoundError("Notification not found.", code="not_found")
        row.read_at = row.read_at or timezone.now()
        row.save(update_fields=["read_at"])
        return Response({"id": row.id, "read": True})


class SummaryView(APIView):
    permission_classes = [MODULE, HasPermission("patent_management.report.own",
                                                "patent_management.report.view")]

    def get(self, request):
        return Response(svc.summary(request.principal))
