"""Thin CMS API views; all reads use selectors and all writes use services."""

from urllib.parse import quote

from django.http import FileResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import ConflictError, NotFoundError
from core.api.pagination import CursorPagination
from core.files import storage
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.complaints.api import serializers as s
from modules.complaints.api.query_params import reject_unknown_query_params
from modules.complaints.models import (
    Announcement,
    Complaint,
    ComplaintAttachment,
    Escalation,
    Feedback,
    ReopeningRequest,
)
from modules.complaints.selectors.complaints import (
    assigned_complaints,
    escalated_complaints,
    history,
    own_complaint,
    own_complaints,
)
from modules.complaints.services import complaints as service
from modules.complaints.services.idempotency import post_once

MODULE = HasModuleGrant("complaints")
P_CREATE = "complaints.complaint.create"
P_VIEW = "complaints.complaint.view"
P_FEEDBACK_CREATE = "complaints.feedback.create"
P_ANNOUNCEMENT_VIEW = "complaints.announcement.view"
P_ANNOUNCEMENT_PUBLISH = "complaints.announcement.publish"
P_APPROVE = "complaints.complaint.approve"
P_FEEDBACK_REVIEW = "complaints.feedback.review"
P_ESCALATION_VIEW = "complaints.escalation.view"
P_REPORT_VIEW = "complaints.report.view"
P_ASSIGN = "complaints.complaint.assign"
P_UPDATE = "complaints.complaint.update"


def _actor(request):
    return request.principal


@extend_schema_view(
    get=extend_schema(operation_id="complaints_list", responses=s.ComplaintPageSerializer),
    post=extend_schema(
        operation_id="complaint_submit",
        request=s.ComplaintCreateSerializer,
        responses={status.HTTP_201_CREATED: s.ComplaintSerializer},
    ),
)
class ComplaintListCreateView(APIView):
    serializer_class = s.ComplaintCreateSerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_permissions(self):
        gate = HasPermission(P_CREATE if self.request.method == "POST" else P_VIEW)
        return [MODULE(), gate()]

    def get(self, request):
        reject_unknown_query_params(request)
        rows = own_complaints(user_id=_actor(request).user_id)
        paginator = CursorPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(s.ComplaintSerializer(page, many=True).data)

    def post(self, request):
        payload = s.ComplaintCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        def operation():
            try:
                complaint = service.submit(
                    user_id=_actor(request).user_id, **payload.validated_data
                )
            except service.InvalidSubmission as exc:
                raise ConflictError(str(exc), code="invalid_submission") from exc
            return s.ComplaintSerializer(complaint).data, status.HTTP_201_CREATED

        return post_once(request, operation)


class ComplaintDetailView(APIView):
    serializer_class = s.ComplaintSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(operation_id="complaint_detail", responses=s.ComplaintSerializer)
    def get(self, request, reference):
        reject_unknown_query_params(request, allowed=())
        row = own_complaint(reference=reference, user_id=_actor(request).user_id)
        if row is None:
            raise NotFoundError("No such complaint.")
        return Response(s.ComplaintSerializer(row).data)


class ComplaintHistoryView(APIView):
    serializer_class = s.ComplaintHistorySerializer
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(operation_id="complaint_history", responses=s.HistoryPageSerializer)
    def get(self, request, reference):
        reject_unknown_query_params(request, allowed=())
        row = own_complaint(reference=reference, user_id=_actor(request).user_id)
        if row is None:
            raise NotFoundError("No such complaint.")
        return Response(
            {"results": s.ComplaintHistorySerializer(history(complaint=row), many=True).data}
        )


