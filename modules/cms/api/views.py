"""CMS API: permission gates, serializers, and transactional service calls."""

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.text import get_valid_filename
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.pagination import CursorPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.cms import selectors, services, storage
from modules.cms.api import serializers as s
from modules.cms.models import (
    CmsRoleAssignment,
    Complaint,
    ComplaintAnnouncement,
    ComplaintAttachment,
    ComplaintFeedback,
    ReopeningRequest,
)


class CmsPagination(CursorPagination):
    page_size = 25
    page_size_query_param = "limit"
    max_page_size = 100
    ordering = "-id"


class CmsConfigView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.complaint.submit")]

    @extend_schema(responses=s.CmsConfigSerializer)
    def get(self, request):
        return Response(
            {
                "attachment_max_bytes": settings.CMS_ATTACHMENT_MAX_BYTES,
                "attachment_max_count": settings.CMS_ATTACHMENT_MAX_COUNT,
                "attachment_allowed_extensions": list(settings.CMS_ATTACHMENT_ALLOWED_EXTENSIONS),
            }
        )


def _actor(request):
    return request.principal


def _active_role(actor, role):
    if not selectors.has_active_role(actor.user_id, role):
        raise PermissionDeniedError(f"An active CMS {role} appointment is required.")


def _active_staff(actor):
    if selectors.has_active_role(actor.user_id, "handler"):
        return "handler"
    if selectors.has_active_role(actor.user_id, "supervisor"):
        return "supervisor"
    raise PermissionDeniedError(
        "An active Complaint Handler or Complaint Supervisor role is required."
    )


def _paginate(request, qs, serializer=s.ComplaintSerializer):
    pager = CmsPagination()
    page = pager.paginate_queryset(qs, request)
    return pager.get_paginated_response(serializer(page, many=True).data)


def _apply_filters(qs, params):
    if value := params.get("status"):
        qs = qs.filter(status=value)
    if value := params.get("category"):
        qs = qs.filter(category__iexact=value)
    if value := params.get("priority"):
        qs = qs.filter(priority=value)
    if value := params.get("escalated"):
        qs = qs.filter(escalated_at__isnull=(value.lower() != "true"))
    if value := params.get("q"):
        qs = qs.filter(
            Q(complaint_id__icontains=value)
            | Q(category__icontains=value)
            | Q(description__icontains=value)
        )
    if value := params.get("from"):
        parsed = parse_date(value)
        if parsed is None:
            raise BadRequestError("The 'from' filter must use YYYY-MM-DD.")
        qs = qs.filter(created_at__date__gte=parsed)
    if value := params.get("to"):
        parsed = parse_date(value)
        if parsed is None:
            raise BadRequestError("The 'to' filter must use YYYY-MM-DD.")
        qs = qs.filter(created_at__date__lte=parsed)
    ordering = params.get("ordering", "-created_at")
    if ordering.lstrip("-") in {"created_at", "updated_at", "status", "priority"}:
        qs = qs.order_by(ordering, "-id")
    return qs


def _can_read(request, complaint):
    actor = _actor(request)
    if complaint.complainant_user_id == actor.user_id:
        return True
    role = (
        "handler"
        if selectors.has_active_role(actor.user_id, "handler")
        else "supervisor"
        if selectors.has_active_role(actor.user_id, "supervisor")
        else None
    )
    return bool(
        role
        and (
            role == "supervisor"
            or complaint.assigned_handler_user_id == actor.user_id
            or complaint.status in {"submitted", "in_progress", "resolved", "rejected", "closed"}
        )
    )


class ComplaintListCreateView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    pagination_class = CmsPagination

    def get_permissions(self):
        if self.request.method == "POST":
            return [HasModuleGrant("cms")(), HasPermission("cms.complaint.submit")()]
        return [
            HasModuleGrant("cms")(),
            HasPermission("cms.complaint.track", "cms.complaint.view")(),
        ]

    @extend_schema(responses=s.ComplaintSerializer(many=True))
    def get(self, request):
        actor = _actor(request)
        if actor.has_permission("cms.complaint.view"):
            role = _active_staff(actor)
            qs = Complaint.objects.all()
            if role == "handler":
                qs = qs.filter(
                    Q(assigned_handler_user_id=actor.user_id)
                    | Q(assigned_handler_user_id__isnull=True)
                )
        else:
            qs = Complaint.objects.filter(complainant_user_id=actor.user_id)
        qs = qs.prefetch_related("attachments", "history", "progress_updates", "reopening_requests")
        return _paginate(request, _apply_filters(qs, request.query_params))

    @extend_schema(request=s.ComplaintSubmissionSerializer, responses={201: s.ComplaintSerializer})
    def post(self, request):
        serializer = s.ComplaintSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if len(data.get("attachments", [])) > settings.CMS_ATTACHMENT_MAX_COUNT:
            raise ConflictError(
                "Too many attachments for this complaint.", code="too_many_attachments"
            )
        created = []
        try:
            with transaction.atomic():
                complaint = services.submit(
                    actor=_actor(request),
                    category=data["category"],
                    description=data["description"],
                )
                for upload in data.get("attachments", []):
                    # Retain each path for cleanup if a later upload fails.
                    created.append(_attach(complaint, upload, _actor(request)))  # noqa: PERF401
        except Exception:
            for item in created:
                storage.delete(item.storage_key)
            raise
        return Response(s.ComplaintSerializer(complaint).data, status=status.HTTP_201_CREATED)


