from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.hreis.api.schema_helpers import ApprovalQueueSerializer
from modules.hreis.api.serializers import (
    AppraisalSerializer,
    AppraisalWindowSerializer,
    AuditEntrySerializer,
    ClaimSerializer,
    EmployeeRecordSerializer,
    LeaveRequestSerializer,
    NotificationSerializer,
    WorkflowRouteSerializer,
)
from modules.hreis.models import (
    Appraisal,
    AppraisalWindow,
    AuditEntry,
    Claim,
    EmployeeRecord,
    LeaveRequest,
    Notification,
    WorkflowRoute,
)
from modules.hreis.services import workflow as svc

MODULE = HasModuleGrant("hreis")
SELF = HasPermission("hreis.record.view_self")
HR = HasPermission("hreis.record.manage")
AUTHORITY = HasPermission(
    "hreis.leave.review",
    "hreis.claim.review",
    "hreis.claim.verify",
    "hreis.claim.process",
    "hreis.appraisal.assign",
    "hreis.appraisal.review",
)


def me(request):
    return request.principal


def own_record(request):
    return get_object_or_404(EmployeeRecord, user_id=me(request).user_id)


class MyRecordView(GenericAPIView):
    serializer_class = EmployeeRecordSerializer
    permission_classes = [MODULE, SELF]

    def get(self, request):
        return Response(EmployeeRecordSerializer(own_record(request)).data)


