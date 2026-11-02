"""API views for Hostel Management (HM)."""

from __future__ import annotations

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from modules.hostel import selectors
from modules.hostel.api import permissions as p
from modules.hostel.api import serializers as s
from modules.hostel.domain.errors import HostelDomainError
from modules.hostel.models import (
    ExtendedStayRequest,
    Hostel,
    HostelComplaint,
    HostelFine,
    HostelLeave,
    HostelNotification,
    HostelRoleBinding,
    Room,
    RoomAllotment,
)
from modules.hostel.services import (
    allotment_service,
    attendance_service,
    complaint_service,
    extended_stay_service,
    fine_service,
    guest_room_service,
    hostel_service,
    inventory_service,
    leave_service,
    notice_service,
    report_service,
    room_service,
    security_service,
)

# --- Hostel Master & Role Bindings (CFR-HM-001, 002) ---


class HostelListCreateView(generics.ListCreateAPIView):
    serializer_class = s.HostelSerializer
    permission_classes = [p.MODULE, p.P_HOSTEL_VIEW]

    def get_queryset(self):
        return selectors.visible_hostels(self.request.principal)

    def perform_create(self, serializer):
        if not self.request.principal.has_permission("hostel.hostel.manage"):
            raise BadRequestError("Permission denied to create hostels")
        try:
            instance = hostel_service.create_hostel(
                name=serializer.validated_data["name"],
                code=serializer.validated_data["code"],
                capacity=serializer.validated_data.get("capacity", 0),
                gender=serializer.validated_data.get("gender", "boys"),
                description=serializer.validated_data.get("description", ""),
                creator_user_id=self.request.principal.user_id,
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


class HostelDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = s.HostelSerializer
    permission_classes = [p.MODULE, p.P_HOSTEL_VIEW]

    def get_queryset(self):
        return selectors.visible_hostels(self.request.principal)


class HostelToggleActiveView(APIView):
    permission_classes = [p.MODULE, p.P_HOSTEL_MANAGE]

    def post(self, request, pk: int):
        is_active = request.data.get("is_active", True)
        try:
            h = hostel_service.set_hostel_active_status(
                hostel_id=pk, is_active=is_active, actor_user_id=request.principal.user_id
            )
            return Response(s.HostelSerializer(h).data)
        except Hostel.DoesNotExist as exc:
            raise NotFoundError("Hostel not found") from exc


class HostelRoleBindingListCreateView(generics.ListCreateAPIView):
    serializer_class = s.HostelRoleBindingSerializer
    permission_classes = [p.MODULE, p.P_HOSTEL_VIEW]

    def get_queryset(self):
        qs = HostelRoleBinding.objects.select_related("hostel")
        hostel_id = self.request.query_params.get("hostel_id")
        if hostel_id:
            qs = qs.filter(hostel_id=hostel_id)
        if selectors.is_super_admin(self.request.principal):
            return qs
        assigned_ids = selectors.get_assigned_hostel_ids(self.request.principal)
        return qs.filter(hostel_id__in=assigned_ids)

    def perform_create(self, serializer):
        if not self.request.principal.has_permission("hostel.role_binding.manage"):
            raise BadRequestError("Permission denied to assign hostel role bindings")
        try:
            instance = hostel_service.assign_role_binding(
                hostel_id=serializer.validated_data["hostel"].id,
                user_id=serializer.validated_data["user_id"],
                role=serializer.validated_data["role"],
                start_date=serializer.validated_data.get("start_date"),
                end_date=serializer.validated_data.get("end_date"),
                assigner_user_id=self.request.principal.user_id,
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


class HostelRoleBindingDeactivateView(APIView):
    permission_classes = [p.MODULE, p.P_ROLE_MANAGE]

    def post(self, request, pk: int):
        try:
            b = hostel_service.deactivate_role_binding(binding_id=pk)
            return Response(s.HostelRoleBindingSerializer(b).data)
        except HostelRoleBinding.DoesNotExist as exc:
            raise NotFoundError("Role binding not found") from exc


# --- Rooms (CFR-HM-004, 006) ---


class RoomListCreateView(generics.ListCreateAPIView):
    serializer_class = s.RoomSerializer
    permission_classes = [p.MODULE, p.P_ROOM_VIEW]

    def get_queryset(self):
        hostel_id = self.request.query_params.get("hostel_id")
        return selectors.visible_rooms(self.request.principal, hostel_id=hostel_id)

    def perform_create(self, serializer):
        if not self.request.principal.has_permission("hostel.room.manage"):
            raise BadRequestError("Permission denied to create rooms")
        try:
            instance = room_service.create_room(
                hostel_id=serializer.validated_data["hostel"].id,
                room_number=serializer.validated_data["room_number"],
                floor=serializer.validated_data.get("floor", 0),
                capacity=serializer.validated_data.get("capacity", 2),
                status=serializer.validated_data.get("status", "available"),
                remarks=serializer.validated_data.get("remarks", ""),
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


class RoomStatusUpdateView(APIView):
    permission_classes = [p.MODULE, p.P_ROOM_MANAGE]

    def patch(self, request, pk: int):
        status_val = request.data.get("status")
        remarks = request.data.get("remarks", "")
        if not status_val:
            raise BadRequestError("Status is required")
        try:
            room = room_service.update_room_status(pk, status=status_val, remarks=remarks)
            return Response(s.RoomSerializer(room).data)
        except Room.DoesNotExist as exc:
            raise NotFoundError("Room not found") from exc


class RoomExchangeView(APIView):
    permission_classes = [p.MODULE, p.P_ROOM_MANAGE]

    def post(self, request):
        req_student = request.data.get("requester_student_user_id")
        tgt_student = request.data.get("target_student_user_id")
        reason = request.data.get("reason", "")
        if not req_student or not tgt_student:
            raise BadRequestError("Both requester and target students are required")
        try:
            exc = room_service.execute_room_exchange(
                requester_student_user_id=int(req_student),
                target_student_user_id=int(tgt_student),
                reason=reason,
                caretaker_user_id=request.principal.user_id,
            )
            return Response(s.RoomExchangeRequestSerializer(exc).data)
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


# --- Accommodation Requests & Allotment (CFR-HM-003..005) ---


class AccommodationRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = s.AccommodationRequestSerializer
    permission_classes = [p.MODULE, p.P_ACCOM_VIEW_SELF]

    def get_queryset(self):
        hostel_id = self.request.query_params.get("hostel_id")
        return selectors.visible_accommodation_requests(self.request.principal, hostel_id=hostel_id)

    def perform_create(self, serializer):
        try:
            pref = serializer.validated_data.get("preferred_hostel")
            instance = allotment_service.submit_accommodation_request(
                student_user_id=self.request.principal.user_id,
                preferred_hostel_id=pref.id if pref else None,
                room_type_preference=serializer.validated_data.get("room_type_preference", ""),
                academic_year=serializer.validated_data.get("academic_year", "2026-27"),
                semester=serializer.validated_data.get("semester", 1),
                reason=serializer.validated_data.get("reason", ""),
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


class RoomAllotmentListCreateView(generics.ListCreateAPIView):
    serializer_class = s.RoomAllotmentSerializer
    permission_classes = [p.MODULE, p.P_ACCOM_VIEW_SELF]

    def get_queryset(self):
        hostel_id = self.request.query_params.get("hostel_id")
        return selectors.visible_allotments(self.request.principal, hostel_id=hostel_id)

    def perform_create(self, serializer):
        if not self.request.principal.has_permission("hostel.accommodation.allot"):
            raise BadRequestError("Permission denied to record allotments")
        try:
            req_id = self.request.data.get("linked_request_id")
            instance = allotment_service.allot_room(
                student_user_id=serializer.validated_data["student_user_id"],
                hostel_id=serializer.validated_data["hostel"].id,
                room_id=serializer.validated_data["room"].id,
                bed_number=serializer.validated_data.get("bed_number", "A"),
                allotment_date=serializer.validated_data.get("allotment_date"),
                allotted_by_user_id=self.request.principal.user_id,
                linked_request_id=int(req_id) if req_id else None,
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


class RoomAllotmentVacateView(APIView):
    permission_classes = [p.MODULE, p.P_ROOM_MANAGE]

    def post(self, request, pk: int):
        remarks = request.data.get("vacation_remarks", "")
        clearance = request.data.get("vacation_clearance_status", True)
        try:
            alt = allotment_service.vacate_room(
                allotment_id=pk,
                vacation_clearance_status=clearance,
                vacation_remarks=remarks,
                actor_user_id=request.principal.user_id,
            )
            return Response(s.RoomAllotmentSerializer(alt).data)
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


# --- Attendance (CFR-HM-009, 010) ---


class AttendanceRecordListCreateView(generics.ListCreateAPIView):
    serializer_class = s.AttendanceRecordSerializer
    permission_classes = [p.MODULE, p.P_ATTENDANCE_VIEW]

    def get_queryset(self):
        hostel_id = self.request.query_params.get("hostel_id")
        return selectors.visible_attendance(self.request.principal, hostel_id=hostel_id)

    def post(self, request, *args, **kwargs):
        if not request.principal.has_permission("hostel.attendance.record"):
            raise BadRequestError("Permission denied to record attendance")
        hostel_id = request.data.get("hostel_id")
        att_date = request.data.get("date")
        records = request.data.get("records", [])
        if not hostel_id or not att_date:
            raise BadRequestError("Hostel ID and Date are required")
        try:
            created = attendance_service.record_daily_attendance(
                hostel_id=int(hostel_id),
                attendance_date=att_date,
                student_attendance_list=records,
                recorded_by_user_id=request.principal.user_id,
            )
            return Response(
                s.AttendanceRecordSerializer(created, many=True).data,
                status=status.HTTP_201_CREATED,
            )
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


# --- Leaves (CFR-HM-012..014) ---


class HostelLeaveListCreateView(generics.ListCreateAPIView):
    serializer_class = s.HostelLeaveSerializer
    permission_classes = [p.MODULE, p.P_LEAVE_VIEW]

    def get_queryset(self):
        hostel_id = self.request.query_params.get("hostel_id")
        return selectors.visible_leaves(self.request.principal, hostel_id=hostel_id)

    def perform_create(self, serializer):
        try:
            instance = leave_service.submit_leave_request(
                student_user_id=self.request.principal.user_id,
                hostel_id=serializer.validated_data["hostel"].id,
                from_date=serializer.validated_data["from_date"],
                to_date=serializer.validated_data["to_date"],
                reason=serializer.validated_data["reason"],
                leave_type=serializer.validated_data.get("leave_type", "home"),
                destination=serializer.validated_data.get("destination", ""),
                emergency_contact=serializer.validated_data.get("emergency_contact", ""),
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


class HostelLeaveDecideView(APIView):
    permission_classes = [p.MODULE, p.P_LEAVE_REVIEW]

    def post(self, request, pk: int):
        decision = request.data.get("decision")  # 'approved' or 'rejected'
        remarks = request.data.get("remarks", "")
        if not decision:
            raise BadRequestError("Decision is required")
        try:
            leave = leave_service.decide_leave_request(
                leave_id=pk,
                decision=decision,
                caretaker_user_id=request.principal.user_id,
                remarks=remarks,
            )
            return Response(s.HostelLeaveSerializer(leave).data)
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


# --- Complaints (CFR-HM-015..018) ---


class HostelComplaintListCreateView(generics.ListCreateAPIView):
    serializer_class = s.HostelComplaintSerializer
    permission_classes = [p.MODULE, p.P_COMPLAINT_VIEW]

    def get_queryset(self):
        hostel_id = self.request.query_params.get("hostel_id")
        return selectors.visible_complaints(self.request.principal, hostel_id=hostel_id)

    def perform_create(self, serializer):
        try:
            instance = complaint_service.submit_complaint(
                student_user_id=self.request.principal.user_id,
                hostel_id=serializer.validated_data["hostel"].id,
                title=serializer.validated_data["title"],
                description=serializer.validated_data["description"],
                location=serializer.validated_data["location"],
                category=serializer.validated_data.get("category", "electrical"),
                severity=serializer.validated_data.get("severity", "medium"),
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


class HostelComplaintUpdateView(APIView):
    permission_classes = [p.MODULE, p.P_COMPLAINT_VIEW]

    def patch(self, request, pk: int):
        target_status = request.data.get("status")
        assigned_worker = request.data.get("assigned_worker", "")
        resolution_notes = request.data.get("resolution_notes", "")
        if not target_status:
            raise BadRequestError("Target status is required")

        actor_role = "student"
        if request.principal.has_permission("hostel.complaint.escalate"):
            actor_role = "warden"
        elif request.principal.has_permission("hostel.complaint.manage"):
            actor_role = "caretaker"

        try:
            cmp = complaint_service.update_complaint_status(
                complaint_id=pk,
                target_status=target_status,
                actor_role=actor_role,
                actor_user_id=request.principal.user_id,
                assigned_worker=assigned_worker,
                resolution_notes=resolution_notes,
            )
            return Response(s.HostelComplaintSerializer(cmp).data)
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


# --- Guest Rooms (CFR-HM-019..021) ---


class GuestRoomBookingListCreateView(generics.ListCreateAPIView):
    serializer_class = s.GuestRoomBookingSerializer
    permission_classes = [p.MODULE, p.P_GUEST_VIEW]

    def get_queryset(self):
        hostel_id = self.request.query_params.get("hostel_id")
        return selectors.visible_guest_room_bookings(self.request.principal, hostel_id=hostel_id)

    def perform_create(self, serializer):
        try:
            instance = guest_room_service.submit_guest_room_booking(
                student_user_id=self.request.principal.user_id,
                hostel_id=serializer.validated_data["hostel"].id,
                guest_name=serializer.validated_data["guest_name"],
                relationship=serializer.validated_data["relationship"],
                num_guests=serializer.validated_data.get("num_guests", 1),
                check_in_date=serializer.validated_data["check_in_date"],
                check_out_date=serializer.validated_data["check_out_date"],
                purpose=serializer.validated_data["purpose"],
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


class GuestRoomBookingDecideView(APIView):
    permission_classes = [p.MODULE, p.P_GUEST_MANAGE]

    def post(self, request, pk: int):
        decision = request.data.get("decision")
        allocated_room = request.data.get("allocated_room_number", "")
        charges = request.data.get("charges", 0.0)
        remarks = request.data.get("remarks", "")
        if not decision:
            raise BadRequestError("Decision is required")
        try:
            booking = guest_room_service.decide_guest_room_booking(
                booking_id=pk,
                decision=decision,
                caretaker_user_id=request.principal.user_id,
                allocated_room_number=allocated_room,
                charges=charges,
                remarks=remarks,
            )
            return Response(s.GuestRoomBookingSerializer(booking).data)
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


# --- Extended Stays (CFR-HM-022..024) ---


class ExtendedStayRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = s.ExtendedStayRequestSerializer
    permission_classes = [p.MODULE, p.P_EXTENDED_VIEW]

    def get_queryset(self):
        hostel_id = self.request.query_params.get("hostel_id")
        return selectors.visible_extended_stays(self.request.principal, hostel_id=hostel_id)

    def perform_create(self, serializer):
        try:
            instance = extended_stay_service.submit_extended_stay_request(
                student_user_id=self.request.principal.user_id,
                hostel_id=serializer.validated_data["hostel"].id,
                from_date=serializer.validated_data["from_date"],
                to_date=serializer.validated_data["to_date"],
                reason_type=serializer.validated_data.get("reason_type", "internship"),
                reason_details=serializer.validated_data.get("reason_details", ""),
                supporting_document_url=serializer.validated_data.get(
                    "supporting_document_url", ""
                ),
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


class ExtendedStayRequestDecideView(APIView):
    permission_classes = [p.MODULE, p.P_EXTENDED_REVIEW]

    def post(self, request, pk: int):
        decision = request.data.get("decision")
        charges = request.data.get("charge_amount", 0.0)
        deadline = request.data.get("payment_deadline")
        remarks = request.data.get("remarks", "")
        if not decision:
            raise BadRequestError("Decision is required")
        try:
            req = extended_stay_service.decide_extended_stay_request(
                request_id=pk,
                decision=decision,
                warden_user_id=request.principal.user_id,
                charge_amount=charges,
                payment_deadline=deadline,
                remarks=remarks,
            )
            return Response(s.ExtendedStayRequestSerializer(req).data)
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


class ExtendedStayComplianceView(APIView):
    permission_classes = [p.MODULE, p.P_EXTENDED_REVIEW]

    def patch(self, request, pk: int):
        status_val = request.data.get("compliance_status")
        remarks = request.data.get("remarks", "")
        if not status_val:
            raise BadRequestError("Compliance status is required")
        try:
            req = extended_stay_service.update_extended_stay_compliance(
                request_id=pk, compliance_status=status_val, remarks=remarks
            )
            return Response(s.ExtendedStayRequestSerializer(req).data)
        except ExtendedStayRequest.DoesNotExist as exc:
            raise NotFoundError("Extended stay request not found") from exc


# --- Fines (CFR-HM-025..027) ---


class HostelFineListCreateView(generics.ListCreateAPIView):
    serializer_class = s.HostelFineSerializer
    permission_classes = [p.MODULE, p.P_FINE_VIEW]

    def get_queryset(self):
        hostel_id = self.request.query_params.get("hostel_id")
        return selectors.visible_fines(self.request.principal, hostel_id=hostel_id)

    def perform_create(self, serializer):
        if not self.request.principal.has_permission("hostel.fine.record"):
            raise BadRequestError("Permission denied to record fines")
        try:
            instance = fine_service.record_fine(
                student_user_id=serializer.validated_data["student_user_id"],
                hostel_id=serializer.validated_data["hostel"].id,
                amount=serializer.validated_data["amount"],
                reason=serializer.validated_data["reason"],
                issued_date=serializer.validated_data.get("issued_date"),
                due_date=serializer.validated_data.get("due_date"),
                imposed_by_user_id=self.request.principal.user_id,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


class HostelFineStatusUpdateView(APIView):
    permission_classes = [p.MODULE, p.P_FINE_MANAGE]

    def patch(self, request, pk: int):
        status_val = request.data.get("status")
        receipt = request.data.get("receipt_reference", "")
        remarks = request.data.get("remarks", "")
        if not status_val:
            raise BadRequestError("Status is required")
        try:
            fine = fine_service.update_fine_status(
                fine_id=pk, status=status_val, receipt_reference=receipt, remarks=remarks
            )
            return Response(s.HostelFineSerializer(fine).data)
        except HostelFine.DoesNotExist as exc:
            raise NotFoundError("Fine record not found") from exc


# --- Inventory & Staff (CFR-HM-028) ---


class HostelInventoryListCreateView(generics.ListCreateAPIView):
    serializer_class = s.HostelInventorySerializer
    permission_classes = [p.MODULE, p.P_INVENTORY_MANAGE]

    def get_queryset(self):
        hostel_id = self.request.query_params.get("hostel_id")
        return selectors.visible_inventory(self.request.principal, hostel_id=hostel_id)

    def perform_create(self, serializer):
        try:
            instance = inventory_service.record_inventory_item(
                hostel_id=serializer.validated_data["hostel"].id,
                item_name=serializer.validated_data["item_name"],
                category=serializer.validated_data.get("category", "furniture"),
                quantity_total=serializer.validated_data.get("quantity_total", 0),
                quantity_functional=serializer.validated_data.get("quantity_functional", 0),
                quantity_damaged=serializer.validated_data.get("quantity_damaged", 0),
                location=serializer.validated_data.get("location", ""),
                last_inspected_at=serializer.validated_data.get("last_inspected_at"),
                remarks=serializer.validated_data.get("remarks", ""),
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


class HostelStaffListCreateView(generics.ListCreateAPIView):
    serializer_class = s.HostelStaffSerializer
    permission_classes = [p.MODULE, p.P_STAFF_MANAGE]

    def get_queryset(self):
        hostel_id = self.request.query_params.get("hostel_id")
        return selectors.visible_staff(self.request.principal, hostel_id=hostel_id)

    def perform_create(self, serializer):
        try:
            instance = inventory_service.record_staff_member(
                hostel_id=serializer.validated_data["hostel"].id,
                name=serializer.validated_data["name"],
                role=serializer.validated_data.get("role", "cleaner"),
                phone_number=serializer.validated_data.get("phone_number", ""),
                shift=serializer.validated_data.get("shift", "morning"),
                is_active=serializer.validated_data.get("is_active", True),
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


# --- Security Shifts (CFR-HM-029) ---


class SecurityShiftListCreateView(generics.ListCreateAPIView):
    serializer_class = s.SecurityShiftSerializer
    permission_classes = [p.MODULE, p.P_SECURITY_SCHEDULE]

    def get_queryset(self):
        hostel_id = self.request.query_params.get("hostel_id")
        return selectors.visible_security_shifts(self.request.principal, hostel_id=hostel_id)

    def perform_create(self, serializer):
        try:
            instance = security_service.schedule_security_shift(
                hostel_id=serializer.validated_data["hostel"].id,
                guard_name=serializer.validated_data["guard_name"],
                shift_date=serializer.validated_data["shift_date"],
                shift_type=serializer.validated_data.get("shift_type", "morning"),
                gate_location=serializer.validated_data.get("gate_location", "Main Gate"),
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


# --- Notices (CFR-HM-030) ---


class HostelNoticeListCreateView(generics.ListCreateAPIView):
    serializer_class = s.HostelNoticeSerializer
    permission_classes = [p.MODULE, p.P_NOTICE_VIEW]

    def get_queryset(self):
        hostel_id = self.request.query_params.get("hostel_id")
        return selectors.visible_notices(self.request.principal, hostel_id=hostel_id)

    def perform_create(self, serializer):
        if not self.request.principal.has_permission("hostel.notice.publish"):
            raise BadRequestError("Permission denied to publish notices")
        try:
            instance = notice_service.publish_notice(
                hostel_id=serializer.validated_data["hostel"].id,
                title=serializer.validated_data["title"],
                content=serializer.validated_data["content"],
                publisher_user_id=self.request.principal.user_id,
                target_audience=serializer.validated_data.get("target_audience", "all"),
                expires_at=serializer.validated_data.get("expires_at"),
            )
            serializer.instance = instance
        except HostelDomainError as e:
            raise BadRequestError(str(e)) from e


# --- Notifications (CFR-HM-033) ---


class HostelNotificationListView(generics.ListAPIView):
    serializer_class = s.HostelNotificationSerializer
    permission_classes = [p.MODULE]

    def get_queryset(self):
        return selectors.visible_notifications(self.request.principal)


class HostelNotificationMarkReadView(APIView):
    permission_classes = [p.MODULE]

    def post(self, request, pk: int):
        updated = HostelNotification.objects.filter(
            id=pk, recipient_user_id=request.principal.user_id
        ).update(is_read=True)
        return Response({"success": bool(updated)})


# --- Reports & Dashboards (CFR-HM-031, 032) ---


class HostelReportsView(APIView):
    permission_classes = [p.MODULE, p.P_REPORT_VIEW]

    def get(self, request):
        hostel_id_str = request.query_params.get("hostel_id")
        hostel_id = int(hostel_id_str) if hostel_id_str else None

        return Response(
            {
                "occupancy": report_service.get_hostel_occupancy_report(hostel_id),
                "attendance": report_service.get_hostel_attendance_report(hostel_id),
                "complaints": report_service.get_hostel_complaints_report(hostel_id),
                "fines": report_service.get_hostel_fines_report(hostel_id),
            }
        )


class HostelExecutiveSummaryView(APIView):
    permission_classes = [p.MODULE, p.P_REPORT_VIEW]

    def get(self, request):
        return Response(report_service.get_cross_hostel_executive_summary())


class HostelDashboardStatsView(APIView):
    permission_classes = [p.MODULE]

    def get(self, request):
        principal = request.principal
        assigned_ids = selectors.get_assigned_hostel_ids(principal)
        is_admin = selectors.is_super_admin(principal)

        my_allotment = (
            RoomAllotment.objects.filter(student_user_id=principal.user_id, status="active")
            .select_related("hostel", "room")
            .first()
        )

        my_pending_leaves = HostelLeave.objects.filter(
            student_user_id=principal.user_id, status="pending"
        ).count()

        my_open_complaints = HostelComplaint.objects.filter(
            student_user_id=principal.user_id, status__in=["open", "in_progress", "escalated"]
        ).count()

        my_pending_fines = HostelFine.objects.filter(
            student_user_id=principal.user_id, status="pending"
        ).count()

        data = {
            "is_admin": is_admin,
            "is_warden_or_caretaker": bool(assigned_ids),
            "assigned_hostels_count": len(assigned_ids),
            "my_allotment": s.RoomAllotmentSerializer(my_allotment).data if my_allotment else None,
            "my_pending_leaves": my_pending_leaves,
            "my_open_complaints": my_open_complaints,
            "my_pending_fines": my_pending_fines,
        }

        if is_admin or assigned_ids:
            h_id = assigned_ids[0] if assigned_ids else None
            data["operational_summary"] = report_service.get_cross_hostel_executive_summary()
            data["occupancy_report"] = report_service.get_hostel_occupancy_report(h_id)

        return Response(data)
