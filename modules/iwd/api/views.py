from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.iwd import services
from modules.iwd.api.serializers import (
    ActionSerializer,
    AuditSerializer,
    ComplaintSerializer,
    ComplaintWriteSerializer,
    EstimateSerializer,
)
from modules.iwd.models import (
    IwdAuditEvent,
    IwdComplaint,
    IwdEstimate,
    IwdFeedback,
    IwdFinalBill,
    IwdProcurementNeed,
)

MODULE = HasModuleGrant("iwd")
VIEW = HasPermission("iwd.complaint.view")


def actor(request):
    return request.principal


def get_complaint(pk, principal):
    queryset = IwdComplaint.objects.filter(pk=pk)
    if not principal.has_permission("iwd.workflow.review"):
        queryset = queryset.filter(
            Q(reporter_user_id=principal.user_id) | Q(engineer_user_id=principal.user_id)
        )
    row = queryset.first()
    if not row:
        raise NotFoundError("No such IWD complaint.")
    return row


class ComplaintListCreateView(generics.ListCreateAPIView):
    permission_classes = [MODULE, VIEW]
    serializer_class = ComplaintSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return IwdComplaint.objects.none()
        p = actor(self.request)
        if p.has_permission("iwd.workflow.review"):
            return IwdComplaint.objects.all().order_by("-created_at")
        return IwdComplaint.objects.filter(
            Q(reporter_user_id=p.user_id) | Q(engineer_user_id=p.user_id)
        ).order_by("-created_at")

    def create(self, request, *args, **kwargs):
        if not actor(request).has_permission("iwd.complaint.submit"):
            return Response({"detail": "Complaint submission is not permitted."}, status=403)
        payload = ComplaintWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            row = services.submit_complaint(actor=actor(request), **payload.validated_data)
        except ValueError as exc:
            raise BadRequestError(str(exc), code="iwd_submit") from exc
        return Response(ComplaintSerializer(row).data, status=status.HTTP_201_CREATED)


class ComplaintDetailView(generics.RetrieveAPIView):
    permission_classes = [MODULE, VIEW]
    serializer_class = ComplaintSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return IwdComplaint.objects.none()
        p = actor(self.request)
        if p.has_permission("iwd.workflow.review"):
            return IwdComplaint.objects.all()
        return IwdComplaint.objects.filter(
            Q(reporter_user_id=p.user_id) | Q(engineer_user_id=p.user_id)
        )