class RecordAdminView(GenericAPIView):
    serializer_class = EmployeeRecordSerializer
    permission_classes = [MODULE, HR]

    def get(self, request):
        rows = EmployeeRecord.objects.order_by("user_id")[:100]
        return Response({"results": EmployeeRecordSerializer(rows, many=True).data})

    def post(self, request):
        form = EmployeeRecordSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        record = svc.save_record(form.validated_data, me(request))
        return Response(EmployeeRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class RecordAdminDetailView(GenericAPIView):
    serializer_class = EmployeeRecordSerializer
    permission_classes = [MODULE, HR]

    def put(self, request, user_id):
        record = get_object_or_404(EmployeeRecord, user_id=user_id)
        form = EmployeeRecordSerializer(record, data=request.data, partial=True)
        form.is_valid(raise_exception=True)
        record = svc.save_record(form.validated_data, me(request), user_id=user_id)
        return Response(EmployeeRecordSerializer(record).data)


class LeaveListView(GenericAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [MODULE, HasPermission("hreis.leave.apply")]

    def get(self, request):
        rows = LeaveRequest.objects.filter(record__user_id=me(request).user_id).order_by(
            "-created_at"
        )[:100]
        return Response({"results": LeaveRequestSerializer(rows, many=True).data})

    def post(self, request):
        form = LeaveRequestSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        row = svc.submit_leave(own_record(request), form.validated_data, me(request))
        return Response(LeaveRequestSerializer(row).data, status=status.HTTP_201_CREATED)


class LeaveDecisionView(GenericAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [MODULE, HasPermission("hreis.leave.review")]

    def post(self, request, pk):
        get_object_or_404(LeaveRequest, pk=pk)
        row = svc.decide_leave(pk, request.data.get("outcome"), me(request))
        return Response(LeaveRequestSerializer(row).data)


class AppraisalListView(GenericAPIView):
    serializer_class = AppraisalSerializer
    permission_classes = [MODULE, HasPermission("hreis.appraisal.submit")]

    def get(self, request):
        rows = Appraisal.objects.filter(record__user_id=me(request).user_id).order_by(
            "-submitted_at"
        )[:100]
        return Response({"results": AppraisalSerializer(rows, many=True).data})

    def post(self, request):
        form = AppraisalSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        obj = svc.submit_appraisal(own_record(request), form.validated_data, me(request))
        return Response(AppraisalSerializer(obj).data, status=status.HTTP_201_CREATED)


class AppraisalAssignView(GenericAPIView):
    serializer_class = AppraisalSerializer
    permission_classes = [MODULE, HasPermission("hreis.appraisal.assign")]

    def post(self, request, pk):
        get_object_or_404(Appraisal, pk=pk)
        obj = svc.assign_appraisal(pk, request.data.get("reviewer_roles"), me(request))
        return Response(AppraisalSerializer(obj).data)


class AppraisalReviewView(GenericAPIView):
    serializer_class = AppraisalSerializer
    permission_classes = [MODULE, HasPermission("hreis.appraisal.review")]

    def post(self, request, pk):
        get_object_or_404(Appraisal, pk=pk)
        obj = svc.review_appraisal(pk, me(request))
        return Response(AppraisalSerializer(obj).data)


class ClaimListView(GenericAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [MODULE, HasPermission("hreis.claim.submit")]

    def get(self, request):
        rows = Claim.objects.filter(record__user_id=me(request).user_id).order_by("-submitted_at")[
            :100
        ]
        return Response({"results": ClaimSerializer(rows, many=True).data})

    def post(self, request):
        form = ClaimSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        obj = svc.submit_claim(own_record(request), form.validated_data, me(request))
        return Response(ClaimSerializer(obj).data, status=status.HTTP_201_CREATED)


class ClaimVerifyView(GenericAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [MODULE, HasPermission("hreis.claim.verify")]

    def post(self, request, pk):
        get_object_or_404(Claim, pk=pk)
        obj = svc.verify_claim(
            pk, me(request), request.data.get("documents_verified"), request.data.get("eligible")
        )
        return Response(ClaimSerializer(obj).data)


class ClaimDecisionView(GenericAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [MODULE, HasPermission("hreis.claim.review")]

    def post(self, request, pk):
        get_object_or_404(Claim, pk=pk)
        obj = svc.decide_claim(pk, request.data.get("outcome"), me(request))
        return Response(ClaimSerializer(obj).data)


class ClaimProcessView(GenericAPIView):
    serializer_class = ClaimSerializer
    permission_classes = [MODULE, HasPermission("hreis.claim.process")]

    def post(self, request, pk):
        get_object_or_404(Claim, pk=pk)
        obj = svc.process_claim(
            pk,
            request.data.get("payment_status"),
            request.data.get("payment_reference"),
            me(request),
        )
        return Response(ClaimSerializer(obj).data)


class ApprovalQueueView(GenericAPIView):
    serializer_class = ApprovalQueueSerializer
    permission_classes = [MODULE, AUTHORITY]

    def get(self, request):
        principal = me(request)
        can = principal.has_permission
        role = principal.active_role
        leaves = []
        claims = []
        appraisals = []
        if can("hreis.leave.review"):
            for item in LeaveRequest.objects.filter(status="pending").select_related("record")[
                :200
            ]:
                route = item.approval_roles
                if item.current_step < len(route) and route[item.current_step] == role:
                    leaves.append(LeaveRequestSerializer(item).data)
        for item in Claim.objects.filter(
            status__in=("awaiting_hr", "pending", "approved")
        ).select_related("record")[:200]:
            if (item.status == "awaiting_hr" and can("hreis.claim.verify")) or (
                item.status == "approved" and can("hreis.claim.process")
            ):
                claims.append(ClaimSerializer(item).data)
            elif item.status == "pending" and can("hreis.claim.review"):
                route = item.approval_roles
                if item.current_step < len(route) and route[item.current_step] == role:
                    claims.append(ClaimSerializer(item).data)
        if can("hreis.appraisal.assign"):
            appraisals.extend(
                AppraisalSerializer(item).data
                for item in Appraisal.objects.filter(status="submitted")[:200]
            )
        if can("hreis.appraisal.review"):
            appraisals.extend(
                AppraisalSerializer(item).data
                for item in Appraisal.objects.filter(status="review")[:200]
                if item.current_step < len(item.reviewer_roles)
                and item.reviewer_roles[item.current_step] == role
            )
        return Response({"leave": leaves, "claims": claims, "appraisals": appraisals})


class RoutesAdminView(GenericAPIView):
    serializer_class = WorkflowRouteSerializer
    permission_classes = [MODULE, HasPermission("hreis.workflow.configure")]

    def get(self, request):
        return Response(
            {
                "results": WorkflowRouteSerializer(
                    WorkflowRoute.objects.order_by("category", "request_kind"), many=True
                ).data
            }
        )

    @transaction.atomic
    def post(self, request):
        existing = WorkflowRoute.objects.filter(
            category=request.data.get("category"), request_kind=request.data.get("request_kind")
        ).first()
        form = WorkflowRouteSerializer(instance=existing, data=request.data)
        form.is_valid(raise_exception=True)
        validated = form.validated_data
        obj, created = WorkflowRoute.objects.update_or_create(
            category=validated["category"],
            request_kind=validated["request_kind"],
            defaults={"authorities": validated["authorities"]},
        )
        svc.record_event(
            obj,
            "route_created" if created else "route_updated",
            me(request),
            {"authorities": obj.authorities},
        )
        return Response(WorkflowRouteSerializer(obj).data)


class WindowsAdminView(GenericAPIView):
    serializer_class = AppraisalWindowSerializer
    permission_classes = [MODULE, HasPermission("hreis.workflow.configure")]

    def get(self, request):
        return Response(
            {
                "results": AppraisalWindowSerializer(
                    AppraisalWindow.objects.order_by("-year"), many=True
                ).data
            }
        )

    @transaction.atomic
    def post(self, request):
        existing = AppraisalWindow.objects.filter(year=request.data.get("year")).first()
        form = AppraisalWindowSerializer(instance=existing, data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data
        obj, created = AppraisalWindow.objects.update_or_create(
            year=data["year"],
            defaults={"opens_at": data["opens_at"], "closes_at": data["closes_at"]},
        )
        svc.record_event(obj, "window_created" if created else "window_updated", me(request))
        return Response(AppraisalWindowSerializer(obj).data)


class AuditView(GenericAPIView):
    serializer_class = AuditEntrySerializer
    permission_classes = [MODULE, HasPermission("hreis.audit.view")]

    def get(self, request):
        return Response(
            {"results": AuditEntrySerializer(AuditEntry.objects.all()[:100], many=True).data}
        )


class NotificationsView(GenericAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [MODULE, HasPermission("hreis.notification.view")]

    def get(self, request):
        rows = Notification.objects.filter(user_id=me(request).user_id).order_by("-created_at")[
            :100
        ]
        return Response({"results": NotificationSerializer(rows, many=True).data})


class ReadNotificationView(GenericAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [MODULE, HasPermission("hreis.notification.view")]

    def post(self, request, pk):
        obj = get_object_or_404(Notification, pk=pk, user_id=me(request).user_id)
        if obj.read_at is None:
            obj.read_at = timezone.now()
            obj.save(update_fields=["read_at"])
            svc.record_event(obj, "notification_read", me(request))
        return Response(NotificationSerializer(obj).data)


class PolicyNotificationView(GenericAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [MODULE, HasPermission("hreis.notification.manage")]

    @transaction.atomic
    def post(self, request):
        message = request.data.get("message", "")
        if not isinstance(message, str) or not message.strip():
            raise ValidationError({"message": "A notification message is required."})
        try:
            user_id = int(request.data.get("user_id"))
        except (TypeError, ValueError) as exc:
            raise ValidationError({"user_id": "A valid recipient is required."}) from exc
        obj = svc.notify(user_id, "policy", message)
        svc.record_event(obj, "policy_notification_created", me(request))
        return Response(NotificationSerializer(obj).data, status=status.HTTP_201_CREATED)
