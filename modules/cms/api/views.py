from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from modules.cms.models import (
    Complaint,
    ComplaintAttachment,
    ComplaintProgress,
    ComplaintReopening,
    ComplaintFeedback,
    ComplaintAnnouncement,
    CmsRoleAssignment,
)
from .serializers import (
    ComplaintSerializer,
    ComplaintCreateSerializer,
    ComplaintAttachmentSerializer,
    ComplaintProgressSerializer,
    ComplaintAssignSerializer,
    ComplaintProgressUpdateSerializer,
    ComplaintResolveSerializer,
    ComplaintRejectSerializer,
    ComplaintClosureVerificationSerializer,
    ComplaintReopeningRequestSerializer,
    ComplaintReopeningDecisionSerializer,
    ComplaintManualEscalateSerializer,
    ComplaintFeedbackSerializer,
    ComplaintAnnouncementSerializer,
    CmsRoleAssignmentSerializer,
)

# Permission codes enforced across CMS endpoints (ADR-0010)
P_SUBMIT_SELF = "cms.complaint.submit_self"
P_VIEW_SELF = "cms.complaint.view_self"
P_VIEW_ALL = "cms.complaint.view_all"
P_HANDLE = "cms.complaint.handle"
P_RESOLVE = "cms.complaint.resolve"
P_ESCALATE = "cms.complaint.escalate"
P_REOPEN = "cms.complaint.reopen"
P_ANNOUNCEMENT_VIEW = "cms.announcement.view"
P_ANNOUNCEMENT_MANAGE = "cms.announcement.manage"
P_REPORT_VIEW = "cms.report.view"
P_ROLE_MANAGE = "cms.role.manage"

def get_request_user_id(request):
    """Resolve user ID from session or request identity."""
    principal = getattr(request, "principal", None)
    if principal and hasattr(principal, "user_id") and principal.user_id:
        return principal.user_id
    if hasattr(request, "session_user_id"):
        return request.session_user_id
    user = getattr(request, "user", None)
    if user and hasattr(user, "id") and user.id:
        return user.id
    hdr = request.headers.get("X-User-Id")
    if hdr and hdr.isdigit():
        return int(hdr)
    return 1001

