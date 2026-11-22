"""Hostel Management API Views.

Implements REST endpoints for all HM Use Cases with strict RBAC enforcement (BR-HM-005).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant
from modules.hostel.api import serializers as s
from modules.hostel.domain.errors import (
    CapacityExceededError,
    HostelDomainError,
    InvalidStateTransitionError,
    MandatoryFieldMissingError,
    NoticePermissionError,
    RoomNotAvailableError,
    ScopeBoundaryError,
    UnauthorizedHostelAccessError,
)
from modules.hostel.models import (
    AccommodationRequest,
    ExtendedStayRequest,
    GuestRoomBooking,
    Hostel,
    HostelComplaint,
    HostelNotification,
    HostelRoleBinding,
    LeaveRequest,
    Room,
    RoomAllotment,
)
from modules.hostel.selectors import hostel as sel
from modules.hostel.services import hostel as svc

MODULE = HasModuleGrant("hostel")


class BaseHostelView(APIView):
    permission_classes = [MODULE]

    @property
    def principal(self):
        return getattr(self.request, "principal", None)

    def handle_error(self, exc: Exception) -> Response:
        if isinstance(
            exc,
            (
                CapacityExceededError,
                RoomNotAvailableError,
                InvalidStateTransitionError,
                MandatoryFieldMissingError,
                NoticePermissionError,
                ScopeBoundaryError,
            ),
        ):
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if isinstance(exc, UnauthorizedHostelAccessError):
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        if isinstance(exc, HostelDomainError):
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- 1. Hostels & Role Bindings (HM-UC-001 to HM-UC-004) ---


class HostelListCreateView(BaseHostelView):
    def get(self, request):
        qs = sel.visible_hostels(self.principal)
        return Response(s.HostelSerializer(qs, many=True).data)

    def post(self, request):
        if not self.principal.has_permission("hostel.hostel.manage"):
            return Response(
                {"error": "Only Super Admin can create hostels."}, status=status.HTTP_403_FORBIDDEN
            )
        serializer = s.HostelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hostel = svc.create_hostel(**serializer.validated_data)
        return Response(s.HostelSerializer(hostel).data, status=status.HTTP_201_CREATED)


class HostelDetailView(BaseHostelView):
    def get(self, request, pk: int):
        hostel = get_object_or_404(Hostel, pk=pk)
        return Response(s.HostelSerializer(hostel).data)

    def patch(self, request, pk: int):
        if not self.principal.has_permission("hostel.hostel.manage"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        hostel = get_object_or_404(Hostel, pk=pk)
        if "is_active" in request.data:
            svc.set_hostel_active_status(hostel, bool(request.data["is_active"]))
        return Response(s.HostelSerializer(hostel).data)


class RoleBindingListCreateView(BaseHostelView):
    def get(self, request):
        if not self.principal.has_permission("hostel.hostel.manage"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        hostel_id = request.query_params.get("hostel_id")
        qs = HostelRoleBinding.objects.all()
        if hostel_id:
            qs = qs.filter(hostel_id=hostel_id)
        return Response(s.HostelRoleBindingSerializer(qs, many=True).data)

    def post(self, request):
        if not self.principal.has_permission("hostel.hostel.manage"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.HostelRoleBindingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hostel = serializer.validated_data["hostel"]
        binding = svc.manage_role_binding(
            hostel=hostel,
            user_id=serializer.validated_data["user_id"],
            role=serializer.validated_data["role"],
            shift=serializer.validated_data.get("shift", "general"),
            is_active=serializer.validated_data.get("is_active", True),
            valid_from=serializer.validated_data.get("valid_from"),
            valid_to=serializer.validated_data.get("valid_to"),
        )
        return Response(s.HostelRoleBindingSerializer(binding).data, status=status.HTTP_201_CREATED)


# --- 2. Rooms & Availability (HM-UC-009) ---


class RoomListCreateView(BaseHostelView):
    def get(self, request):
        hostel_id = request.query_params.get("hostel_id")
        qs = sel.visible_rooms(self.principal, int(hostel_id) if hostel_id else None)
        return Response(s.RoomSerializer(qs, many=True).data)

    def post(self, request):
        if not (
            self.principal.has_permission("hostel.occupancy.manage")
            or self.principal.has_permission("hostel.hostel.manage")
        ):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.RoomSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = serializer.save()
        return Response(s.RoomSerializer(room).data, status=status.HTTP_201_CREATED)


class RoomDetailView(BaseHostelView):
    def patch(self, request, pk: int):
        if not (
            self.principal.has_permission("hostel.occupancy.manage")
            or self.principal.has_permission("hostel.hostel.manage")
        ):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        room = get_object_or_404(Room, pk=pk)
        serializer = s.RoomSerializer(room, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# --- 3. Accommodation Requests & Allotment (HM-UC-005..008, HM-UC-010) ---


class AccommodationRequestListCreateView(BaseHostelView):
    def get(self, request):
        qs = sel.visible_accommodation_requests(self.principal)
        return Response(s.AccommodationRequestSerializer(qs, many=True).data)

    def post(self, request):
        if not self.principal.has_permission("hostel.accommodation.create"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.AccommodationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = svc.submit_accommodation_request(
            student_user_id=self.principal.user_id,
            preferred_hostel=serializer.validated_data.get("preferred_hostel"),
            academic_year=serializer.validated_data.get("academic_year", "2026-2027"),
            semester=serializer.validated_data.get("semester", "Regular"),
            preferences=serializer.validated_data.get("preferences", {}),
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(s.AccommodationRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class AllotmentListView(BaseHostelView):
    def get(self, request):
        qs = sel.visible_allotments(self.principal)
        return Response(s.RoomAllotmentSerializer(qs, many=True).data)


class BatchAllotmentDecisionView(BaseHostelView):
    def post(self, request):
        if not self.principal.has_permission("hostel.allotment.manage"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        data = request.data
        try:
            student_user_id = data["student_user_id"]
            hostel_id = data["hostel_id"]
            room_id = data["room_id"]
            req_id = data.get("request_id")
            round_name = data.get("allotment_round", "Round 1")
            notes = data.get("notes", "")

            hostel = get_object_or_404(Hostel, pk=hostel_id)
            room = get_object_or_404(Room, pk=room_id, hostel=hostel)
            acc_req = AccommodationRequest.objects.filter(pk=req_id).first() if req_id else None

            allotment = svc.record_allotment_decision(
                accommodation_request=acc_req,
                student_user_id=student_user_id,
                hostel=hostel,
                room=room,
                allotment_round=round_name,
                allotted_by_user_id=self.principal.user_id,
                notes=notes,
            )
            return Response(
                s.RoomAllotmentSerializer(allotment).data, status=status.HTTP_201_CREATED
            )
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


class RoomVacationView(BaseHostelView):
    def post(self, request, pk: int):
        if not self.principal.has_permission("hostel.allotment.manage"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        allotment = get_object_or_404(RoomAllotment, pk=pk)
        try:
            res = svc.record_room_vacation(
                allotment=allotment, actor_user_id=self.principal.user_id
            )
            return Response(s.RoomAllotmentSerializer(res).data)
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


class RoomExchangeView(BaseHostelView):
    def post(self, request):
        if not (
            self.principal.has_permission("hostel.occupancy.manage")
            or self.principal.has_permission("hostel.allotment.manage")
        ):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        data = request.data
        try:
            hostel = get_object_or_404(Hostel, pk=data["hostel_id"])
            exchange = svc.record_room_exchange(
                hostel=hostel,
                student_a_user_id=data["student_a_user_id"],
                student_b_user_id=data["student_b_user_id"],
                reason=data.get("reason", ""),
                processed_by_user_id=self.principal.user_id,
            )
            return Response(s.RoomExchangeSerializer(exchange).data, status=status.HTTP_201_CREATED)
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


# --- 4. Attendance Management (HM-UC-012, HM-UC-013, HM-UC-036) ---


class AttendanceListView(BaseHostelView):
    def get(self, request):
        date_str = request.query_params.get("date")
        date_val = date.fromisoformat(date_str) if date_str else None
        qs = sel.visible_attendance(self.principal, date_val=date_val)
        return Response(s.AttendanceRecordSerializer(qs, many=True).data)

    def post(self, request):
        if not self.principal.has_permission("hostel.attendance.record"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        data = request.data
        try:
            hostel = get_object_or_404(Hostel, pk=data["hostel_id"])
            date_val = date.fromisoformat(data["date"])
            created_records = []
            for item in data.get("records", []):
                rec = svc.record_attendance(
                    hostel=hostel,
                    student_user_id=item["student_user_id"],
                    date_val=date_val,
                    status=item.get("status", "present"),
                    recorded_by_user_id=self.principal.user_id,
                    remarks=item.get("remarks", ""),
                )
                created_records.append(rec)
            return Response(
                s.AttendanceRecordSerializer(created_records, many=True).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


# --- 5. Leave Management (HM-UC-014, HM-UC-015, HM-UC-016, HM-UC-037) ---


class LeaveRequestListCreateView(BaseHostelView):
    def get(self, request):
        qs = sel.visible_leaves(self.principal)
        return Response(s.LeaveRequestSerializer(qs, many=True).data)

    def post(self, request):
        if not self.principal.has_permission("hostel.leave.create"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.LeaveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            hostel = serializer.validated_data["hostel"]
            req = svc.submit_leave_request(
                hostel=hostel,
                student_user_id=self.principal.user_id,
                leave_type=serializer.validated_data.get("leave_type", "home"),
                start_date=serializer.validated_data["start_date"],
                end_date=serializer.validated_data["end_date"],
                reason=serializer.validated_data["reason"],
                destination=serializer.validated_data.get("destination", ""),
                supporting_document=serializer.validated_data.get("supporting_document", ""),
            )
            return Response(s.LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


class LeaveDecideView(BaseHostelView):
    def post(self, request, pk: int):
        if not self.principal.has_permission("hostel.leave.review"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        leave = get_object_or_404(LeaveRequest, pk=pk)
        serializer = s.LeaveDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            res = svc.record_leave_decision(
                leave_request=leave,
                decision=serializer.validated_data["decision"],
                remarks=serializer.validated_data.get("remarks", ""),
                decision_by_user_id=self.principal.user_id,
            )
            return Response(s.LeaveRequestSerializer(res).data)
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


# --- 6. Complaints (HM-UC-017, HM-UC-018, HM-UC-019) ---


class ComplaintListCreateView(BaseHostelView):
    def get(self, request):
        qs = sel.visible_complaints(self.principal)
        return Response(s.HostelComplaintSerializer(qs, many=True).data)

    def post(self, request):
        if not self.principal.has_permission("hostel.complaint.create"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.HostelComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            complaint = svc.submit_complaint(
                hostel=serializer.validated_data["hostel"],
                student_user_id=self.principal.user_id,
                category=serializer.validated_data["category"],
                description=serializer.validated_data["description"],
                room=serializer.validated_data.get("room"),
                attachment=serializer.validated_data.get("attachment", ""),
            )
            return Response(
                s.HostelComplaintSerializer(complaint).data, status=status.HTTP_201_CREATED
            )
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


class ComplaintUpdateView(BaseHostelView):
    def patch(self, request, pk: int):
        if not (
            self.principal.has_permission("hostel.complaint.manage")
            or self.principal.has_permission("hostel.complaint.oversight")
        ):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        complaint = get_object_or_404(HostelComplaint, pk=pk)
        serializer = s.ComplaintUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            target_status = serializer.validated_data["status"]
            res = svc.update_complaint_status(
                complaint=complaint,
                status=target_status,
                action_taken=serializer.validated_data.get("action_taken", ""),
                actor_user_id=self.principal.user_id,
                escalate=(target_status == "escalated"),
            )
            return Response(s.HostelComplaintSerializer(res).data)
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


# --- 7. Guest Room Bookings (HM-UC-020, HM-UC-021, HM-UC-022) ---


class GuestRoomBookingListCreateView(BaseHostelView):
    def get(self, request):
        qs = sel.visible_guest_bookings(self.principal)
        return Response(s.GuestRoomBookingSerializer(qs, many=True).data)

    def post(self, request):
        if not self.principal.has_permission("hostel.guestroom.create"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.GuestRoomBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = svc.submit_guest_room_booking(
                hostel=serializer.validated_data["hostel"],
                student_user_id=self.principal.user_id,
                guest_name=serializer.validated_data["guest_name"],
                guest_relation=serializer.validated_data["guest_relation"],
                guest_contact=serializer.validated_data["guest_contact"],
                check_in_date=serializer.validated_data["check_in_date"],
                check_out_date=serializer.validated_data["check_out_date"],
                room=serializer.validated_data.get("room"),
            )
            return Response(
                s.GuestRoomBookingSerializer(booking).data, status=status.HTTP_201_CREATED
            )
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


class GuestRoomDecideView(BaseHostelView):
    def post(self, request, pk: int):
        if not self.principal.has_permission("hostel.guestroom.manage"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        booking = get_object_or_404(GuestRoomBooking, pk=pk)
        serializer = s.GuestRoomDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            room_id = serializer.validated_data.get("room_id")
            room = Room.objects.filter(pk=room_id).first() if room_id else None
            res = svc.record_guest_room_decision(
                booking=booking,
                decision=serializer.validated_data["decision"],
                remarks=serializer.validated_data.get("remarks", ""),
                decision_by_user_id=self.principal.user_id,
                room=room,
            )
            return Response(s.GuestRoomBookingSerializer(res).data)
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


# --- 8. Extended Stay (HM-UC-023, HM-UC-024, HM-UC-025) ---


class ExtendedStayListCreateView(BaseHostelView):
    def get(self, request):
        qs = sel.visible_extended_stays(self.principal)
        return Response(s.ExtendedStayRequestSerializer(qs, many=True).data)

    def post(self, request):
        if not self.principal.has_permission("hostel.extendedstay.create"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.ExtendedStayRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            stay = svc.submit_extended_stay(
                hostel=serializer.validated_data["hostel"],
                student_user_id=self.principal.user_id,
                stay_reason=serializer.validated_data["stay_reason"],
                start_date=serializer.validated_data["start_date"],
                end_date=serializer.validated_data["end_date"],
            )
            return Response(
                s.ExtendedStayRequestSerializer(stay).data, status=status.HTTP_201_CREATED
            )
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


class ExtendedStayDecideView(BaseHostelView):
    def post(self, request, pk: int):
        if not self.principal.has_permission("hostel.extendedstay.review"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        stay = get_object_or_404(ExtendedStayRequest, pk=pk)
        serializer = s.ExtendedStayDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            res = svc.record_extended_stay_decision(
                stay=stay,
                decision=serializer.validated_data["decision"],
                remarks=serializer.validated_data.get("remarks", ""),
                charge_amount=serializer.validated_data.get("charge_amount", Decimal("0.00")),
                payment_deadline=serializer.validated_data.get("payment_deadline"),
                decision_by_user_id=self.principal.user_id,
            )
            return Response(s.ExtendedStayRequestSerializer(res).data)
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


# --- 9. Fines (HM-UC-026, HM-UC-027, HM-UC-038) ---


class FineListCreateView(BaseHostelView):
    def get(self, request):
        qs = sel.visible_fines(self.principal)
        return Response(s.HostelFineSerializer(qs, many=True).data)

    def post(self, request):
        if not (
            self.principal.has_permission("hostel.fine.record")
            or self.principal.has_permission("hostel.fine.oversight")
        ):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.HostelFineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            fine = svc.record_hostel_fine(
                hostel=serializer.validated_data["hostel"],
                student_user_id=serializer.validated_data["student_user_id"],
                amount=serializer.validated_data["amount"],
                reason=serializer.validated_data["reason"],
                imposed_date=serializer.validated_data["imposed_date"],
                issued_by_user_id=self.principal.user_id,
                remarks=serializer.validated_data.get("remarks", ""),
            )
            return Response(s.HostelFineSerializer(fine).data, status=status.HTTP_201_CREATED)
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


# --- 10. Operations: Inventory, Staff, Security (HM-UC-028, HM-UC-029, HM-UC-030) ---


class InventoryListCreateView(BaseHostelView):
    def get(self, request):
        hostel_id = request.query_params.get("hostel_id")
        qs = sel.visible_inventory(self.principal, int(hostel_id) if hostel_id else None)
        return Response(s.HostelInventoryItemSerializer(qs, many=True).data)

    def post(self, request):
        if not self.principal.has_permission("hostel.inventory.manage"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.HostelInventoryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by_user_id=self.principal.user_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StaffDutyLogListCreateView(BaseHostelView):
    def get(self, request):
        hostel_id = request.query_params.get("hostel_id")
        qs = sel.visible_staff_logs(self.principal, int(hostel_id) if hostel_id else None)
        return Response(s.HostelStaffDutyLogSerializer(qs, many=True).data)

    def post(self, request):
        if not self.principal.has_permission("hostel.staff.manage"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.HostelStaffDutyLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(recorded_by_user_id=self.principal.user_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SecurityGuardShiftListCreateView(BaseHostelView):
    def get(self, request):
        hostel_id = request.query_params.get("hostel_id")
        qs = sel.visible_security_shifts(self.principal, int(hostel_id) if hostel_id else None)
        return Response(s.SecurityGuardShiftSerializer(qs, many=True).data)

    def post(self, request):
        if not self.principal.has_permission("hostel.security.manage"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.SecurityGuardShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(scheduled_by_user_id=self.principal.user_id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# --- 11. Notices & Announcements (HM-UC-031, HM-UC-032) ---


class NoticeListCreateView(BaseHostelView):
    def get(self, request):
        hostel_id = request.query_params.get("hostel_id")
        qs = sel.visible_notices(self.principal, int(hostel_id) if hostel_id else None)
        return Response(s.HostelNoticeSerializer(qs, many=True).data)

    def post(self, request):
        if not self.principal.has_permission("hostel.notice.publish"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = s.HostelNoticeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            hostel = serializer.validated_data.get("hostel")
            notice = svc.publish_notice(
                hostel=hostel,
                title=serializer.validated_data["title"],
                content=serializer.validated_data["content"],
                priority=serializer.validated_data.get("priority", "normal"),
                published_by_user_id=self.principal.user_id,
                is_super_admin=sel.is_super_admin(self.principal),
            )
            return Response(s.HostelNoticeSerializer(notice).data, status=status.HTTP_201_CREATED)
        except Exception as e:  # noqa: BLE001
            return self.handle_error(e)


# --- 12. Notifications (HM-UC-034) ---


class NotificationListView(BaseHostelView):
    def get(self, request):
        qs = sel.visible_notifications(self.principal)
        return Response(s.HostelNotificationSerializer(qs, many=True).data)


class NotificationMarkReadView(BaseHostelView):
    def post(self, request, pk: int):
        notif = get_object_or_404(
            HostelNotification, pk=pk, recipient_user_id=self.principal.user_id
        )
        notif.is_read = True
        notif.save(update_fields=["is_read", "updated_at"])
        return Response({"status": "ok"})


# --- 13. Operational Reports (HM-UC-033, BR-HM-032) ---


class OperationalReportView(BaseHostelView):
    def get(self, request, hostel_id: int):
        if not self.principal.has_permission("hostel.report.view"):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        rep = sel.generate_hostel_report(hostel_id)
        return Response(rep)
