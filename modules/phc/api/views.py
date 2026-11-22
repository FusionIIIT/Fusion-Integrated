"""DRF Views for PHC module."""
from decimal import Decimal
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasPermission, IsAuthenticatedPrincipal
from modules.directory.contracts import get_users
from modules.phc.domain.errors import (
    ClaimImmutableError,
    IneligibleClaimantError,
    InsufficientStockError,
    InvalidStateTransitionError,
    PrescriptionRequiredError,
    RequisitionNotApprovedError,
    SubmissionWindowExpiredError,
    UnauthorizedRecordAccessError,
)
from modules.phc.api.serializers import (
    AmbulanceLogSerializer,
    DoctorAttendanceSerializer,
    DoctorScheduleSerializer,
    DoctorSerializer,
    HealthAnnouncementSerializer,
    InventoryItemSerializer,
    PatientVisitCreateSerializer,
    PatientVisitSerializer,
    PHCAuditTrailSerializer,
    PHCNotificationSerializer,
    PrescriptionCreateSerializer,
    PrescriptionSerializer,
    ProcurementRequisitionSerializer,
    ProcurementRequisitionSubmitSerializer,
    ReimbursementClaimSerializer,
    ReimbursementClaimSubmitSerializer,
    StockAdjustmentCreateSerializer,
    StockAdjustmentSerializer,
)
from modules.phc.selectors.ambulance import list_ambulance_logs
from modules.phc.selectors.announcements import list_active_announcements, list_all_announcements
from modules.phc.selectors.audit import list_audit_trail_events
from modules.phc.selectors.doctors import (
    get_all_doctors,
    get_all_schedules,
    get_patient_doctor_availability,
    get_today_attendance,
)
from modules.phc.selectors.inventory import (
    get_inventory_item,
    get_procurement_requisition,
    list_inventory_items,
    list_procurement_requisitions,
    list_stock_adjustments,
)
from modules.phc.selectors.notifications import count_unread_notifications, get_user_notifications
from modules.phc.selectors.patient_records import (
    get_patient_medical_history,
    get_patient_prescriptions,
    get_patient_visit_by_id,
    search_patient_records_staff,
)
from modules.phc.selectors.reimbursement import (
    get_reimbursement_claim_detail,
    get_review_queue_for_stage,
    get_user_reimbursement_claims,
)
from modules.phc.services.ambulance import log_ambulance_usage
from modules.phc.services.announcements import publish_health_announcement
from modules.phc.services.doctors import (
    create_doctor,
    create_or_update_schedule,
    mark_attendance,
    publish_schedules,
)
from modules.phc.services.inventory import (
    adjust_stock,
    create_or_update_item,
    decide_procurement_requisition,
    fulfill_procurement_requisition,
    submit_procurement_requisition,
)
from modules.phc.services.patient_records import create_patient_visit, create_prescription
from modules.phc.services.reimbursement import (
    decide_claim_sanction,
    process_claim_payment,
    review_claim_phc,
    submit_reimbursement_claim,
    verify_claim_accounts,
)
from modules.phc.services.reports import generate_administrative_report


# ==============================================================================
# 1. Doctor Schedule & Real-Time Availability (CFR-PHC-001, PHC-BR-01)
# ==============================================================================

class DoctorAvailabilityView(APIView):
    """Patient-facing combined weekly schedule and live attendance (AFR-PHC-001; PHC-BR-01; UC-PHC-01)."""
    permission_classes = [HasPermission("phc.doctor_schedule.view")]

    def get(self, request):
        data = get_patient_doctor_availability()
        return Response(data)


class DoctorManageView(APIView):
    """Doctor management for PHC Staff (UC-PHC-07)."""
    permission_classes = [HasPermission("phc.doctor_schedule.manage")]

    def get(self, request):
        doctors = get_all_doctors()
        return Response(DoctorSerializer(doctors, many=True).data)

    def post(self, request):
        serializer = DoctorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = create_doctor(**serializer.validated_data)
        return Response(DoctorSerializer(doc).data, status=status.HTTP_201_CREATED)