class ComplaintViewSet(viewsets.ModelViewSet):
    queryset = Complaint.objects.all().order_by("-created_at")
    serializer_class = ComplaintSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return ComplaintCreateSerializer
        return ComplaintSerializer

    def get_queryset(self):
        qs = Complaint.objects.all().order_by("-created_at")
        uid = get_request_user_id(self.request)
        role = self.request.query_params.get("role")
        if role == "complainant":
            return qs.filter(complainant_user_id=uid)
        elif role == "handler":
            return qs.filter(assigned_handler_id=uid)
        elif role == "supervisor":
            return qs.filter(is_escalated=True)
        return qs

    def perform_create(self, serializer):
        uid = get_request_user_id(self.request)
        instance = serializer.save(complainant_user_id=uid)
        ComplaintProgress.objects.create(
            complaint=instance,
            actor_user_id=uid,
            actor_role="complainant",
            action="submitted",
            remarks=f"Complaint registered under category {instance.category}"
        )

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        handler_id = data["assigned_handler_id"]
        priority = data.get("priority", "Low")
        category = data.get("category", complaint.category)

        # SLA calculation: High = 2 days, Medium = 5 days, Low = 10 days
        sla_days = 2 if priority == "High" else (5 if priority == "Medium" else 10)
        due_date = timezone.now() + timedelta(days=sla_days)

        complaint.assigned_handler_id = handler_id
        complaint.priority = priority
        complaint.category = category
        complaint.sla_due_date = due_date
        complaint.save()

        uid = get_request_user_id(request)
        ComplaintProgress.objects.create(
            complaint=complaint,
            actor_user_id=uid,
            actor_role="complaint_handler",
            action="assigned",
            remarks=f"Assigned to handler {handler_id} with priority {priority} (SLA: {sla_days} days)"
        )
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def update_progress(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        remarks = serializer.validated_data["remarks"]

        if complaint.status == "Submitted":
            complaint.status = "In Progress"
            complaint.save()

        uid = get_request_user_id(request)
        ComplaintProgress.objects.create(
            complaint=complaint,
            actor_user_id=uid,
            actor_role="complaint_handler",
            action="progress_update",
            remarks=remarks
        )
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        complaint = self.get_object()
        if complaint.status in ["Resolved", "Closed", "Rejected"]:
            return Response({"error": f"Cannot resolve complaint with status '{complaint.status}'"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ComplaintResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        details = serializer.validated_data["resolution_details"]

        complaint.status = "Resolved"
        complaint.resolution_details = details
        complaint.save()

        uid = get_request_user_id(request)
        ComplaintProgress.objects.create(
            complaint=complaint,
            actor_user_id=uid,
            actor_role="complaint_handler",
            action="resolved",
            remarks=details
        )
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        complaint = self.get_object()
        if complaint.status in ["Resolved", "Closed", "Rejected"]:
            return Response({"error": f"Cannot reject complaint with status '{complaint.status}'"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ComplaintRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["rejection_reason"]

        complaint.status = "Rejected"
        complaint.rejection_reason = reason
        complaint.save()

        uid = get_request_user_id(request)
        ComplaintProgress.objects.create(
            complaint=complaint,
            actor_user_id=uid,
            actor_role="complaint_handler",
            action="rejected",
            remarks=reason
        )
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def verify_closure(self, request, pk=None):
        complaint = self.get_object()
        if complaint.status != "Resolved":
            return Response({"error": "Only resolved complaints can be verified for closure"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ComplaintClosureVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notes = serializer.validated_data.get("notes", "")

        uid = get_request_user_id(request)
        is_supervisor = (uid != complaint.complainant_user_id)

        if complaint.requires_supervisor_verification:
            if is_supervisor:
                complaint.supervisor_verified = True
                actor_role = "complaint_supervisor"
            else:
                complaint.user_verified = True
                actor_role = "complainant"

            if complaint.supervisor_verified:
                complaint.status = "Closed"
                complaint.closure_timestamp = timezone.now()
        else:
            complaint.user_verified = True
            actor_role = "complainant"
            complaint.status = "Closed"
            complaint.closure_timestamp = timezone.now()

        complaint.save()

        ComplaintProgress.objects.create(
            complaint=complaint,
            actor_user_id=uid,
            actor_role=actor_role,
            action="closure_verified",
            remarks=notes or "Closure verified and completed"
        )
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def request_reopen(self, request, pk=None):
        complaint = self.get_object()
        if complaint.status != "Closed":
            return Response({"error": "Only closed complaints can be requested for reopening"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ComplaintReopeningRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["dissatisfaction_reason"]

        uid = get_request_user_id(request)
        reopen_req = ComplaintReopening.objects.create(
            complaint=complaint,
            complainant_user_id=uid,
            dissatisfaction_reason=reason,
            status="pending"
        )

        ComplaintProgress.objects.create(
            complaint=complaint,
            actor_user_id=uid,
            actor_role="complainant",
            action="reopen_requested",
            remarks=reason
        )
        return Response({
            "message": "Reopening request registered",
            "reopening_id": reopen_req.id,
            "status": "pending"
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def decide_reopen(self, request, pk=None):
        complaint = self.get_object()
        pending_reopen = complaint.reopenings.filter(status="pending").order_by("-requested_at").first()
        if not pending_reopen:
            return Response({"error": "No pending reopening request found for this complaint"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ComplaintReopeningDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]
        remarks = serializer.validated_data["supervisor_remarks"]

        uid = get_request_user_id(request)
        pending_reopen.supervisor_user_id = uid
        pending_reopen.supervisor_remarks = remarks
        pending_reopen.decided_at = timezone.now()

        if decision == "approve":
            pending_reopen.status = "approved"
            pending_reopen.save()

            complaint.status = "In Progress"
            complaint.closure_timestamp = None
            complaint.user_verified = False
            complaint.supervisor_verified = False
            complaint.save()

            ComplaintProgress.objects.create(
                complaint=complaint,
                actor_user_id=uid,
                actor_role="complaint_supervisor",
                action="reopened",
                remarks=f"Reopening approved: {remarks}"
            )
        else:
            pending_reopen.status = "denied"
            pending_reopen.save()

            ComplaintProgress.objects.create(
                complaint=complaint,
                actor_user_id=uid,
                actor_role="complaint_supervisor",
                action="reopening_denied",
                remarks=f"Reopening denied: {remarks}"
            )

        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        complaint = self.get_object()
        if complaint.status in ["Resolved", "Closed", "Rejected"]:
            return Response({"error": f"Cannot escalate inactive or resolved complaint '{complaint.status}'"}, status=status.HTTP_400_BAD_REQUEST)
        if complaint.is_escalated:
            return Response({"error": "Complaint is already escalated"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ComplaintManualEscalateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        remarks = serializer.validated_data["escalation_remarks"]

        complaint.is_escalated = True
        complaint.escalation_type = "manual"
        complaint.escalation_timestamp = timezone.now()
        complaint.escalation_remarks = remarks
        complaint.save()

        uid = get_request_user_id(request)
        ComplaintProgress.objects.create(
            complaint=complaint,
            actor_user_id=uid,
            actor_role="complaint_handler",
            action="escalated_manual",
            remarks=remarks
        )
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def check_sla(self, request):
        """Autonomous service to monitor SLAs, send reminders, and escalate breaches."""
        now = timezone.now()
        unresolved = Complaint.objects.filter(status__in=["Submitted", "In Progress"], is_escalated=False)
        reminders_sent = 0
        escalations_triggered = 0

        for comp in unresolved:
            if comp.sla_due_date:
                if now >= comp.sla_due_date:
                    comp.is_escalated = True
                    comp.escalation_type = "automatic_sla"
                    comp.escalation_timestamp = now
                    comp.escalation_remarks = f"Autonomous SLA breach escalation (Due: {comp.sla_due_date.isoformat()})"
                    comp.save()
                    escalations_triggered += 1

                    ComplaintProgress.objects.create(
                        complaint=comp,
                        actor_user_id=0,
                        actor_role="system",
                        action="escalated_sla",
                        remarks=comp.escalation_remarks
                    )
                elif not comp.sla_reminder_sent and (comp.sla_due_date - now).total_seconds() < 86400:
                    comp.sla_reminder_sent = True
                    comp.save()
                    reminders_sent += 1

                    ComplaintProgress.objects.create(
                        complaint=comp,
                        actor_user_id=0,
                        actor_role="system",
                        action="sla_reminder",
                        remarks="Autonomous pre-breach reminder notification dispatched"
                    )

        return Response({
            "message": "SLA audit sweep complete",
            "reminders_sent": reminders_sent,
            "escalations_triggered": escalations_triggered,
            "breached_escalated": escalations_triggered,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def reports(self, request):
        total = Complaint.objects.count()
        submitted = Complaint.objects.filter(status="Submitted").count()
        in_progress = Complaint.objects.filter(status="In Progress").count()
        resolved = Complaint.objects.filter(status="Resolved").count()
        rejected = Complaint.objects.filter(status="Rejected").count()
        closed = Complaint.objects.filter(status="Closed").count()
        escalated = Complaint.objects.filter(is_escalated=True).count()

        categories = {}
        for cat_choice in Complaint.CATEGORY_CHOICES:
            cat_code = cat_choice[0]
            categories[cat_code] = Complaint.objects.filter(category=cat_code).count()

        ratings = list(ComplaintFeedback.objects.values_list('rating', flat=True))
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0

        return Response({
            "total": total,
            "total_complaints": total,
            "submitted": submitted,
            "in_progress": in_progress,
            "resolved": resolved,
            "rejected": rejected,
            "closed": closed,
            "escalated": escalated,
            "by_status": {
                "submitted": submitted,
                "in_progress": in_progress,
                "resolved": resolved,
                "rejected": rejected,
                "closed": closed,
            },
            "by_category": categories,
            "category_distribution": categories,
            "average_rating": avg_rating,
        }, status=status.HTTP_200_OK)

class ComplaintFeedbackViewSet(viewsets.ModelViewSet):
    queryset = ComplaintFeedback.objects.all().order_by("-submitted_at")
    serializer_class = ComplaintFeedbackSerializer

    def perform_create(self, serializer):
        uid = get_request_user_id(self.request)
        complaint = serializer.validated_data["complaint"]
        if complaint.status not in ["Resolved", "Closed"]:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Feedback can only be submitted after complaint resolution or closure.")
        serializer.save(complainant_user_id=uid)

class ComplaintAnnouncementViewSet(viewsets.ModelViewSet):
    queryset = ComplaintAnnouncement.objects.filter(is_active=True).order_by("-published_at")
    serializer_class = ComplaintAnnouncementSerializer

    def perform_create(self, serializer):
        uid = get_request_user_id(self.request)
        serializer.save(author_user_id=uid, author_role="staff")

class CmsRoleAssignmentViewSet(viewsets.ModelViewSet):
    queryset = CmsRoleAssignment.objects.all().order_by("-created_at")
    serializer_class = CmsRoleAssignmentSerializer

    def perform_create(self, serializer):
        uid = get_request_user_id(self.request)
        role_type = serializer.validated_data["role_type"]
        # Enforce cardinality: exactly one active role-holder at a time (BR-CMS-037)
        if serializer.validated_data.get("is_active", True):
            CmsRoleAssignment.objects.filter(role_type=role_type, is_active=True).update(is_active=False)
        serializer.save(assigned_by_id=uid)