class ComplaintAttachmentListCreateView(APIView):
    serializer_class = s.AttachmentSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        code = P_CREATE if self.request.method == "POST" else P_VIEW
        return [MODULE(), HasPermission(code)()]

    @extend_schema(operation_id="complaint_attachments", responses=s.AttachmentPageSerializer)
    def get(self, request, reference):
        row = own_complaint(reference=reference, user_id=_actor(request).user_id)
        if row is None:
            row = Complaint.objects.filter(
                reference=reference, assigned_to_user_id=_actor(request).user_id
            ).first()
        if row is None and _actor(request).has_permission(P_ESCALATION_VIEW):
            row = Complaint.objects.filter(reference=reference, escalations__isnull=False).first()
        if row is None and _actor(request).has_permission(P_ASSIGN):
            row = Complaint.objects.filter(
                reference=reference, status__in=("submitted", "in_progress")
            ).first()
        if row is None and _actor(request).has_permission(P_APPROVE):
            row = Complaint.objects.filter(reference=reference, status="resolved").first()
        if row is None:
            raise NotFoundError("No such complaint.")
        attachments = row.attachments.order_by("uploaded_at")
        return Response({"results": s.AttachmentSerializer(attachments, many=True).data})

    @extend_schema(
        operation_id="complaint_attachment_upload",
        request=s.AttachmentUploadSerializer,
        responses={status.HTTP_201_CREATED: s.AttachmentSerializer},
    )
    def post(self, request, reference):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            raise ConflictError("A file is required.", code="attachment_required")
        try:
            row = service.attach_file(
                reference=reference, user_id=_actor(request).user_id, uploaded_file=uploaded_file
            )
        except service.InvalidSubmission as exc:
            raise ConflictError(str(exc), code="attachment_invalid") from exc
        return Response(s.AttachmentSerializer(row).data, status=status.HTTP_201_CREATED)


