"""PHC API: views.

Role-to-permission mapping (PHC-BR-03, AFR-PHC-036):
  phc_staff           → schedule/attendance, records, inventory, requisitions (create/fulfill),
                        ambulance, announcements, reports, PHC-stage claim review.
  patient / employee  → read own records, download, announcements; employee: submit/track claims.
  accounts_audit      → verify claims, process payment.
  approving_authority → decide claims and requisitions.

No endpoint is reachable without both HasModuleGrant("phc") and the fine-grained permission.
"""

from __future__ import annotations

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.phc.api import serializers as s
from modules.phc.models import (
    DoctorSchedule,
    InventoryItem,
    PatientVisit,
    ProcurementRequisition,
    ReimbursementClaim,
    ReimbursementConfig,
)
from modules.phc.selectors import scoping
from modules.phc.services import inventory as inv_service
from modules.phc.services import operations as ops_service
from modules.phc.services import records as rec_service
from modules.phc.services import reimbursement as reimb_service
from modules.phc.services import schedules as sched_service

MODULE = HasModuleGrant("phc")

# Fine-grained permission codes (PHC-BR-03)
P_SCHEDULE_MANAGE = "phc.schedule.manage"
P_SCHEDULE_VIEW = "phc.schedule.view"
P_ATTENDANCE_MARK = "phc.attendance.mark"
P_RECORD_MANAGE = "phc.record.manage"
P_RECORD_VIEW_SELF = "phc.record.view_self"
P_CLAIM_SUBMIT = "phc.claim.submit"
P_CLAIM_VIEW_SELF = "phc.claim.view_self"
P_CLAIM_REVIEW_PHC = "phc.claim.review_phc"
P_CLAIM_VERIFY = "phc.claim.verify"
P_CLAIM_DECIDE = "phc.claim.decide"
P_CLAIM_PAYMENT = "phc.claim.payment"
P_CLAIM_CONFIGURE = "phc.claim.configure"
P_INVENTORY_MANAGE = "phc.inventory.manage"
P_REQUISITION_SUBMIT = "phc.requisition.submit"
P_REQUISITION_DECIDE = "phc.requisition.decide"
P_REQUISITION_FULFILL = "phc.requisition.fulfill"
P_AMBULANCE_LOG = "phc.ambulance.log"
P_ANNOUNCEMENT_PUBLISH = "phc.announcement.publish"
P_REPORT_VIEW = "phc.report.view"


def _actor(request):
    return getattr(request, "principal", None)


def _user_id(request) -> int:
    return _actor(request).user_id


def _not_found(msg: str = "Not found."):
    raise NotFoundError(msg)


# ---------------------------------------------------------------------------
# Schedule & Availability  (PHC-UC-01, PHC-UC-07, PHC-UC-08, PHC-UC-22)
# ---------------------------------------------------------------------------


class ScheduleListView(generics.ListAPIView):
    """PHC-UC-01 (patients) + PHC-UC-07/22 list (PHC Staff).

    Patients see only published slots; staff see all.
    """

    serializer_class = s.DoctorScheduleSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        p = _actor(self.request)
        if p and p.has_permission(P_SCHEDULE_MANAGE):
            return scoping.all_schedules()
        return scoping.published_schedules()


class ScheduleCreateView(APIView):
    """PHC-UC-07/22: PHC Staff creates a schedule slot."""

    permission_classes = [MODULE, HasPermission(P_SCHEDULE_MANAGE)]

    def post(self, request):
        ser = s.DoctorScheduleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        slot = sched_service.create_schedule_slot(
            doctor_name=d["doctor_name"],
            specialisation=d.get("specialisation", ""),
            day_of_week=d["day_of_week"],
            start_time=d["start_time"],
            end_time=d["end_time"],
            room=d.get("room", ""),
            is_published=False,
            actor_user_id=_user_id(request),
        )
        return Response(s.DoctorScheduleSerializer(slot).data, status=status.HTTP_201_CREATED)