class MyComplaintsView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.complaint.track")]

    @extend_schema(responses=s.ComplaintSerializer(many=True))
    def get(self, request):
        qs = Complaint.objects.filter(complainant_user_id=_actor(request).user_id)
        qs = qs.prefetch_related("attachments", "history", "progress_updates", "reopening_requests")
        return _paginate(request, _apply_filters(qs, request.query_params))


class ComplaintDetailView(APIView):
    permission_classes = [
        HasModuleGrant("cms"),
        HasPermission("cms.complaint.track", "cms.complaint.view"),
    ]

    @extend_schema(responses=s.ComplaintSerializer)
    def get(self, request, pk):
        complaint = services.get_complaint(pk)
        if not _can_read(request, complaint):
            raise NotFoundError("No such complaint.")
        return Response(s.ComplaintSerializer(complaint).data)


class HandlingSetupView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.complaint.assign")]

    @extend_schema(request=s.HandlingSetupSerializer, responses=s.ComplaintSerializer)
    def post(self, request, pk):
        _active_role(_actor(request), "handler")
        serializer = s.HandlingSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            s.ComplaintSerializer(
                services.setup_handling(
                    complaint_id=pk, actor=_actor(request), **serializer.validated_data
                )
            ).data
        )


class ProgressView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.complaint.update")]

    @extend_schema(request=s.TextActionSerializer, responses=s.ComplaintProgressSerializer)
    def post(self, request, pk):
        _active_role(_actor(request), "handler")
        serializer = s.TextActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        progress = services.add_progress(
            complaint_id=pk, actor=_actor(request), text=serializer.validated_data["text"]
        )
        return Response(
            s.ComplaintProgressSerializer(progress).data, status=status.HTTP_201_CREATED
        )


class OutcomeView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.complaint.resolve")]

    @extend_schema(request=s.OutcomeSerializer, responses=s.ComplaintSerializer)
    def post(self, request, pk):
        _active_role(_actor(request), "handler")
        serializer = s.OutcomeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            s.ComplaintSerializer(
                services.decide_outcome(
                    complaint_id=pk, actor=_actor(request), **serializer.validated_data
                )
            ).data
        )


class UserClosureView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.close.user")]
    serializer_class = s.ComplaintSerializer

    @extend_schema(responses=s.ComplaintSerializer)
    def post(self, request, pk):
        return Response(
            s.ComplaintSerializer(
                services.verify_closure(
                    complaint_id=pk, actor=_actor(request), verifier="complainant"
                )
            ).data
        )


class SupervisorClosureView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.close.supervisor")]
    serializer_class = s.ComplaintSerializer

    @extend_schema(responses=s.ComplaintSerializer)
    def post(self, request, pk):
        _active_role(_actor(request), "supervisor")
        return Response(
            s.ComplaintSerializer(
                services.verify_closure(
                    complaint_id=pk, actor=_actor(request), verifier="supervisor"
                )
            ).data
        )


class ReopeningRequestView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.complaint.reopen")]

    @extend_schema(request=s.TextActionSerializer, responses=s.ReopeningRequestSerializer)
    def post(self, request, pk):
        serializer = s.TextActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.request_reopening(
            complaint_id=pk, actor=_actor(request), reason=serializer.validated_data["text"]
        )
        return Response(s.ReopeningRequestSerializer(result).data, status=status.HTTP_201_CREATED)


class ReopeningReviewListView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.reopening.review")]

    @extend_schema(responses=s.ReopeningRequestSerializer(many=True))
    def get(self, request):
        _active_role(_actor(request), "supervisor")
        qs = ReopeningRequest.objects.filter(decision="pending").select_related("complaint")
        return _paginate(request, qs, s.ReopeningRequestSerializer)