class DoctorScheduleManageView(APIView):
    """Create, maintain and publish weekly schedules (AFR-PHC-002, 004, 005; UC-PHC-07, 22)."""
    permission_classes = [HasPermission("phc.doctor_schedule.manage")]

    def get(self, request):
        schedules = get_all_schedules()
        return Response(DoctorScheduleSerializer(schedules, many=True).data)

    def post(self, request):
        doctor_id = request.data.get("doctor_id")
        day_of_week = request.data.get("day_of_week")
        start_time = request.data.get("start_time")
        end_time = request.data.get("end_time")
        room_number = request.data.get("room_number", "")
        is_published = bool(request.data.get("is_published", False))
        schedule_id = request.data.get("schedule_id")

        if not all([doctor_id, day_of_week, start_time, end_time]):
            return Response({"error": "doctor_id, day_of_week, start_time, and end_time are required."}, status=status.HTTP_400_BAD_REQUEST)

        sched = create_or_update_schedule(
            doctor_id=int(doctor_id),
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            room_number=room_number,
            is_published=is_published,
            schedule_id=int(schedule_id) if schedule_id else None,
        )
        return Response(DoctorScheduleSerializer(sched).data, status=status.HTTP_201_CREATED)


class DoctorSchedulePublishView(APIView):
    """Publish schedules for patient visibility (AFR-PHC-005, UC-PHC-22)."""
    permission_classes = [HasPermission("phc.doctor_schedule.manage")]

    def post(self, request):
        schedule_ids = request.data.get("schedule_ids", [])
        if not schedule_ids:
            return Response({"error": "schedule_ids list required."}, status=status.HTTP_400_BAD_REQUEST)
        count = publish_schedules(schedule_ids)
        return Response({"published_count": count})


class DoctorAttendanceView(APIView):
    """Mark and view doctor real-time attendance (AFR-PHC-003, UC-PHC-08)."""
    permission_classes = [HasPermission("phc.doctor_schedule.manage")]

    def get(self, request):
        records = get_today_attendance()
        return Response(DoctorAttendanceSerializer(records, many=True).data)

    def post(self, request):
        doctor_id = request.data.get("doctor_id")
        attendance_status = request.data.get("status")
        remarks = request.data.get("remarks", "")
        if not doctor_id or not attendance_status:
            return Response({"error": "doctor_id and status are required."}, status=status.HTTP_400_BAD_REQUEST)

        principal = request.principal
        record = mark_attendance(
            doctor_id=int(doctor_id),
            status=attendance_status,
            marked_by_user_id=principal.user_id,
            remarks=remarks,
        )
        return Response(DoctorAttendanceSerializer(record).data)


# ==============================================================================
# 2. Patient Records & Prescriptions (CFR-PHC-002, PHC-BR-02)
# ==============================================================================

class PatientMedicalHistoryView(APIView):
    """Patient read-only access to own medical visits (AFR-PHC-009, 012; PHC-BR-02; UC-PHC-02)."""
    permission_classes = [HasPermission("phc.patient_record.view_self")]

    def get(self, request):
        patient_id = request.principal.user_id
        visits = get_patient_medical_history(patient_id)
        return Response(PatientVisitSerializer(visits, many=True).data)


class PatientPrescriptionsView(APIView):
    """Patient read-only access to own prescriptions (AFR-PHC-010, 012; PHC-BR-02; UC-PHC-02)."""
    permission_classes = [HasPermission("phc.patient_record.view_self")]

    def get(self, request):
        patient_id = request.principal.user_id
        prescriptions = get_patient_prescriptions(patient_id)
        return Response(PrescriptionSerializer(prescriptions, many=True).data)