class SchedulePublishView(APIView):
    """PHC-UC-07/22, AFR-PHC-003: Publish a schedule slot."""

    permission_classes = [MODULE, HasPermission(P_SCHEDULE_MANAGE)]

    def post(self, request, pk):
        try:
            slot = DoctorSchedule.objects.get(pk=pk)
        except DoctorSchedule.DoesNotExist:
            _not_found()
        sched_service.publish_schedule(slot=slot, actor_user_id=_user_id(request))
        return Response(s.DoctorScheduleSerializer(slot).data)


class AttendanceMarkView(APIView):
    """PHC-UC-08, AFR-PHC-004: PHC Staff marks a doctor's real-time status."""

    permission_classes = [MODULE, HasPermission(P_ATTENDANCE_MARK)]

    def post(self, request):
        ser = s.MarkAttendanceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            schedule = DoctorSchedule.objects.get(pk=d["schedule_id"])
        except DoctorSchedule.DoesNotExist:
            _not_found("No schedule slot found with that id.")
        date = d.get("date") or timezone.localdate()
        attendance = sched_service.mark_attendance(
            schedule=schedule,
            status=d["status"],
            date=date,
            actor_user_id=_user_id(request),
        )
        return Response(s.DoctorAttendanceSerializer(attendance).data)


class AttendanceTodayView(generics.ListAPIView):
    """PHC-UC-01, AFR-PHC-005: Combined schedule + today's attendance for patients."""

    serializer_class = s.DoctorAttendanceSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        return scoping.today_attendance(timezone.localdate())


# ---------------------------------------------------------------------------
# Patient Records  (PHC-UC-02, PHC-UC-03, PHC-UC-06)
# ---------------------------------------------------------------------------


class MyVisitsView(generics.ListAPIView):
    """PHC-UC-02, AFR-PHC-009: Patient reads own visits (ownership check)."""

    serializer_class = s.PatientVisitSerializer
    permission_classes = [MODULE, HasPermission(P_RECORD_VIEW_SELF)]

    def get_queryset(self):
        return scoping.patient_visits(_user_id(self.request))


class MyVisitDetailView(generics.RetrieveAPIView):
    """PHC-UC-02, PHC-BR-02: ownership-scoped detail + associated prescriptions."""

    serializer_class = s.PatientVisitSerializer
    permission_classes = [MODULE, HasPermission(P_RECORD_VIEW_SELF)]

    def get_object(self):
        qs = scoping.patient_visits(_user_id(self.request))
        try:
            return qs.get(pk=self.kwargs["pk"])
        except PatientVisit.DoesNotExist:
            _not_found()


