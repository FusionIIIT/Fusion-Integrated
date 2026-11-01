"""HR-EIS API Views (parse, scope, delegate, serialize)."""
from __future__ import annotations

from decimal import Decimal
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.hreis.api import serializers as s
from modules.hreis.models import (
    AppraisalSubmission,
    CpdaRequest,
    EmployeeServiceRecord,
    LeaveRequest,
    LtcRequest,
    WorkflowConfiguration,
)
from modules.hreis.selectors import scoping
from modules.hreis.services import (
    appraisals as appraisal_service,
    claims as claim_service,
    leaves as leave_service,
    notifications as notif_service,
    service_records as record_service,
    workflow_config as config_service,
)

MODULE = HasModuleGrant("hr_eis")


class MyServiceRecordView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.service_record.view_self")]
    serializer_class = s.EmployeeServiceRecordSerializer

    def get(self, request):
        rec = record_service.get_or_create_service_record(request.principal.user_id)
        return Response(s.EmployeeServiceRecordSerializer(rec).data)


class ServiceRecordListView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.service_record.view_all")]
    serializer_class = s.EmployeeServiceRecordSerializer

    def get(self, request):
        records = scoping.service_records_for(request.principal)
        return Response(s.EmployeeServiceRecordSerializer(records, many=True).data)

    def post(self, request):
        if not request.principal.has_permission("hr_eis.service_record.manage"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.EmployeeServiceRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rec = serializer.save()
        return Response(s.EmployeeServiceRecordSerializer(rec).data, status=status.HTTP_201_CREATED)


class ServiceRecordDetailView(APIView):
    permission_classes = [MODULE]
    serializer_class = s.EmployeeServiceRecordSerializer

    def get(self, request, pk: int):
        rec = scoping.service_records_for(request.principal).filter(id=pk).first()
        if not rec:
            raise NotFoundError("Service record not found.")
        return Response(s.EmployeeServiceRecordSerializer(rec).data)

    def patch(self, request, pk: int):
        if not request.principal.has_permission("hr_eis.service_record.manage"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        updated = record_service.update_service_record(
            record_id=pk,
            data=request.data,
            actor_id=request.principal.user_id,
            actor_username=request.principal.username,
            actor_role=request.principal.roles[0] if request.principal.roles else "hr_admin",
        )
        return Response(s.EmployeeServiceRecordSerializer(updated).data)


# --- LEAVES ---

class LeaveListCreateView(APIView):
    permission_classes = [MODULE]
    serializer_class = s.LeaveRequestSerializer

    def get(self, request):
        if not (request.principal.has_permission("hr_eis.leave.view_self") or request.principal.has_permission("hr_eis.leave.review")):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        leaves = scoping.leaves_for(request.principal)
        return Response(s.LeaveRequestSerializer(leaves, many=True).data)

    def post(self, request):
        if not request.principal.has_permission("hr_eis.leave.apply"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.LeaveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        leave = leave_service.submit_leave_request(
            user_id=request.principal.user_id,
            username=request.principal.username,
            leave_type=data["leave_type"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            duration_days=float(data["duration_days"]),
            justification=data["justification"],
        )
        return Response(s.LeaveRequestSerializer(leave).data, status=status.HTTP_201_CREATED)


class LeaveDetailView(APIView):
    permission_classes = [MODULE]
    serializer_class = s.LeaveRequestSerializer

    def get(self, request, pk: int):
        if not (request.principal.has_permission("hr_eis.leave.view_self") or request.principal.has_permission("hr_eis.leave.review")):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        leave = scoping.leaves_for(request.principal).filter(id=pk).first()
        if not leave:
            raise NotFoundError("Leave request not found.")
        return Response(s.LeaveRequestSerializer(leave).data)


class LeaveDecideView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.leave.review")]
    serializer_class = s.LeaveDecisionSerializer

    def post(self, request, pk: int):
        serializer = s.LeaveDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        outcome = serializer.validated_data["outcome"]
        remarks = serializer.validated_data.get("remarks", "")

        decided = leave_service.decide_leave_request(
            leave_id=pk,
            outcome=outcome,
            remarks=remarks,
            actor_id=request.principal.user_id,
            actor_username=request.principal.username,
            actor_role=request.principal.roles[0] if request.principal.roles else "approver",
        )
        return Response(s.LeaveRequestSerializer(decided).data)


# --- APPRAISALS ---

class AppraisalListCreateView(APIView):
    permission_classes = [MODULE]
    serializer_class = s.AppraisalSubmissionSerializer

    def get(self, request):
        if not (
            request.principal.has_permission("hr_eis.appraisal.view_self")
            or request.principal.has_permission("hr_eis.appraisal.review")
            or request.principal.has_permission("hr_eis.appraisal.assign_reviewer")
            or request.principal.has_permission("hr_eis.appraisal.finalize")
        ):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        appraisals = scoping.appraisals_for(request.principal)
        return Response(s.AppraisalSubmissionSerializer(appraisals, many=True).data)

    def post(self, request):
        if not request.principal.has_permission("hr_eis.appraisal.submit"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.AppraisalSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        content = data.get("content")
        if not content:
            content = {k: v for k, v in request.data.items() if k not in ("academic_year", "draft")}

        appraisal = appraisal_service.submit_appraisal(
            user_id=request.principal.user_id,
            username=request.principal.username,
            academic_year=data["academic_year"],
            content=content,
            is_draft=request.query_params.get("draft") == "1",
        )
        return Response(s.AppraisalSubmissionSerializer(appraisal).data, status=status.HTTP_201_CREATED)


class AppraisalDetailView(APIView):
    permission_classes = [MODULE]
    serializer_class = s.AppraisalSubmissionSerializer

    def get(self, request, pk: int):
        if not (
            request.principal.has_permission("hr_eis.appraisal.view_self")
            or request.principal.has_permission("hr_eis.appraisal.review")
            or request.principal.has_permission("hr_eis.appraisal.assign_reviewer")
            or request.principal.has_permission("hr_eis.appraisal.finalize")
        ):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        appraisal = scoping.appraisals_for(request.principal).filter(id=pk).first()
        if not appraisal:
            raise NotFoundError("Appraisal not found.")
        return Response(s.AppraisalSubmissionSerializer(appraisal).data)


class AppraisalAssignReviewersView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.appraisal.assign_reviewer")]
    serializer_class = s.AssignReviewersSerializer

    def post(self, request, pk: int):
        serializer = s.AssignReviewersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reviewer_ids = serializer.validated_data["reviewer_ids"]

        appraisal = appraisal_service.assign_appraisal_reviewers(
            appraisal_id=pk,
            reviewer_ids=reviewer_ids,
            actor_id=request.principal.user_id,
            actor_username=request.principal.username,
            actor_role=request.principal.roles[0] if request.principal.roles else "hr_admin",
        )
        return Response(s.AppraisalSubmissionSerializer(appraisal).data)


class AppraisalReviewView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.appraisal.review")]
    serializer_class = s.AppraisalReviewSerializer

    def post(self, request, pk: int):
        serializer = s.AppraisalReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appraisal = appraisal_service.submit_appraisal_review(
            appraisal_id=pk,
            score=serializer.validated_data["score"],
            comments=serializer.validated_data["comments"],
            actor_id=request.principal.user_id,
            actor_username=request.principal.username,
            actor_role=request.principal.roles[0] if request.principal.roles else "reviewer",
        )
        return Response(s.AppraisalSubmissionSerializer(appraisal).data)


class AppraisalFinalizeView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.appraisal.finalize")]
    serializer_class = s.AppraisalFinalizeSerializer

    def post(self, request, pk: int):
        serializer = s.AppraisalFinalizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appraisal = appraisal_service.finalize_appraisal(
            appraisal_id=pk,
            final_score=serializer.validated_data["final_score"],
            final_remarks=serializer.validated_data["final_remarks"],
            actor_id=request.principal.user_id,
            actor_username=request.principal.username,
            actor_role=request.principal.roles[0] if request.principal.roles else "director",
        )
        return Response(s.AppraisalSubmissionSerializer(appraisal).data)


# --- LTC ---

class LtcListCreateView(APIView):
    permission_classes = [MODULE]
    serializer_class = s.LtcRequestSerializer

    def get(self, request):
        if not (
            request.principal.has_permission("hr_eis.ltc.view_self")
            or request.principal.has_permission("hr_eis.ltc.verify")
            or request.principal.has_permission("hr_eis.ltc.approve")
            or request.principal.has_permission("hr_eis.ltc.settle")
        ):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        claims = scoping.ltc_requests_for(request.principal)
        return Response(s.LtcRequestSerializer(claims, many=True).data)

    def post(self, request):
        if not request.principal.has_permission("hr_eis.ltc.apply"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.LtcRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        claim = claim_service.submit_ltc_request(
            user_id=request.principal.user_id,
            username=request.principal.username,
            request_type=data["request_type"],
            block_year=data["block_year"],
            travel_from=data["travel_from"],
            travel_to=data["travel_to"],
            travel_start_date=data["travel_start_date"],
            travel_end_date=data["travel_end_date"],
            estimated_amount=data["estimated_amount"],
            claimed_amount=data.get("claimed_amount"),
            supporting_documents=data.get("supporting_documents", []),
        )
        return Response(s.LtcRequestSerializer(claim).data, status=status.HTTP_201_CREATED)


class LtcDetailView(APIView):
    permission_classes = [MODULE]
    serializer_class = s.LtcRequestSerializer

    def get(self, request, pk: int):
        if not (
            request.principal.has_permission("hr_eis.ltc.view_self")
            or request.principal.has_permission("hr_eis.ltc.verify")
            or request.principal.has_permission("hr_eis.ltc.approve")
            or request.principal.has_permission("hr_eis.ltc.settle")
        ):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        claim = scoping.ltc_requests_for(request.principal).filter(id=pk).first()
        if not claim:
            raise NotFoundError("LTC claim not found.")
        return Response(s.LtcRequestSerializer(claim).data)


class LtcVerifyView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.ltc.verify")]
    serializer_class = s.ClaimVerificationSerializer

    def post(self, request, pk: int):
        serializer = s.ClaimVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verified = claim_service.verify_ltc_request(
            ltc_id=pk,
            verdict=serializer.validated_data["verdict"],
            remarks=serializer.validated_data.get("remarks", ""),
            actor_id=request.principal.user_id,
            actor_username=request.principal.username,
            actor_role=request.principal.roles[0] if request.principal.roles else "hr_admin",
        )
        return Response(s.LtcRequestSerializer(verified).data)


class LtcDecideView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.ltc.approve")]
    serializer_class = s.ClaimDecisionSerializer

    def post(self, request, pk: int):
        serializer = s.ClaimDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decided = claim_service.decide_ltc_request(
            ltc_id=pk,
            outcome=serializer.validated_data["outcome"],
            remarks=serializer.validated_data.get("remarks", ""),
            actor_id=request.principal.user_id,
            actor_username=request.principal.username,
            actor_role=request.principal.roles[0] if request.principal.roles else "approver",
        )
        return Response(s.LtcRequestSerializer(decided).data)


class LtcSettleView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.ltc.settle")]
    serializer_class = s.LtcSettlementSerializer

    def post(self, request, pk: int):
        serializer = s.LtcSettlementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        settled = claim_service.settle_ltc_claim(
            ltc_id=pk,
            passed_amount=serializer.validated_data["passed_amount"],
            reference_id=serializer.validated_data["reference_id"],
            remarks=serializer.validated_data.get("remarks", ""),
            actor_id=request.principal.user_id,
            actor_username=request.principal.username,
            actor_role=request.principal.roles[0] if request.principal.roles else "accountant",
        )
        return Response(s.LtcRequestSerializer(settled).data)


# --- CPDA ---

class CpdaListCreateView(APIView):
    permission_classes = [MODULE]
    serializer_class = s.CpdaRequestSerializer

    def get(self, request):
        if not (
            request.principal.has_permission("hr_eis.cpda.view_self")
            or request.principal.has_permission("hr_eis.cpda.verify")
            or request.principal.has_permission("hr_eis.cpda.approve")
            or request.principal.has_permission("hr_eis.cpda.settle")
        ):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        claims = scoping.cpda_requests_for(request.principal)
        return Response(s.CpdaRequestSerializer(claims, many=True).data)

    def post(self, request):
        if not request.principal.has_permission("hr_eis.cpda.apply"):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.CpdaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        claim = claim_service.submit_cpda_request(
            user_id=request.principal.user_id,
            username=request.principal.username,
            request_type=data["request_type"],
            purpose=data["purpose"],
            amount=data["amount"],
            supporting_documents=data.get("supporting_documents", []),
        )
        return Response(s.CpdaRequestSerializer(claim).data, status=status.HTTP_201_CREATED)


class CpdaDetailView(APIView):
    permission_classes = [MODULE]
    serializer_class = s.CpdaRequestSerializer

    def get(self, request, pk: int):
        if not (
            request.principal.has_permission("hr_eis.cpda.view_self")
            or request.principal.has_permission("hr_eis.cpda.verify")
            or request.principal.has_permission("hr_eis.cpda.approve")
            or request.principal.has_permission("hr_eis.cpda.settle")
        ):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        claim = scoping.cpda_requests_for(request.principal).filter(id=pk).first()
        if not claim:
            raise NotFoundError("CPDA claim not found.")
        return Response(s.CpdaRequestSerializer(claim).data)


class CpdaVerifyView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.cpda.verify")]
    serializer_class = s.ClaimVerificationSerializer

    def post(self, request, pk: int):
        serializer = s.ClaimVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verified = claim_service.verify_cpda_request(
            cpda_id=pk,
            verdict=serializer.validated_data["verdict"],
            remarks=serializer.validated_data.get("remarks", ""),
            actor_id=request.principal.user_id,
            actor_username=request.principal.username,
            actor_role=request.principal.roles[0] if request.principal.roles else "hr_admin",
        )
        return Response(s.CpdaRequestSerializer(verified).data)


class CpdaDecideView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.cpda.approve")]
    serializer_class = s.ClaimDecisionSerializer

    def post(self, request, pk: int):
        serializer = s.ClaimDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decided = claim_service.decide_cpda_request(
            cpda_id=pk,
            outcome=serializer.validated_data["outcome"],
            remarks=serializer.validated_data.get("remarks", ""),
            actor_id=request.principal.user_id,
            actor_username=request.principal.username,
            actor_role=request.principal.roles[0] if request.principal.roles else "approver",
        )
        return Response(s.CpdaRequestSerializer(decided).data)


class CpdaSettleView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.cpda.settle")]
    serializer_class = s.CpdaSettlementSerializer

    def post(self, request, pk: int):
        serializer = s.CpdaSettlementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        settled = claim_service.settle_cpda_claim(
            cpda_id=pk,
            passed_amount=serializer.validated_data["passed_amount"],
            voucher_no=serializer.validated_data["voucher_no"],
            remarks=serializer.validated_data.get("remarks", ""),
            actor_id=request.principal.user_id,
            actor_username=request.principal.username,
            actor_role=request.principal.roles[0] if request.principal.roles else "accountant",
        )
        return Response(s.CpdaRequestSerializer(settled).data)


# --- WORKFLOW CONFIGURATION ---

class WorkflowConfigView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.workflow.configure")]
    serializer_class = s.WorkflowConfigurationSerializer

    def get(self, request):
        configs = WorkflowConfiguration.objects.all()
        return Response(s.WorkflowConfigurationSerializer(configs, many=True).data)

    def put(self, request):
        key = request.data.get("setting_key")
        value = request.data.get("setting_value")
        desc = request.data.get("description", "")
        if not key or value is None:
            raise BadRequestError("setting_key and setting_value are required.")
        updated = config_service.update_workflow_config(key, value, desc)
        return Response({"setting_key": key, "setting_value": updated})


# --- AUDIT LOGS ---

class AuditLogListView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.audit.view")]
    serializer_class = s.HrAuditLogSerializer

    def get(self, request):
        logs = scoping.audit_logs_for(request.principal)
        return Response(s.HrAuditLogSerializer(logs[:100], many=True).data)


# --- NOTIFICATIONS ---

class NotificationListView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.notification.view_self")]
    serializer_class = s.HrNotificationSerializer

    def get(self, request):
        notifs = scoping.notifications_for(request.principal)
        return Response(s.HrNotificationSerializer(notifs, many=True).data)


class NotificationMarkReadView(APIView):
    permission_classes = [MODULE, HasPermission("hr_eis.notification.view_self")]
    serializer_class = s.HrNotificationSerializer

    def patch(self, request, pk: int):
        ok = notif_service.mark_notification_read(pk, request.principal.user_id)
        if not ok:
            raise NotFoundError("Notification not found.")
        return Response({"status": "ok"})


# --- STATS / DASHBOARD ---

class DashboardStatsView(APIView):
    permission_classes = [MODULE]
    serializer_class = s.DashboardStatsSerializer

    def get(self, request):
        user_id = request.principal.user_id
        service_rec = record_service.get_or_create_service_record(user_id)

        stats = {
            "leave_balances": service_rec.leave_balances,
            "cpda_balance": float(service_rec.cpda_balance),
            "pending_leaves_count": LeaveRequest.objects.filter(user_id=user_id, status="pending").count(),
            "pending_ltc_count": LtcRequest.objects.filter(user_id=user_id, status__in=["submitted", "verified", "pending_approval"]).count(),
            "pending_cpda_count": CpdaRequest.objects.filter(user_id=user_id, status__in=["submitted", "verified", "pending_approval"]).count(),
            "unread_notifications": scoping.notifications_for(request.principal).filter(is_read=False).count(),
        }

        roles = [r.lower() for r in request.principal.roles]
        if request.principal.has_permission("hr_eis.leave.review"):
            stats["queue_leave_approvals"] = LeaveRequest.objects.filter(current_authority_role__in=roles, status__in=["pending", "forwarded"]).count()
        if request.principal.has_permission("hr_eis.ltc.verify"):
            stats["queue_ltc_verifications"] = LtcRequest.objects.filter(verification_status="pending_verification").count()
        if request.principal.has_permission("hr_eis.cpda.verify"):
            stats["queue_cpda_verifications"] = CpdaRequest.objects.filter(verification_status="pending_verification").count()
        if request.principal.has_permission("hr_eis.ltc.settle"):
            stats["queue_ltc_settlements"] = LtcRequest.objects.filter(status="approved", payment_status="unpaid").count()
        if request.principal.has_permission("hr_eis.cpda.settle"):
            stats["queue_cpda_settlements"] = CpdaRequest.objects.filter(status="approved", disbursement_status="unpaid").count()

        return Response(stats)