class PatientRecordDownloadView(APIView):
    """Patient PDF summary of own medical records (AFR-PHC-011; UC-PHC-03)."""
    permission_classes = [HasPermission("phc.patient_record.download_self")]

    def get(self, request):
        patient_id = request.principal.user_id
        visits = get_patient_medical_history(patient_id)
        prescriptions = get_patient_prescriptions(patient_id)

        # Structure payload representing the downloadable medical record
        summary = {
            "patient_user_id": patient_id,
            "patient_name": request.principal.display_name,
            "patient_username": request.principal.username,
            "total_visits": len(visits),
            "total_prescriptions": len(prescriptions),
            "visits": PatientVisitSerializer(visits, many=True).data,
            "prescriptions": PrescriptionSerializer(prescriptions, many=True).data,
            "document_format": "PDF-JSON",
        }
        return Response(summary)


class PatientVisitsManageView(APIView):
    """PHC Staff patient record search and consultation creation (AFR-PHC-006, 007; UC-PHC-06)."""
    permission_classes = [HasPermission("phc.patient_record.manage")]

    def get(self, request):
        q = request.query_params.get("q", "")
        visits = search_patient_records_staff(query=q)
        return Response(PatientVisitSerializer(visits, many=True).data)

    def post(self, request):
        serializer = PatientVisitCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = request.principal

        visit = create_patient_visit(
            patient_user_id=data["patient_user_id"],
            doctor_id=data.get("doctor_id"),
            visit_date=data.get("visit_date"),
            symptoms=data["symptoms"],
            diagnosis=data["diagnosis"],
            notes=data.get("notes", ""),
            created_by_user_id=principal.user_id,
            created_by_username=principal.username,
        )
        return Response(PatientVisitSerializer(visit).data, status=status.HTTP_201_CREATED)


class PrescriptionManageView(APIView):
    """PHC Staff digitizes physical prescription linked to a visit (AFR-PHC-008; UC-PHC-06)."""
    permission_classes = [HasPermission("phc.patient_record.manage")]

    def post(self, request):
        serializer = PrescriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = request.principal

        prescription = create_prescription(
            visit_id=data["visit_id"],
            prescription_number=data["prescription_number"],
            prescribed_date=data.get("prescribed_date"),
            medicines_prescribed=data["medicines_prescribed"],
            scanned_document_url=data.get("scanned_document_url", ""),
            notes=data.get("notes", ""),
            created_by_user_id=principal.user_id,
            created_by_username=principal.username,
        )
        return Response(PrescriptionSerializer(prescription).data, status=status.HTTP_201_CREATED)


# ==============================================================================
# 3. Medical Bill Reimbursement (CFR-PHC-003, 004, 005)
# ==============================================================================