class ComplaintActionView(APIView):
    permission_classes = [MODULE, VIEW]

    def post(self, request, pk, action):
        p = actor(request)
        row = get_complaint(pk, p)
        permissions = {
            "assess": "iwd.complaint.assess",
            "estimate": "iwd.estimate.submit",
            "decide": "iwd.workflow.review",
            "committee": "iwd.workflow.review",
            "urgent": "iwd.complaint.assess",
            "urgent-review": "iwd.workflow.review",
            "stock": "iwd.workflow.review",
            "procurement": "iwd.workflow.review",
            "execute": "iwd.complaint.assess",
            "verify": "iwd.workflow.review",
            "bill": "iwd.estimate.submit",
            "audit": "iwd.workflow.review",
            "payment": "iwd.workflow.review",
            "settlement": "iwd.workflow.review",
            "feedback": "iwd.complaint.submit",
            "resubmit": "iwd.estimate.submit",
        }
        permission = permissions.get(action)
        if not permission:
            raise NotFoundError("Unknown IWD action.")
        if not p.has_permission(permission):
            return Response({"detail": "This active role cannot perform the action."}, status=403)
        payload = ActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        try:
            if action == "assess":
                result = services.assess(
                    complaint=row,
                    actor=p,
                    assessment=data.get("assessment"),
                    needs_site_information=data.get("needs_site_information", False),
                )
            elif action == "estimate":
                result = services.estimate(
                    complaint=row,
                    actor=p,
                    total_cost=data.get("total_cost"),
                    details=data.get("details"),
                    estimated_time=data.get("estimated_time", ""),
                    materials=data.get("materials"),
                )
            elif action == "decide":
                result = services.decide(
                    complaint=row,
                    actor=p,
                    outcome=data.get("outcome"),
                    reason=data.get("reason", ""),
                )
            elif action == "committee":
                result = services.committee_review(
                    complaint=row, actor=p, outcome=data.get("outcome")
                )
            elif action == "urgent":
                result = services.flag_urgent(
                    complaint=row, actor=p, remarks=data.get("remarks", "")
                )
            elif action == "urgent-review":
                result = services.review_urgent(
                    complaint=row,
                    actor=p,
                    accepted=data.get("accepted", False),
                    remarks=data.get("remarks", ""),
                )
            elif action == "stock":
                result = services.check_stock(
                    complaint=row, actor=p, materials=data.get("materials", [])
                )
            elif action == "procurement":
                need = row.procurement_needs.order_by("-created_at").first()
                if need is None:
                    raise BadRequestError(
                        "No procurement need exists.", code="iwd_procurement_missing"
                    )
                result = services.complete_procurement(
                    need=need, actor=p, remarks=data.get("remarks", "")
                )
            elif action == "execute":
                result = services.execute_work(
                    complaint=row,
                    actor=p,
                    progress=data.get("progress", ""),
                    materials_used=data.get("materials"),
                    complete=data.get("complete", False),
                )
            elif action == "verify":
                result = services.verify_work(
                    complaint=row,
                    actor=p,
                    outcome=data.get("outcome"),
                    remarks=data.get("remarks", ""),
                )
            elif action == "bill":
                result = services.submit_bill(
                    complaint=row,
                    actor=p,
                    invoice_number=data.get("invoice_number", ""),
                    amount=data.get("amount"),
                    supporting_records=data.get("supporting_records"),
                )
            elif action == "audit":
                result = services.audit_bill(
                    bill=row.final_bill,
                    actor=p,
                    outcome=data.get("outcome"),
                    remarks=data.get("remarks", ""),
                )
            elif action == "payment":
                result = services.approve_payment(
                    bill=row.final_bill,
                    actor=p,
                    approved=data.get("approved", False),
                    reason=data.get("reason", ""),
                )
            elif action == "settlement":
                result = services.record_settlement(
                    bill=row.final_bill, actor=p, status=data.get("status", "")
                )
            elif action == "feedback":
                result = services.submit_feedback(
                    complaint=row,
                    actor=p,
                    rating=data.get("rating"),
                    comments=data.get("comments", ""),
                    post_repair_issue=data.get("post_repair_issue", ""),
                )
            else:
                result = services.modify_and_resubmit(
                    complaint=row,
                    actor=p,
                    total_cost=data.get("total_cost"),
                    details=data.get("details"),
                )
        except (TypeError, ValueError) as exc:
            raise BadRequestError(str(exc), code="iwd_action") from exc
        if isinstance(result, IwdEstimate):
            body = EstimateSerializer(result).data
        elif isinstance(result, IwdAuditEvent):
            body = AuditSerializer(result).data
        elif isinstance(result, IwdFinalBill):
            body = {"id": result.id, "state": result.state, "complaint_id": result.complaint_id}
        elif isinstance(result, IwdFeedback):
            body = {"id": result.id, "complaint_id": result.complaint_id, "rating": result.rating}
        elif isinstance(result, IwdProcurementNeed):
            body = {"id": result.id, "state": result.state, "complaint_id": result.complaint_id}
        else:
            body = ComplaintSerializer(result).data
        return Response(body)


class AuditListView(generics.ListAPIView):
    permission_classes = [MODULE, VIEW]
    serializer_class = AuditSerializer

    def get_queryset(self):
        p = actor(self.request)
        complaints = IwdComplaint.objects.all()
        if not p.has_permission("iwd.workflow.review"):
            complaints = complaints.filter(
                Q(reporter_user_id=p.user_id) | Q(engineer_user_id=p.user_id)
            )
        return IwdAuditEvent.objects.filter(
            complaint_id=self.kwargs["pk"], complaint__in=complaints
        ).order_by("created_at")