class MyVisitsPdfView(APIView):
    """PHC-UC-03: download selected own visit records as a PDF."""

    permission_classes = [MODULE, HasPermission(P_RECORD_VIEW_SELF)]

    def get(self, request):
        from modules.phc.services.pdf import render_visits_pdf

        raw_ids = request.query_params.get("ids", "")
        visit_ids = None
        if raw_ids:
            try:
                visit_ids = [int(value) for value in raw_ids.split(",") if value.strip()]
            except ValueError:
                raise BadRequestError("ids must be comma-separated visit IDs.") from None
            if not visit_ids:
                raise BadRequestError("Select at least one visit to download.")

        queryset = scoping.patient_visits(_user_id(request))
        if visit_ids is not None:
            queryset = queryset.filter(pk__in=visit_ids)
            visits = list(queryset.prefetch_related("prescriptions"))
            if len(visits) != len(set(visit_ids)):
                # Do not disclose whether a missing ID belongs to another patient.
                _not_found("One or more selected records are unavailable.")
        else:
            visits = list(queryset.prefetch_related("prescriptions"))
        if not visits:
            _not_found("No medical records are available to download.")

        response = HttpResponse(render_visits_pdf(visits), content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="phc-medical-records.pdf"'
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class VisitListStaffView(generics.ListAPIView):
    """PHC-UC-06: PHC Staff lists all visits."""

    serializer_class = s.PatientVisitSerializer
    permission_classes = [MODULE, HasPermission(P_RECORD_MANAGE)]

    def get_queryset(self):
        return scoping.all_visits()


class PatientSearchView(APIView):
    """PHC-UC-06, AFR-PHC-006: find a student/employee patient profile."""

    permission_classes = [MODULE, HasPermission(P_RECORD_MANAGE)]

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        try:
            limit = min(max(int(request.query_params.get("limit", 25)), 1), 100)
        except (TypeError, ValueError) as exc:
            raise BadRequestError("limit must be a number.", code="invalid_filter") from exc
        results = rec_service.search_patients(query=query, limit=limit) if len(query) >= 2 else []
        return Response({"results": results})


class VisitCreateView(APIView):
    """PHC-UC-06, AFR-PHC-006: PHC Staff creates a visit record."""

    permission_classes = [MODULE, HasPermission(P_RECORD_MANAGE)]

    def post(self, request):
        ser = s.CreateVisitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        visit = rec_service.create_visit(
            patient_user_id=d["patient_user_id"],
            visit_date=d["visit_date"],
            chief_complaint=d["chief_complaint"],
            diagnosis=d.get("diagnosis", ""),
            notes=d.get("notes", ""),
            actor_user_id=_user_id(request),
        )
        return Response(s.PatientVisitSerializer(visit).data, status=status.HTTP_201_CREATED)


class PrescriptionCreateView(APIView):
    """PHC-UC-06, AFR-PHC-008: PHC Staff adds a prescription to a visit."""

    permission_classes = [MODULE, HasPermission(P_RECORD_MANAGE)]

    def post(self, request, visit_pk):
        try:
            visit = PatientVisit.objects.get(pk=visit_pk)
        except PatientVisit.DoesNotExist:
            _not_found()
        ser = s.AddPrescriptionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        rx = rec_service.add_prescription(
            visit=visit,
            medicine_name=d["medicine_name"],
            dosage=d["dosage"],
            duration_days=d.get("duration_days"),
            instructions=d.get("instructions", ""),
            expense_date=d.get("expense_date"),
            actor_user_id=_user_id(request),
        )
        return Response(s.PrescriptionSerializer(rx).data, status=status.HTTP_201_CREATED)


class MyPrescriptionsView(generics.ListAPIView):
    """PHC-UC-02, AFR-PHC-010: Patient reads own prescriptions."""

    serializer_class = s.PrescriptionSerializer
    permission_classes = [MODULE, HasPermission(P_RECORD_VIEW_SELF)]

    def get_queryset(self):
        return scoping.patient_prescriptions(_user_id(self.request))


# ---------------------------------------------------------------------------
# Medical Bill Reimbursement  (PHC-UC-04, PHC-UC-05, PHC-UC-15, PHC-UC-19,
#                               PHC-UC-20, PHC-UC-21)
# ---------------------------------------------------------------------------


class MyClaimsView(generics.ListAPIView):
    """PHC-UC-05, AFR-PHC-022: Employee tracks own claims."""

    serializer_class = s.ReimbursementClaimSerializer
    permission_classes = [MODULE, HasPermission(P_CLAIM_VIEW_SELF)]

    def get_queryset(self):
        return scoping.employee_claims(_user_id(self.request))


class MyClaimDetailView(generics.RetrieveAPIView):
    """PHC-UC-05 detail: employee views own claim with status history."""

    serializer_class = s.ReimbursementClaimSerializer
    permission_classes = [MODULE, HasPermission(P_CLAIM_VIEW_SELF)]

    def get_object(self):
        try:
            return scoping.employee_claims(_user_id(self.request)).get(pk=self.kwargs["pk"])
        except ReimbursementClaim.DoesNotExist:
            _not_found()


class SubmitClaimView(APIView):
    """PHC-UC-04, AFR-PHC-013: Employee submits a reimbursement claim.

    PHC-BR-04: students are denied here.
    """

    permission_classes = [MODULE, HasPermission(P_CLAIM_SUBMIT)]

    def post(self, request):
        ser = s.SubmitClaimSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        principal = _actor(request)
        claim = reimb_service.submit_claim(
            claimant_user_id=principal.user_id,
            claimant_kind=principal.kind,
            prescription_id=d["prescription_id"],
            amount_claimed=d["amount_claimed"],
            description=d.get("description", ""),
        )
        return Response(s.ReimbursementClaimSerializer(claim).data, status=status.HTTP_201_CREATED)


class AllClaimsView(generics.ListAPIView):
    """PHC Staff / Accounts & Audit / Approving Authority: all claims."""

    serializer_class = s.ReimbursementClaimSerializer
    permission_classes = [
        MODULE,
        HasPermission(
            P_CLAIM_REVIEW_PHC,
            P_CLAIM_VERIFY,
            P_CLAIM_DECIDE,
            P_CLAIM_PAYMENT,
        ),
    ]

    def get_queryset(self):
        status_filter = self.request.query_params.get("status")
        qs = scoping.all_claims()
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class ClaimReviewView(APIView):
    """PHC-UC-15, AFR-PHC-017: PHC Staff forwards claim to Accounts & Audit."""

    permission_classes = [MODULE, HasPermission(P_CLAIM_REVIEW_PHC)]

    def post(self, request, pk):
        try:
            claim = ReimbursementClaim.objects.get(pk=pk)
        except ReimbursementClaim.DoesNotExist:
            _not_found()
        reimb_service.phc_review_forward(claim=claim, actor_user_id=_user_id(request))
        return Response(s.ReimbursementClaimSerializer(claim).data)


class ClaimVerifyView(APIView):
    """PHC-UC-19, AFR-PHC-018: Accounts & Audit completes verification."""

    permission_classes = [MODULE, HasPermission(P_CLAIM_VERIFY)]

    def post(self, request, pk):
        try:
            claim = ReimbursementClaim.objects.get(pk=pk)
        except ReimbursementClaim.DoesNotExist:
            _not_found()
        reimb_service.accounts_verify(claim=claim, actor_user_id=_user_id(request))
        return Response(s.ReimbursementClaimSerializer(claim).data)


class ClaimDecideView(APIView):
    """PHC-UC-20, AFR-PHC-019: Approving Authority approves or rejects sanction."""

    permission_classes = [MODULE, HasPermission(P_CLAIM_DECIDE)]

    def post(self, request, pk):
        try:
            claim = ReimbursementClaim.objects.get(pk=pk)
        except ReimbursementClaim.DoesNotExist:
            _not_found()
        ser = s.ClaimDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reimb_service.authority_decide(
            claim=claim,
            actor_user_id=_user_id(request),
            approve=ser.validated_data["approve"],
            notes=ser.validated_data.get("notes", ""),
        )
        return Response(s.ReimbursementClaimSerializer(claim).data)


class ClaimPaymentView(APIView):
    """PHC-UC-21, AFR-PHC-021: Accounts & Audit records payment."""

    permission_classes = [MODULE, HasPermission(P_CLAIM_PAYMENT)]

    def post(self, request, pk):
        try:
            claim = ReimbursementClaim.objects.get(pk=pk)
        except ReimbursementClaim.DoesNotExist:
            _not_found()
        reimb_service.process_payment(claim=claim, actor_user_id=_user_id(request))
        return Response(s.ReimbursementClaimSerializer(claim).data)


class ReimbursementConfigView(APIView):
    """PHC Staff configures the submission window (PHC-BR-06)."""

    permission_classes = [MODULE, HasPermission(P_CLAIM_CONFIGURE)]

    def get(self, request):
        config, _ = ReimbursementConfig.objects.get_or_create(pk=1)
        return Response(s.ReimbursementConfigSerializer(config).data)

    def patch(self, request):
        config, _ = ReimbursementConfig.objects.get_or_create(pk=1)
        serializer = s.ReimbursementConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Inventory  (PHC-UC-09, AFR-PHC-024 … AFR-PHC-026)
# ---------------------------------------------------------------------------


class InventoryListView(generics.ListAPIView):
    """PHC Staff: view all inventory items."""

    serializer_class = s.InventoryItemSerializer
    permission_classes = [MODULE, HasPermission(P_INVENTORY_MANAGE)]

    def get_queryset(self):
        return scoping.all_inventory()


class InventoryCreateView(APIView):
    """PHC Staff: create an inventory item."""

    permission_classes = [MODULE, HasPermission(P_INVENTORY_MANAGE)]

    def post(self, request):
        ser = s.InventoryItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        item = InventoryItem.objects.create(**ser.validated_data)
        return Response(s.InventoryItemSerializer(item).data, status=status.HTTP_201_CREATED)


class InventoryDetailView(generics.RetrieveAPIView):
    """PHC Staff: retrieve a single inventory item."""

    serializer_class = s.InventoryItemSerializer
    permission_classes = [MODULE, HasPermission(P_INVENTORY_MANAGE)]

    def get_object(self):
        try:
            return InventoryItem.objects.get(pk=self.kwargs["pk"])
        except InventoryItem.DoesNotExist:
            _not_found()


class InventoryAdjustView(APIView):
    """PHC-UC-09, AFR-PHC-024: PHC Staff adjusts stock level.

    PHC-BR-07: triggers low-stock notification automatically.
    PHC-BR-09: immutable InventoryAudit is created by the service.
    """

    permission_classes = [MODULE, HasPermission(P_INVENTORY_MANAGE)]

    def post(self, request, pk):
        try:
            item = InventoryItem.objects.get(pk=pk)
        except InventoryItem.DoesNotExist:
            _not_found()
        ser = s.AdjustStockSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        inv_service.adjust_stock(
            item=item,
            delta=ser.validated_data["delta"],
            actor_user_id=_user_id(request),
            notes=ser.validated_data.get("notes", ""),
        )
        return Response(s.InventoryItemSerializer(item).data)


class LowStockListView(generics.ListAPIView):
    """PHC-BR-07: List items currently below reorder threshold."""

    serializer_class = s.InventoryItemSerializer
    permission_classes = [MODULE, HasPermission(P_INVENTORY_MANAGE)]

    def get_queryset(self):
        return scoping.low_stock_items()


# ---------------------------------------------------------------------------
# Procurement Requisitions  (PHC-UC-10, PHC-UC-14, PHC-UC-16)
# ---------------------------------------------------------------------------


class RequisitionListView(generics.ListAPIView):
    """PHC Staff: own requisitions. Approving Authority: all pending."""

    serializer_class = s.ProcurementRequisitionSerializer
    permission_classes = [MODULE, HasPermission(P_REQUISITION_SUBMIT, P_REQUISITION_DECIDE)]

    def get_queryset(self):
        p = _actor(self.request)
        if p and p.has_permission(P_REQUISITION_DECIDE):
            return scoping.pending_requisitions()
        return scoping.submitter_requisitions(p.user_id)


class RequisitionCreateView(APIView):
    """PHC-UC-10, AFR-PHC-027: PHC Staff submits a procurement requisition."""

    permission_classes = [MODULE, HasPermission(P_REQUISITION_SUBMIT)]

    def post(self, request):
        ser = s.CreateRequisitionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        req = inv_service.create_requisition(
            title=d["title"],
            justification=d.get("justification", ""),
            line_items=d["line_items"],
            actor_user_id=_user_id(request),
        )
        return Response(
            s.ProcurementRequisitionSerializer(req).data, status=status.HTTP_201_CREATED
        )


class RequisitionDecideView(APIView):
    """PHC-UC-16, AFR-PHC-028/AFR-PHC-029: Approving Authority decides."""

    permission_classes = [MODULE, HasPermission(P_REQUISITION_DECIDE)]

    def post(self, request, pk):
        try:
            req = ProcurementRequisition.objects.prefetch_related("line_items").get(pk=pk)
        except ProcurementRequisition.DoesNotExist:
            _not_found()
        ser = s.RequisitionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        inv_service.decide_requisition(
            req=req,
            actor_user_id=_user_id(request),
            approve=ser.validated_data["approve"],
            notes=ser.validated_data.get("notes", ""),
        )
        return Response(s.ProcurementRequisitionSerializer(req).data)


class RequisitionFulfillView(APIView):
    """PHC-UC-14, AFR-PHC-031: PHC Staff marks approved requisition fulfilled."""

    permission_classes = [MODULE, HasPermission(P_REQUISITION_FULFILL)]

    def post(self, request, pk):
        try:
            req = ProcurementRequisition.objects.prefetch_related("line_items").get(pk=pk)
        except ProcurementRequisition.DoesNotExist:
            _not_found()
        inv_service.mark_fulfilled(req=req, actor_user_id=_user_id(request))
        return Response(s.ProcurementRequisitionSerializer(req).data)


# ---------------------------------------------------------------------------
# Ambulance  (PHC-UC-11, AFR-PHC-032)
# ---------------------------------------------------------------------------


class AmbulanceLogListView(generics.ListAPIView):
    serializer_class = s.AmbulanceLogSerializer
    permission_classes = [MODULE, HasPermission(P_AMBULANCE_LOG)]

    def get_queryset(self):
        from modules.phc.models import AmbulanceLog

        return AmbulanceLog.objects.all()


class AmbulanceLogCreateView(APIView):
    """PHC-UC-11, AFR-PHC-032: PHC Staff records ambulance usage."""

    permission_classes = [MODULE, HasPermission(P_AMBULANCE_LOG)]

    def post(self, request):
        ser = s.CreateAmbulanceLogSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        entry = ops_service.log_ambulance_usage(
            patient_name=d["patient_name"],
            destination=d["destination"],
            usage_at=d["usage_at"],
            notes=d.get("notes", ""),
            actor_user_id=_user_id(request),
        )
        return Response(s.AmbulanceLogSerializer(entry).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Health Announcements  (PHC-UC-12, AFR-PHC-033)
# ---------------------------------------------------------------------------


class AnnouncementListView(generics.ListAPIView):
    """PHC-UC-12, AFR-PHC-033: Patients see published announcements on dashboard."""

    serializer_class = s.HealthAnnouncementSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        p = _actor(self.request)
        if p and p.has_permission(P_ANNOUNCEMENT_PUBLISH):
            return scoping.all_announcements()
        return scoping.patient_announcements()


class AnnouncementPublishView(APIView):
    """PHC-UC-12: PHC Staff publishes a health advisory."""

    permission_classes = [MODULE, HasPermission(P_ANNOUNCEMENT_PUBLISH)]

    def post(self, request):
        ser = s.PublishAnnouncementSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ann = ops_service.publish_announcement(
            title=ser.validated_data["title"],
            body=ser.validated_data["body"],
            actor_user_id=_user_id(request),
        )
        return Response(s.HealthAnnouncementSerializer(ann).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Reports  (PHC-UC-13, AFR-PHC-034, AFR-PHC-035, PHC-BR-12)
# ---------------------------------------------------------------------------


class ReportView(APIView):
    """PHC-UC-13: PHC Staff generates an anonymized report."""

    permission_classes = [MODULE, HasPermission(P_REPORT_VIEW)]

    def get(self, request):
        report_type = request.query_params.get("type", "demographics")
        data = ops_service.generate_report(report_type)
        return Response(data)


# ---------------------------------------------------------------------------
# Notifications (self)
# ---------------------------------------------------------------------------


class MyNotificationsView(generics.ListAPIView):
    """PHC-UC-05, AFR-PHC-023: Claimant or staff sees own notifications."""

    serializer_class = s.PhcNotificationSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        return scoping.recipient_notifications(_user_id(self.request))