class ReopeningDecisionView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.reopening.review")]

    @extend_schema(request=s.ReopeningDecisionSerializer, responses=s.ReopeningRequestSerializer)
    def post(self, request, pk):
        _active_role(_actor(request), "supervisor")
        serializer = s.ReopeningDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            s.ReopeningRequestSerializer(
                services.review_reopening(
                    request_id=pk, actor=_actor(request), **serializer.validated_data
                )
            ).data
        )


class EscalationView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.escalation.manual")]
    serializer_class = s.ComplaintSerializer

    @extend_schema(responses=s.ComplaintSerializer)
    def post(self, request, pk):
        _active_role(_actor(request), "handler")
        return Response(
            s.ComplaintSerializer(
                services.escalate(complaint_id=pk, actor=_actor(request), kind="manual")
            ).data
        )


class EscalatedComplaintsView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.escalation.monitor")]

    @extend_schema(responses=s.ComplaintSerializer(many=True))
    def get(self, request):
        _active_role(_actor(request), "supervisor")
        qs = Complaint.objects.filter(escalated_at__isnull=False).prefetch_related(
            "attachments", "history", "progress_updates", "reopening_requests"
        )
        return _paginate(request, _apply_filters(qs, request.query_params))


class FeedbackSubmitView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.feedback.submit")]

    @extend_schema(request=s.TextActionSerializer, responses=s.FeedbackSerializer)
    def post(self, request, pk):
        serializer = s.TextActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = services.submit_feedback(
            complaint_id=pk, actor=_actor(request), text=serializer.validated_data["text"]
        )
        return Response(s.FeedbackSerializer(item).data, status=status.HTTP_201_CREATED)


class FeedbackReviewView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.feedback.review")]

    @extend_schema(responses=s.FeedbackSerializer(many=True))
    def get(self, request):
        _active_staff(_actor(request))
        qs = ComplaintFeedback.objects.select_related("complaint").order_by("-created_at", "-id")
        if value := request.query_params.get("complaint_id"):
            qs = qs.filter(complaint_id=value)
        return _paginate(request, qs, s.FeedbackSerializer)


class AnnouncementListCreateView(APIView):
    serializer_class = s.CmsAnnouncementSerializer

    def get_permissions(self):
        return [
            HasModuleGrant("cms")(),
            HasPermission("cms.announcement.view", "cms.announcement.publish")(),
        ]

    @extend_schema(responses=s.CmsAnnouncementSerializer(many=True))
    def get(self, request):
        qs = ComplaintAnnouncement.objects.filter(is_published=True)
        return _paginate(request, qs, s.CmsAnnouncementSerializer)

    @extend_schema(request=s.CmsAnnouncementSerializer, responses=s.CmsAnnouncementSerializer)
    def post(self, request):
        actor = _actor(request)
        _active_staff(actor)
        if not actor.has_permission("cms.announcement.publish"):
            raise PermissionDeniedError()
        serializer = s.CmsAnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = services.publish_announcement(actor=actor, **serializer.validated_data)
        return Response(s.CmsAnnouncementSerializer(item).data, status=status.HTTP_201_CREATED)


class ReportsView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.report.view")]

    @extend_schema(responses=s.CmsReportSerializer)
    def get(self, request):
        actor = _actor(request)
        handler = selectors.has_active_role(actor.user_id, "handler")
        supervisor = selectors.has_active_role(actor.user_id, "supervisor")
        admin = actor.has_permission("cms.role.manage")
        if not (handler or supervisor or admin):
            raise PermissionDeniedError()
        base = Complaint.objects.all()
        if handler and not supervisor:
            base = base.filter(
                Q(assigned_handler_user_id=actor.user_id) | Q(assigned_handler_user_id__isnull=True)
            )
        base = _apply_filters(base, request.query_params)
        # `format` is reserved by DRF's content negotiation query override.
        if request.query_params.get("export") == "csv":
            import csv

            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="cms-complaints.csv"'
            writer = csv.writer(response)
            writer.writerow(
                [
                    "Complaint ID",
                    "Category",
                    "Status",
                    "Priority",
                    "Submitted at",
                    "Assigned handler",
                    "Escalation",
                ]
            )
            for row in base.order_by("created_at", "id").iterator():
                writer.writerow(
                    [
                        row.complaint_id,
                        row.category,
                        row.status,
                        row.priority,
                        row.created_at.isoformat(),
                        row.assigned_handler_user_id or "",
                        row.escalation_kind,
                    ]
                )
            return response
        status_rows = list(base.values("status").annotate(count=Count("id")).order_by("status"))
        priority_rows = list(
            base.values("priority").annotate(count=Count("id")).order_by("priority")
        )
        category_rows = list(
            base.values("category").annotate(count=Count("id")).order_by("category")
        )
        return Response(
            {
                "total": base.count(),
                "by_status": status_rows,
                "by_priority": priority_rows,
                "by_category": category_rows,
                "escalated": base.filter(escalated_at__isnull=False).count(),
                "unresolved": base.filter(status__in=["submitted", "in_progress"]).count(),
                "oldest_unresolved_at": base.filter(status__in=["submitted", "in_progress"])
                .order_by("created_at")
                .values_list("created_at", flat=True)
                .first(),
            }
        )