class ComplaintAttachmentDownloadView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(
        operation_id="complaint_attachment_download", responses={200: OpenApiTypes.BINARY}
    )
    def get(self, request, attachment_id):
        attachment = (
            ComplaintAttachment.objects.select_related("complaint").filter(pk=attachment_id).first()
        )
        if attachment is None:
            raise NotFoundError("No such attachment.")
        actor = _actor(request)
        complaint = attachment.complaint
        can_read = (
            complaint.complainant_user_id == actor.user_id
            or complaint.assigned_to_user_id == actor.user_id
            or (actor.has_permission(P_ESCALATION_VIEW) and complaint.escalations.exists())
            or (actor.has_permission(P_ASSIGN) and complaint.status in ("submitted", "in_progress"))
            or (actor.has_permission(P_APPROVE) and complaint.status == "resolved")
        )
        if not can_read:
            raise NotFoundError("No such attachment.")
        try:
            response = FileResponse(
                storage.open_stream(attachment.storage_key), content_type=attachment.content_type
            )
        except (OSError, storage.StorageError) as exc:
            raise NotFoundError("No such attachment.") from exc
        response["Content-Disposition"] = (
            'attachment; filename="attachment"; '
            f"filename*=UTF-8''{quote(attachment.original_name)}"
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response


class FeedbackCreateView(APIView):
    serializer_class = s.FeedbackCreateSerializer
    permission_classes = [MODULE, HasPermission(P_FEEDBACK_CREATE)]

    @extend_schema(
        operation_id="complaint_feedback_create",
        request=s.FeedbackCreateSerializer,
        responses={status.HTTP_201_CREATED: s.FeedbackSerializer},
    )
    def post(self, request, reference):
        payload = s.FeedbackCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        def operation():
            try:
                feedback = service.submit_feedback(
                    reference=reference,
                    user_id=_actor(request).user_id,
                    message=payload.validated_data["message"],
                )
            except Complaint.DoesNotExist as exc:
                raise NotFoundError("No such complaint.") from exc
            except service.InvalidSubmission as exc:
                raise ConflictError(str(exc), code="feedback_not_eligible") from exc
            return s.FeedbackSerializer(feedback).data, status.HTTP_201_CREATED

        return post_once(request, operation)


class ReopeningRequestCreateView(APIView):
    serializer_class = s.ReopeningCreateSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(
        operation_id="complaint_reopening_request",
        request=s.ReopeningCreateSerializer,
        responses={status.HTTP_201_CREATED: s.ReopeningSerializer},
    )
    def post(self, request, reference):
        payload = s.ReopeningCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        def operation():
            try:
                row = service.request_reopening(
                    reference=reference,
                    user_id=_actor(request).user_id,
                    reason=payload.validated_data["reason"],
                )
            except Complaint.DoesNotExist as exc:
                raise NotFoundError("No such complaint.") from exc
            except service.InvalidSubmission as exc:
                raise ConflictError(str(exc), code="reopening_not_eligible") from exc
            return s.ReopeningSerializer(row).data, status.HTTP_201_CREATED

        return post_once(request, operation)


class AnnouncementListCreateView(APIView):
    serializer_class = s.AnnouncementCreateSerializer

    def get_permissions(self):
        code = P_ANNOUNCEMENT_PUBLISH if self.request.method == "POST" else P_ANNOUNCEMENT_VIEW
        return [MODULE(), HasPermission(code)()]

    @extend_schema(operation_id="complaint_announcements", responses=s.AnnouncementPageSerializer)
    def get(self, request):
        reject_unknown_query_params(request)
        rows = Announcement.objects.filter(is_published=True).order_by("-published_at")
        paginator = CursorPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(s.CMSAnnouncementSerializer(page, many=True).data)

    @extend_schema(
        operation_id="complaint_announcement_publish",
        request=s.AnnouncementCreateSerializer,
        responses={status.HTTP_201_CREATED: s.CMSAnnouncementSerializer},
    )
    def post(self, request):
        payload = s.AnnouncementCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        def operation():
            row = service.publish_announcement(
                actor_user_id=_actor(request).user_id, **payload.validated_data
            )
            return s.CMSAnnouncementSerializer(row).data, status.HTTP_201_CREATED

        return post_once(request, operation)


class UserClosureVerificationView(APIView):
    serializer_class = s.ComplaintSerializer
    permission_classes = [MODULE, HasPermission(P_VIEW)]

    @extend_schema(operation_id="complaint_verify_user", responses=s.ComplaintSerializer)
    def post(self, request, reference):
        try:
            row = service.verify_closure(
                reference=reference, actor_user_id=_actor(request).user_id, actor_kind="complainant"
            )
        except Complaint.DoesNotExist as exc:
            raise NotFoundError("No such complaint.") from exc
        except service.InvalidSubmission as exc:
            raise ConflictError(str(exc), code="closure_not_eligible") from exc
        return Response(s.ComplaintSerializer(row).data)


class SupervisorClosureVerificationView(APIView):
    serializer_class = s.ComplaintSerializer
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    @extend_schema(operation_id="complaint_verify_supervisor", responses=s.ComplaintSerializer)
    def post(self, request, reference):
        try:
            row = service.verify_closure(
                reference=reference, actor_user_id=_actor(request).user_id, actor_kind="supervisor"
            )
        except Complaint.DoesNotExist as exc:
            raise NotFoundError("No such complaint.") from exc
        except service.InvalidSubmission as exc:
            raise ConflictError(str(exc), code="closure_not_eligible") from exc
        return Response(s.ComplaintSerializer(row).data)


class ReopeningDecisionView(APIView):
    serializer_class = s.ReopeningDecisionSerializer
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    @extend_schema(
        operation_id="complaint_reopening_decision",
        request=s.ReopeningDecisionSerializer,
        responses=s.ReopeningSerializer,
    )
    def post(self, request, request_id):
        payload = s.ReopeningDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            row = service.review_reopening(
                request_id=request_id,
                actor_user_id=_actor(request).user_id,
                **payload.validated_data,
            )
        except service.InvalidSubmission as exc:
            raise ConflictError(str(exc), code="bad_reopening_decision") from exc
        return Response(s.ReopeningSerializer(row).data)


class FeedbackReviewView(APIView):
    serializer_class = s.FeedbackReadSerializer
    permission_classes = [MODULE, HasPermission(P_FEEDBACK_REVIEW)]

    @extend_schema(operation_id="complaint_feedback_review", responses=s.FeedbackPageSerializer)
    def get(self, request):
        reject_unknown_query_params(request)
        rows = Feedback.objects.select_related("complaint").order_by("-created_at")
        paginator = CursorPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(s.FeedbackReadSerializer(page, many=True).data)


class EscalationSummaryView(APIView):
    serializer_class = s.EscalationSummarySerializer
    permission_classes = [MODULE, HasPermission(P_ESCALATION_VIEW)]

    @extend_schema(
        operation_id="complaint_escalation_summary", responses=s.EscalationSummarySerializer
    )
    def get(self, request):
        from django.db.models import Count

        rows = Escalation.objects.values("source").annotate(total=Count("id")).order_by("source")
        return Response({"results": list(rows)})


class ComplaintReportView(APIView):
    serializer_class = s.ComplaintReportSerializer
    permission_classes = [MODULE, HasPermission(P_REPORT_VIEW)]

    @extend_schema(operation_id="complaint_report", responses=s.ComplaintReportSerializer)
    def get(self, request):
        from django.db.models import Count

        status_counts = list(
            Complaint.objects.values("status").annotate(total=Count("id")).order_by("status")
        )
        return Response(
            {
                "complaints_by_status": status_counts,
            }
        )


class ReopeningQueueView(APIView):
    serializer_class = s.ReopeningSerializer
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    @extend_schema(operation_id="complaint_reopening_queue", responses=s.ReopeningPageSerializer)
    def get(self, request):
        reject_unknown_query_params(request)
        rows = (
            ReopeningRequest.objects.filter(status="pending")
            .select_related("complaint")
            .order_by("created_at")
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(s.ReopeningSerializer(page, many=True).data)


class PendingClosureView(APIView):
    serializer_class = s.ComplaintSerializer
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    @extend_schema(operation_id="complaint_pending_closures", responses=s.ComplaintPageSerializer)
    def get(self, request):
        reject_unknown_query_params(request)
        rows = (
            Complaint.objects.filter(status="resolved")
            .prefetch_related("history", "feedback", "reopening_requests")
            .order_by("resolved_at")
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(s.ComplaintSerializer(page, many=True).data)


class HandlerQueueView(APIView):
    serializer_class = s.ComplaintPageSerializer
    permission_classes = [MODULE, HasPermission(P_UPDATE)]

    @extend_schema(operation_id="complaints_handler_queue", responses=s.ComplaintPageSerializer)
    def get(self, request):
        reject_unknown_query_params(request)
        rows = assigned_complaints(user_id=_actor(request).user_id)
        paginator = CursorPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(s.ComplaintSerializer(page, many=True).data)


class ComplaintAssignmentView(APIView):
    serializer_class = s.HandlerAssignmentSerializer
    permission_classes = [MODULE, HasPermission(P_ASSIGN)]

    @extend_schema(
        operation_id="complaint_assign_handler",
        request=s.HandlerAssignmentSerializer,
        responses=s.ComplaintSerializer,
    )
    def post(self, request, reference):
        payload = s.HandlerAssignmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            row = service.assign(
                reference=reference,
                actor_user_id=_actor(request).user_id,
                **payload.validated_data,
            )
        except Complaint.DoesNotExist as exc:
            raise NotFoundError("No such complaint.") from exc
        except service.InvalidSubmission as exc:
            raise ConflictError(str(exc), code="assignment_invalid") from exc
        return Response(s.ComplaintSerializer(row).data)


class AssignmentQueueView(APIView):
    serializer_class = s.ComplaintPageSerializer
    permission_classes = [MODULE, HasPermission(P_ASSIGN)]

    @extend_schema(operation_id="complaints_assignment_queue", responses=s.ComplaintPageSerializer)
    def get(self, request):
        reject_unknown_query_params(request)
        rows = Complaint.objects.filter(status__in=("submitted", "in_progress")).order_by(
            "sla_due_at", "submitted_at"
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(s.ComplaintSerializer(page, many=True).data)


class HandlerOptionsView(APIView):
    serializer_class = s.HandlerOptionSerializer
    permission_classes = [MODULE, HasPermission(P_ASSIGN)]

    @extend_schema(
        operation_id="complaints_handler_options", responses=s.HandlerOptionSerializer(many=True)
    )
    def get(self, request):
        from modules.directory import contracts as directory

        return Response(s.HandlerOptionSerializer(directory.get_employees(), many=True).data)


class ComplaintProgressView(APIView):
    serializer_class = s.ProgressSerializer
    permission_classes = [MODULE, HasPermission(P_UPDATE)]

    @extend_schema(
        operation_id="complaint_progress",
        request=s.ProgressSerializer,
        responses=s.ComplaintSerializer,
    )
    def post(self, request, reference):
        payload = s.ProgressSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            row = service.add_progress(
                reference=reference,
                actor_user_id=_actor(request).user_id,
                **payload.validated_data,
            )
        except Complaint.DoesNotExist as exc:
            raise NotFoundError("No such complaint.") from exc
        except service.InvalidSubmission as exc:
            raise ConflictError(str(exc), code="progress_invalid") from exc
        return Response(s.ComplaintSerializer(row).data)


class ComplaintResolveView(APIView):
    serializer_class = s.ResolutionSerializer
    permission_classes = [MODULE, HasPermission(P_UPDATE)]

    @extend_schema(
        operation_id="complaint_resolve",
        request=s.ResolutionSerializer,
        responses=s.ComplaintSerializer,
    )
    def post(self, request, reference):
        payload = s.ResolutionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            row = service.resolve(
                reference=reference,
                actor_user_id=_actor(request).user_id,
                **payload.validated_data,
            )
        except Complaint.DoesNotExist as exc:
            raise NotFoundError("No such complaint.") from exc
        except service.InvalidSubmission as exc:
            raise ConflictError(str(exc), code="resolution_invalid") from exc
        return Response(s.ComplaintSerializer(row).data)


class ComplaintRejectView(APIView):
    serializer_class = s.RejectionSerializer
    permission_classes = [MODULE, HasPermission(P_UPDATE)]

    @extend_schema(
        operation_id="complaint_reject",
        request=s.RejectionSerializer,
        responses=s.ComplaintSerializer,
    )
    def post(self, request, reference):
        payload = s.RejectionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            row = service.reject(
                reference=reference,
                actor_user_id=_actor(request).user_id,
                **payload.validated_data,
            )
        except Complaint.DoesNotExist as exc:
            raise NotFoundError("No such complaint.") from exc
        except service.InvalidSubmission as exc:
            raise ConflictError(str(exc), code="rejection_invalid") from exc
        return Response(s.ComplaintSerializer(row).data)


class ComplaintManualEscalationView(APIView):
    serializer_class = s.RejectionSerializer
    permission_classes = [MODULE, HasPermission(P_UPDATE)]

    @extend_schema(
        operation_id="complaint_manual_escalate",
        request=s.RejectionSerializer,
        responses=s.EscalationSerializer,
    )
    def post(self, request, reference):
        payload = s.RejectionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            row = service.escalate_manual(
                reference=reference,
                actor_user_id=_actor(request).user_id,
                reason=payload.validated_data["reason"],
            )
        except Complaint.DoesNotExist as exc:
            raise NotFoundError("No such complaint.") from exc
        except service.InvalidSubmission as exc:
            raise ConflictError(str(exc), code="escalation_invalid") from exc
        return Response(
            {
                "reference": row.complaint.reference,
                "source": row.source,
                "reason": row.reason,
                "escalated_at": row.escalated_at,
            },
            status=status.HTTP_201_CREATED,
        )


class EscalatedQueueView(APIView):
    serializer_class = s.ComplaintPageSerializer
    permission_classes = [MODULE, HasPermission(P_ESCALATION_VIEW)]

    @extend_schema(operation_id="complaints_escalated_queue", responses=s.ComplaintPageSerializer)
    def get(self, request):
        reject_unknown_query_params(request)
        rows = escalated_complaints()
        paginator = CursorPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(s.ComplaintSerializer(page, many=True).data)