class ReimbursementClaimSubmitView(APIView):
    """Employee reimbursement claim submission (AFR-PHC-013, 014, 015, 016; UC-PHC-04; BR-PHC-04, 05, 06)."""
    permission_classes = [HasPermission("phc.reimbursement.create")]

    def post(self, request):
        serializer = ReimbursementClaimSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = request.principal

        try:
            claim = submit_reimbursement_claim(
                claimant_user_id=principal.user_id,
                claimant_kind=principal.kind,
                claimant_username=principal.username,
                prescription_id=data["prescription_id"],
                expense_date=data["expense_date"],
                amount_claimed=data["amount_claimed"],
                bills_document_url=data.get("bills_document_url", ""),
                remarks=data.get("remarks", ""),
            )
            return Response(ReimbursementClaimSerializer(claim).data, status=status.HTTP_201_CREATED)
        except IneligibleClaimantError as e:
            return Response({"error": str(e), "code": "INELIGIBLE_CLAIMANT"}, status=status.HTTP_403_FORBIDDEN)
        except PrescriptionRequiredError as e:
            return Response({"error": str(e), "code": "PRESCRIPTION_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
        except SubmissionWindowExpiredError as e:
            return Response({"error": str(e), "code": "SUBMISSION_WINDOW_EXPIRED"}, status=status.HTTP_400_BAD_REQUEST)


class ReimbursementClaimTrackingView(APIView):
    """Employee view of own claims and status history (AFR-PHC-022; UC-PHC-05)."""
    permission_classes = [HasPermission("phc.reimbursement.view_self")]

    def get(self, request):
        claims = get_user_reimbursement_claims(request.principal.user_id)
        return Response(ReimbursementClaimSerializer(claims, many=True).data)


class ReimbursementClaimDetailView(APIView):
    """Detailed view of a claim and action audit history (AFR-PHC-022)."""
    permission_classes = [IsAuthenticatedPrincipal]

    def get(self, request, pk):
        is_staff = request.principal.has_any_permission(
            "phc.reimbursement.review", "phc.reimbursement.verify", "phc.reimbursement.sanction", "phc.reimbursement.pay"
        )
        try:
            claim = get_reimbursement_claim_detail(
                claim_id=pk,
                requesting_user_id=request.principal.user_id,
                is_staff=is_staff,
            )
            return Response(ReimbursementClaimSerializer(claim).data)
        except PermissionError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)


class ReimbursementReviewQueueView(APIView):
    """Processing queue for claims across workflow stages (AFR-PHC-017)."""
    permission_classes = [HasPermission("phc.reimbursement.review")]

    def get(self, request):
        stage = request.query_params.get("stage")
        claims = get_review_queue_for_stage(stage=stage)
        return Response(ReimbursementClaimSerializer(claims, many=True).data)


class ReimbursementReviewForwardView(APIView):
    """PHC Staff review -> forwards to Accounts & Audit (AFR-PHC-018; UC-PHC-15)."""
    permission_classes = [HasPermission("phc.reimbursement.review")]

    def post(self, request, pk):
        comments = request.data.get("comments", "")
        principal = request.principal
        try:
            claim = review_claim_phc(
                claim_id=pk,
                actor_user_id=principal.user_id,
                actor_username=principal.username,
                comments=comments,
            )
            return Response(ReimbursementClaimSerializer(claim).data)
        except InvalidStateTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReimbursementVerifyView(APIView):
    """Accounts & Audit financial verification -> forwards to Approver (AFR-PHC-019; UC-PHC-19)."""
    permission_classes = [HasPermission("phc.reimbursement.verify")]

    def post(self, request, pk):
        amount = request.data.get("amount_verified")
        comments = request.data.get("comments", "")
        principal = request.principal
        amount_dec = Decimal(str(amount)) if amount is not None else None
        try:
            claim = verify_claim_accounts(
                claim_id=pk,
                actor_user_id=principal.user_id,
                actor_username=principal.username,
                amount_verified=amount_dec,
                comments=comments,
            )
            return Response(ReimbursementClaimSerializer(claim).data)
        except InvalidStateTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReimbursementSanctionView(APIView):
    """Approving Authority sanction decision: approve or reject (AFR-PHC-020; UC-PHC-20; BR-PHC-14)."""
    permission_classes = [HasPermission("phc.reimbursement.sanction")]

    def post(self, request, pk):
        decision = request.data.get("decision")  # "approve" or "reject"
        sanctioned_amount = request.data.get("sanctioned_amount")
        comments = request.data.get("comments", "")
        if decision not in ("approve", "reject"):
            return Response({"error": "decision must be 'approve' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

        approve = (decision == "approve")
        principal = request.principal
        amount_dec = Decimal(str(sanctioned_amount)) if sanctioned_amount is not None else None

        try:
            claim = decide_claim_sanction(
                claim_id=pk,
                approve=approve,
                actor_user_id=principal.user_id,
                actor_username=principal.username,
                sanctioned_amount=amount_dec,
                comments=comments,
            )
            return Response(ReimbursementClaimSerializer(claim).data)
        except InvalidStateTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReimbursementPaymentView(APIView):
    """Accounts & Audit payment completion -> marks Reimbursed (AFR-PHC-021; UC-PHC-21)."""
    permission_classes = [HasPermission("phc.reimbursement.pay")]

    def post(self, request, pk):
        payment_reference = request.data.get("payment_reference", "")
        comments = request.data.get("comments", "")
        principal = request.principal
        try:
            claim = process_claim_payment(
                claim_id=pk,
                actor_user_id=principal.user_id,
                actor_username=principal.username,
                payment_reference=payment_reference,
                comments=comments,
            )
            return Response(ReimbursementClaimSerializer(claim).data)
        except InvalidStateTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# 4. Inventory & Procurement Requisitions (CFR-PHC-006, CFR-PHC-007)
# ==============================================================================

class InventoryItemListView(APIView):
    """Inventory item catalog view and addition (AFR-PHC-024)."""
    permission_classes = [HasPermission("phc.inventory.view")]

    def get(self, request):
        category = request.query_params.get("category")
        items = list_inventory_items(category=category)
        return Response(InventoryItemSerializer(items, many=True).data)

    def post(self, request):
        if not request.principal.has_permission("phc.inventory.adjust"):
            return Response({"error": "Permission phc.inventory.adjust required to create/edit items."}, status=status.HTTP_403_FORBIDDEN)
        serializer = InventoryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = create_or_update_item(
            item_code=serializer.validated_data["item_code"],
            name=serializer.validated_data["name"],
            category=serializer.validated_data.get("category", "Medicine"),
            reorder_threshold=serializer.validated_data.get("reorder_threshold", 10),
            unit=serializer.validated_data.get("unit", "units"),
            description=serializer.validated_data.get("description", ""),
            item_id=request.data.get("item_id"),
        )
        return Response(InventoryItemSerializer(item).data, status=status.HTTP_201_CREATED)


class InventoryStockAdjustmentView(APIView):
    """Stock adjustment with automatic low-stock evaluation (AFR-PHC-024, 025, 026; BR-PHC-07, 09; UC-PHC-09)."""
    permission_classes = [HasPermission("phc.inventory.adjust")]

    def get(self, request):
        item_id = request.query_params.get("item_id")
        adjustments = list_stock_adjustments(item_id=int(item_id) if item_id else None)
        return Response(StockAdjustmentSerializer(adjustments, many=True).data)

    def post(self, request):
        serializer = StockAdjustmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = request.principal

        try:
            item = adjust_stock(
                item_id=data["item_id"],
                adjustment_type=data["adjustment_type"],
                quantity=data["quantity"],
                reason=data["reason"],
                actor_user_id=principal.user_id,
                actor_username=principal.username,
            )
            return Response(InventoryItemSerializer(item).data)
        except InsufficientStockError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProcurementRequisitionView(APIView):
    """Procurement requisition list and creation (AFR-PHC-027, 028; UC-PHC-10; CW-PHC-02)."""
    permission_classes = [HasPermission("phc.requisition.create")]

    def get(self, request):
        status_param = request.query_params.get("status")
        requisitions = list_procurement_requisitions(status=status_param)
        return Response(ProcurementRequisitionSerializer(requisitions, many=True).data)

    def post(self, request):
        serializer = ProcurementRequisitionSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = request.principal

        req = submit_procurement_requisition(
            originator_user_id=principal.user_id,
            originator_username=principal.username,
            justification=data["justification"],
            items_data=data["items"],
        )
        return Response(ProcurementRequisitionSerializer(req).data, status=status.HTTP_201_CREATED)


class ProcurementRequisitionDecisionView(APIView):
    """Approving Authority decision on procurement requisition (AFR-PHC-029, 030; UC-PHC-16; BR-PHC-10, 11)."""
    permission_classes = [HasPermission("phc.requisition.decide")]

    def post(self, request, pk):
        decision = request.data.get("decision")  # "approve" or "reject"
        remarks = request.data.get("remarks", "")
        if decision not in ("approve", "reject"):
            return Response({"error": "decision must be 'approve' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

        approve = (decision == "approve")
        principal = request.principal
        try:
            req = decide_procurement_requisition(
                requisition_id=pk,
                approve=approve,
                actor_user_id=principal.user_id,
                actor_username=principal.username,
                remarks=remarks,
            )
            return Response(ProcurementRequisitionSerializer(req).data)
        except InvalidStateTransitionError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProcurementRequisitionFulfillView(APIView):
    """PHC Staff marks delivered approved requisition as Fulfilled (AFR-PHC-031; UC-PHC-14; BR-PHC-10)."""
    permission_classes = [HasPermission("phc.requisition.fulfill")]

    def post(self, request, pk):
        principal = request.principal
        try:
            req = fulfill_procurement_requisition(
                requisition_id=pk,
                actor_user_id=principal.user_id,
                actor_username=principal.username,
            )
            return Response(ProcurementRequisitionSerializer(req).data)
        except RequisitionNotApprovedError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# 5. Ambulance & Announcements (CFR-PHC-008, CFR-PHC-009)
# ==============================================================================

class AmbulanceLogView(APIView):
    """Ambulance usage logging and viewing (AFR-PHC-032; UC-PHC-11)."""
    permission_classes = [HasPermission("phc.ambulance.manage")]

    def get(self, request):
        logs = list_ambulance_logs()
        return Response(AmbulanceLogSerializer(logs, many=True).data)

    def post(self, request):
        serializer = AmbulanceLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = request.principal

        log = log_ambulance_usage(
            patient_name=data["patient_name"],
            destination=data["destination"],
            departure_time=data["departure_time"],
            driver_name=data["driver_name"],
            recorded_by_user_id=principal.user_id,
            patient_user_id=data.get("patient_user_id"),
            return_time=data.get("return_time"),
            reason=data.get("reason", ""),
        )
        return Response(AmbulanceLogSerializer(log).data, status=status.HTTP_201_CREATED)


class HealthAnnouncementView(APIView):
    """Health advisory view and publishing (AFR-PHC-033; UC-PHC-12)."""
    permission_classes = [HasPermission("phc.announcement.view")]

    def get(self, request):
        announcements = list_active_announcements()
        return Response(HealthAnnouncementSerializer(announcements, many=True).data)

    def post(self, request):
        if not request.principal.has_permission("phc.announcement.manage"):
            return Response({"error": "Permission phc.announcement.manage required to publish advisories."}, status=status.HTTP_403_FORBIDDEN)
        serializer = HealthAnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        principal = request.principal

        announcement = publish_health_announcement(
            title=data["title"],
            content=data["content"],
            priority=data.get("priority", "Normal"),
            published_by_user_id=principal.user_id,
        )
        return Response(HealthAnnouncementSerializer(announcement).data, status=status.HTTP_201_CREATED)


# ==============================================================================
# 6. Administrative Reporting & Anonymization (CFR-PHC-010, PHC-BR-12)
# ==============================================================================

class PHCReportView(APIView):
    """Anonymized administrative reporting (AFR-PHC-034, 035; PHC-BR-12; UC-PHC-13)."""
    permission_classes = [HasPermission("phc.report.view")]

    def get(self, request):
        report_type = request.query_params.get("type", "demographics")
        try:
            report_data = generate_administrative_report(report_type)
            return Response(report_data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# 7. Audit Trail & In-App Notifications (CFR-PHC-012, PHC-BR-09, 07, 11, 13)
# ==============================================================================

class PHCAuditTrailView(APIView):
    """Immutable audit trail of sensitive patient, inventory and claim actions (AFR-PHC-037; PHC-BR-09)."""
    permission_classes = [HasPermission("phc.audit.view")]

    def get(self, request):
        target_type = request.query_params.get("target_type")
        events = list_audit_trail_events(target_type=target_type)
        return Response(PHCAuditTrailSerializer(events, many=True).data)


class PHCNotificationView(APIView):
    """In-system notifications for low stock, requisitions and claim updates (BR-PHC-07, 11, 13)."""
    permission_classes = [IsAuthenticatedPrincipal]

    def get(self, request):
        user_id = request.principal.user_id
        notifications = get_user_notifications(user_id)
        unread_count = count_unread_notifications(user_id)
        return Response({
            "unread_count": unread_count,
            "notifications": PHCNotificationSerializer(notifications, many=True).data,
        })