class RoleAssignmentView(APIView):
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.role.manage")]

    @extend_schema(responses=s.RoleAssignmentSerializer(many=True))
    def get(self, request):
        now = timezone.now()
        rows = CmsRoleAssignment.objects.filter(
            is_active=True, starts_at__lte=now, ends_at__gt=now
        ).order_by("role")
        return Response(s.RoleAssignmentSerializer(rows, many=True).data)

    @extend_schema(request=s.RoleAssignmentSerializer, responses=s.RoleAssignmentSerializer)
    def post(self, request):
        serializer = s.RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = services.assign_role(actor=_actor(request), **serializer.validated_data)
        except IntegrityError as exc:
            raise ConflictError(
                "Another active CMS appointment already exists.", code="active_role_conflict"
            ) from exc
        return Response(s.RoleAssignmentSerializer(item).data, status=status.HTTP_201_CREATED)


def _attach(complaint, upload, actor):
    allowed = set(getattr(settings, "CMS_ATTACHMENT_ALLOWED_EXTENSIONS", ()))
    ext = "." + upload.name.rsplit(".", 1)[-1].lower() if "." in upload.name else ""
    if ext not in allowed:
        raise ConflictError("This attachment type is not allowed.", code="invalid_attachment_type")
    if upload.size > settings.CMS_ATTACHMENT_MAX_BYTES:
        raise ConflictError(
            "Attachment exceeds the configured size limit.", code="attachment_too_large"
        )
    if complaint.attachments.count() >= settings.CMS_ATTACHMENT_MAX_COUNT:
        raise ConflictError("Too many attachments for this complaint.", code="too_many_attachments")
    safe_name = get_valid_filename(upload.name)[:160] or "attachment"
    try:
        key, size = storage.save(upload)
    except storage.CmsStorageError as exc:
        raise ConflictError(str(exc), code="invalid_attachment") from exc
    try:
        return ComplaintAttachment.objects.create(
            complaint=complaint,
            storage_key=key,
            file_name=safe_name,
            content_type=upload.content_type or "application/octet-stream",
            size_bytes=size,
            uploaded_by_user_id=actor.user_id,
        )
    except Exception:
        storage.delete(key)
        raise


class ComplaintAttachmentView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [HasModuleGrant("cms"), HasPermission("cms.complaint.submit")]
    serializer_class = s.ComplaintAttachmentSerializer

    @extend_schema(responses=s.ComplaintAttachmentSerializer(many=True))
    def post(self, request, pk):
        complaint = services.get_complaint(pk)
        if complaint.complainant_user_id != _actor(request).user_id:
            raise NotFoundError("No such complaint.")
        files = request.FILES.getlist("attachments")
        if not files:
            raise ConflictError("Choose at least one attachment.", code="attachment_required")
        made = []
        try:
            for upload in files:
                # Retain each path for cleanup if a later upload fails.
                made.append(_attach(complaint, upload, _actor(request)))  # noqa: PERF401
        except Exception:
            for item in made:
                storage.delete(item.storage_key)
                item.delete()
            raise
        return Response(
            s.ComplaintAttachmentSerializer(made, many=True).data, status=status.HTTP_201_CREATED
        )


class AttachmentDownloadView(APIView):
    permission_classes = [
        HasModuleGrant("cms"),
        HasPermission("cms.complaint.track", "cms.complaint.view"),
    ]

    @extend_schema(responses={200: bytes})
    def get(self, request, pk):
        attachment = ComplaintAttachment.objects.select_related("complaint").filter(pk=pk).first()
        if attachment is None or not _can_read(request, attachment.complaint):
            raise NotFoundError("No such attachment.")
        try:
            stream = storage.open_file(attachment.storage_key)
        except storage.CmsStorageError as exc:
            raise NotFoundError("Attachment is no longer available.") from exc
        response = FileResponse(stream, content_type=attachment.content_type)
        response["Content-Disposition"] = f'attachment; filename="{attachment.file_name}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response
