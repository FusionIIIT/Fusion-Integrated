"""Hostel Management API Views."""

from datetime import datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import IsAuthenticatedPrincipal
from ..domain.errors import HostelDomainError
from ..models import Hostel, NotificationRecord
from ..selectors import (
    get_hostel_by_id,
    get_room_by_id,
    get_user_assigned_hostel_ids,
    list_accommodation_requests,
    list_allotments,
    list_attendance,
    list_complaints,
    list_extended_stays,
    list_fines,
    list_guest_bookings,
    list_hostels,
    list_inventory,
    list_inventory_audits,
    list_leave_requests,
    list_notices,
    list_notifications,
    list_role_bindings,
    list_room_assignment_history,
    list_rooms,
    list_security_shifts,
    list_staff_assignments,
)
from ..services import (
    create_hostel,
    create_or_update_inventory_item,
    create_or_update_role_binding,
    create_or_update_security_shift,
    create_or_update_staff_assignment,
    create_room,
    generate_operational_report,
    publish_notice,
    record_allotment_decision,
    record_attendance_batch,
    record_charge_and_compliance,
    record_extended_stay_decision,
    record_fine,
    record_guest_room_decision,
    record_individual_room_exchange,
    record_leave_decision,
    record_reallotment,
    record_room_vacation,
    submit_accommodation_request,
    submit_complaint,
    submit_extended_stay_request,
    submit_guest_room_request,
    submit_leave_request,
    toggle_hostel_status,
    update_complaint_status,
    update_hostel,
    update_room,
)
from .permissions import (
    CanApplyAccommodation,
    CanApplyExtendedStay,
    CanApplyLeave,
    CanManageAllotments,
    CanManageHostelMaster,
    CanManageInventory,
    CanManageRoleBindings,
    CanManageRooms,
    CanManageSecurity,
    CanManageStaff,
    CanPublishNotice,
    CanRecordAttendance,
    CanRecordFine,
    CanRequestGuestRoom,
    CanResolveComplaint,
    CanReviewExtendedStay,
    CanReviewGuestRoom,
    CanReviewLeave,
    CanSubmitComplaint,
    CanViewAccommodation,
    CanViewAttendance,
    CanViewComplaint,
    CanViewExtendedStay,
    CanViewFine,
    CanViewGuestRoom,
    CanViewInventory,
    CanViewLeave,
    CanViewNotice,
    CanViewReports,
    CanViewRooms,
    CanViewSecurity,
    CanViewStaff,
    RequireHostelModule,
)
from .serializers import (
    AccommodationRequestSerializer,
    AttendanceRecordSerializer,
    ExtendedStayRequestSerializer,
    GuestRoomBookingSerializer,
    HostelComplaintSerializer,
    HostelFineSerializer,
    HostelInventoryItemSerializer,
    HostelNoticeSerializer,
    HostelRoleBindingSerializer,
    HostelSerializer,
    InventoryAuditLogSerializer,
    LeaveRequestSerializer,
    NotificationRecordSerializer,
    RoomAllotmentSerializer,
    RoomAssignmentHistorySerializer,
    RoomSerializer,
    SecurityGuardShiftSerializer,
    StaffAssignmentSerializer,
)


def _get_principal(request):
    return getattr(request, "principal", None)


def _parse_date(date_str: str | None):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


# -- 1. Hostel Master Views (3.0, HM-UC-001..004) -----------------------------

class HostelListCreateView(APIView):
    permission_classes = [RequireHostelModule]

    def get(self, request):
        is_active = request.query_params.get("is_active")
        active_bool = is_active.lower() in ("true", "1") if is_active is not None else None
        hostels = list_hostels(is_active=active_bool)
        serializer = HostelSerializer(hostels, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not CanManageHostelMaster().has_permission(request, self):
            return Response({"error": "Permission denied: Super Admin required."}, status=status.HTTP_403_FORBIDDEN)
        try:
            hostel = create_hostel(
                name=request.data.get("name", ""),
                code=request.data.get("code", ""),
                gender_policy=request.data.get("gender_policy", "coed"),
                capacity=int(request.data.get("capacity", 0)),
                description=request.data.get("description", ""),
            )
            return Response(HostelSerializer(hostel).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class HostelDetailView(APIView):
    permission_classes = [RequireHostelModule]

    def get(self, request, pk):
        hostel = get_hostel_by_id(pk)
        if not hostel:
            return Response({"error": "Hostel not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(HostelSerializer(hostel).data)

    def put(self, request, pk):
        if not CanManageHostelMaster().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            hostel = update_hostel(
                hostel_id=pk,
                name=request.data.get("name"),
                gender_policy=request.data.get("gender_policy"),
                capacity=request.data.get("capacity"),
                description=request.data.get("description"),
            )
            return Response(HostelSerializer(hostel).data)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class HostelToggleActiveView(APIView):
    permission_classes = [RequireHostelModule, CanManageHostelMaster]

    def post(self, request, pk):
        is_active = bool(request.data.get("is_active", True))
        try:
            hostel = toggle_hostel_status(pk, is_active=is_active)
            return Response(HostelSerializer(hostel).data)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class RoleBindingListCreateView(APIView):
    permission_classes = [RequireHostelModule]

    def get(self, request):
        hostel_id = request.query_params.get("hostel_id")
        h_id = int(hostel_id) if hostel_id else None
        bindings = list_role_bindings(hostel_id=h_id)
        return Response(HostelRoleBindingSerializer(bindings, many=True).data)

    def post(self, request):
        if not CanManageRoleBindings().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        p = _get_principal(request)
        assigned_by = p.user_id if p else 1
        try:
            binding = create_or_update_role_binding(
                hostel_id=int(request.data["hostel_id"]),
                user_id=int(request.data["user_id"]),
                role=request.data["role"],
                assigned_by_user_id=assigned_by,
                is_active=bool(request.data.get("is_active", True)),
                start_date=_parse_date(request.data.get("start_date")),
                end_date=_parse_date(request.data.get("end_date")),
                notes=request.data.get("notes", ""),
            )
            return Response(HostelRoleBindingSerializer(binding).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


# -- 2. Room & Occupancy Views (3.1 & 3.2, HM-UC-009..011) ---------------------

class RoomListCreateView(APIView):
    permission_classes = [RequireHostelModule, CanViewRooms]

    def get(self, request):
        hostel_id = request.query_params.get("hostel_id")
        h_id = int(hostel_id) if hostel_id else None
        rooms = list_rooms(hostel_id=h_id)
        return Response(RoomSerializer(rooms, many=True).data)

    def post(self, request):
        if not CanManageRooms().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        try:
            room = create_room(
                hostel_id=int(request.data["hostel_id"]),
                room_number=request.data["room_number"],
                floor=int(request.data.get("floor", 1)),
                capacity=int(request.data.get("capacity", 2)),
                room_type=request.data.get("room_type", "double"),
            )
            return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class RoomExchangeView(APIView):
    permission_classes = [RequireHostelModule, CanManageRooms]

    def post(self, request):
        """Caretaker records individual room exchange / transfer (HM-UC-010)."""
        p = _get_principal(request)
        caretaker_id = p.user_id if p else 1
        try:
            s2 = request.data.get("student_user_id_2")
            allot1, allot2 = record_individual_room_exchange(
                caretaker_user_id=caretaker_id,
                hostel_id=int(request.data["hostel_id"]),
                student_user_id_1=int(request.data["student_user_id_1"]),
                target_room_id=int(request.data["target_room_id"]),
                student_user_id_2=int(s2) if s2 else None,
                reason=request.data.get("reason", ""),
            )
            data = {"student_1": RoomAllotmentSerializer(allot1).data}
            if allot2:
                data["student_2"] = RoomAllotmentSerializer(allot2).data
            return Response(data, status=status.HTTP_200_OK)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


# -- 3. Accommodation & Allotment Views (3.1 & 3.2, HM-UC-005..008) ------------

class AccommodationRequestListCreateView(APIView):
    permission_classes = [RequireHostelModule, CanViewAccommodation]

    def get(self, request):
        p = _get_principal(request)
        student_id = request.query_params.get("student_user_id")
        # If student, scope to own requests
        if p and p.kind == "student":
            student_id = p.user_id
        reqs = list_accommodation_requests(
            hostel_id=request.query_params.get("hostel_id"),
            student_user_id=int(student_id) if student_id else None,
            status=request.query_params.get("status"),
        )
        return Response(AccommodationRequestSerializer(reqs, many=True).data)

    def post(self, request):
        if not CanApplyAccommodation().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        p = _get_principal(request)
        student_id = p.user_id if p else int(request.data.get("student_user_id", 1))
        roll = p.username if p else request.data.get("student_roll_number", "TEST_ROLL")
        name = p.display_name if p else request.data.get("student_name", "Test Student")
        try:
            req_hostel = request.data.get("requested_hostel_id")
            req = submit_accommodation_request(
                student_user_id=student_id,
                student_roll_number=roll,
                student_name=name,
                academic_year=request.data.get("academic_year", "2026-2027"),
                semester=request.data.get("semester", "Autumn"),
                requested_hostel_id=int(req_hostel) if req_hostel else None,
                reason=request.data.get("reason", ""),
            )
            return Response(AccommodationRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class AllotmentDecisionView(APIView):
    permission_classes = [RequireHostelModule, CanManageAllotments]

    def post(self, request, pk):
        """Super Admin records allotment decision for request (HM-UC-006, BW-HM-01)."""
        p = _get_principal(request)
        admin_id = p.user_id if p else 1
        try:
            allotment = record_allotment_decision(
                super_admin_user_id=admin_id,
                request_id=pk,
                room_id=int(request.data["room_id"]),
                allotment_reason=request.data.get("reason", "Batch allotment round"),
            )
            return Response(RoomAllotmentSerializer(allotment).data, status=status.HTTP_200_OK)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class AllotmentListView(APIView):
    permission_classes = [RequireHostelModule, CanViewAccommodation]

    def get(self, request):
        p = _get_principal(request)
        student_id = request.query_params.get("student_user_id")
        if p and p.kind == "student":
            student_id = p.user_id
        is_active = request.query_params.get("is_active")
        active_bool = is_active.lower() in ("true", "1") if is_active is not None else None
        allotments = list_allotments(
            hostel_id=request.query_params.get("hostel_id"),
            student_user_id=int(student_id) if student_id else None,
            is_active=active_bool,
        )
        return Response(RoomAllotmentSerializer(allotments, many=True).data)


class AllotmentReallotView(APIView):
    permission_classes = [RequireHostelModule, CanManageAllotments]

    def post(self, request, pk):
        p = _get_principal(request)
        admin_id = p.user_id if p else 1
        try:
            allotment = record_reallotment(
                super_admin_user_id=admin_id,
                allotment_id=pk,
                new_room_id=int(request.data["new_room_id"]),
                reason=request.data.get("reason", "Central re-allotment"),
            )
            return Response(RoomAllotmentSerializer(allotment).data)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class AllotmentVacateView(APIView):
    permission_classes = [RequireHostelModule, CanManageAllotments]

    def post(self, request, pk):
        p = _get_principal(request)
        admin_id = p.user_id if p else 1
        try:
            allotment = record_room_vacation(
                super_admin_user_id=admin_id,
                allotment_id=pk,
                vacation_reason=request.data.get("reason", "Graduation / semester completion"),
            )
            return Response(RoomAllotmentSerializer(allotment).data)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class RoomHistoryListView(APIView):
    permission_classes = [RequireHostelModule, CanViewAccommodation]

    def get(self, request):
        p = _get_principal(request)
        student_id = request.query_params.get("student_user_id")
        if p and p.kind == "student":
            student_id = p.user_id
        history = list_room_assignment_history(
            student_user_id=int(student_id) if student_id else None,
            room_id=request.query_params.get("room_id"),
        )
        return Response(RoomAssignmentHistorySerializer(history, many=True).data)


# -- 4. Attendance Views (3.3, HM-UC-012, HM-UC-013, HM-UC-036) ----------------

class AttendanceListCreateView(APIView):
    permission_classes = [RequireHostelModule, CanViewAttendance]

    def get(self, request):
        p = _get_principal(request)
        student_id = request.query_params.get("student_user_id")
        if p and p.kind == "student":
            student_id = p.user_id
        recs = list_attendance(
            hostel_id=request.query_params.get("hostel_id"),
            student_user_id=int(student_id) if student_id else None,
            date_val=_parse_date(request.query_params.get("date")),
            from_date=_parse_date(request.query_params.get("from_date")),
            to_date=_parse_date(request.query_params.get("to_date")),
        )
        return Response(AttendanceRecordSerializer(recs, many=True).data)

    def post(self, request):
        if not CanRecordAttendance().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        p = _get_principal(request)
        caretaker_id = p.user_id if p else 1
        try:
            records = record_attendance_batch(
                caretaker_user_id=caretaker_id,
                hostel_id=int(request.data["hostel_id"]),
                date_val=_parse_date(request.data["date"]),
                records=request.data["records"],
            )
            return Response(AttendanceRecordSerializer(records, many=True).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


# -- 5. Leave Request Views (3.4, HM-UC-014..016, HM-UC-037, CW-HM-01) ---------

class LeaveRequestListCreateView(APIView):
    permission_classes = [RequireHostelModule, CanViewLeave]

    def get(self, request):
        p = _get_principal(request)
        student_id = request.query_params.get("student_user_id")
        if p and p.kind == "student":
            student_id = p.user_id
        leaves = list_leave_requests(
            hostel_id=request.query_params.get("hostel_id"),
            student_user_id=int(student_id) if student_id else None,
            status=request.query_params.get("status"),
        )
        return Response(LeaveRequestSerializer(leaves, many=True).data)

    def post(self, request):
        if not CanApplyLeave().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        p = _get_principal(request)
        student_id = p.user_id if p else int(request.data.get("student_user_id", 1))
        roll = p.username if p else request.data.get("student_roll_number", "TEST_ROLL")
        name = p.display_name if p else request.data.get("student_name", "Test Student")
        try:
            leave = submit_leave_request(
                student_user_id=student_id,
                student_roll_number=roll,
                student_name=name,
                hostel_id=int(request.data["hostel_id"]),
                leave_type=request.data.get("leave_type", "home"),
                start_date=_parse_date(request.data["start_date"]),
                end_date=_parse_date(request.data["end_date"]),
                reason=request.data.get("reason", ""),
                address_during_leave=request.data.get("address_during_leave", ""),
                emergency_contact=request.data.get("emergency_contact", ""),
                supporting_document=request.data.get("supporting_document", ""),
            )
            return Response(LeaveRequestSerializer(leave).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class LeaveDecisionView(APIView):
    permission_classes = [RequireHostelModule, CanReviewLeave]

    def post(self, request, pk):
        p = _get_principal(request)
        caretaker_id = p.user_id if p else 1
        try:
            leave = record_leave_decision(
                caretaker_user_id=caretaker_id,
                request_id=pk,
                decision=request.data["decision"],
                remarks=request.data.get("remarks", ""),
            )
            return Response(LeaveRequestSerializer(leave).data)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


# -- 6. Hostel Complaints Views (3.5, HM-UC-017..019, CW-HM-02) ----------------

class ComplaintListCreateView(APIView):
    permission_classes = [RequireHostelModule, CanViewComplaint]

    def get(self, request):
        p = _get_principal(request)
        student_id = request.query_params.get("student_user_id")
        if p and p.kind == "student":
            student_id = p.user_id
        escalated = request.query_params.get("escalated_only", "").lower() in ("true", "1")
        comps = list_complaints(
            hostel_id=request.query_params.get("hostel_id"),
            student_user_id=int(student_id) if student_id else None,
            status=request.query_params.get("status"),
            escalated_only=escalated,
        )
        return Response(HostelComplaintSerializer(comps, many=True).data)

    def post(self, request):
        if not CanSubmitComplaint().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        p = _get_principal(request)
        student_id = p.user_id if p else int(request.data.get("student_user_id", 1))
        roll = p.username if p else request.data.get("student_roll_number", "TEST_ROLL")
        name = p.display_name if p else request.data.get("student_name", "Test Student")
        try:
            comp = submit_complaint(
                student_user_id=student_id,
                student_roll_number=roll,
                student_name=name,
                hostel_id=int(request.data["hostel_id"]),
                category=request.data.get("category", "other"),
                title=request.data["title"],
                description=request.data["description"],
                room_number=request.data.get("room_number", ""),
                attachment_url=request.data.get("attachment_url", ""),
            )
            return Response(HostelComplaintSerializer(comp).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class ComplaintStatusView(APIView):
    permission_classes = [RequireHostelModule, CanResolveComplaint]

    def post(self, request, pk):
        p = _get_principal(request)
        handler_id = p.user_id if p else 1
        try:
            comp = update_complaint_status(
                handler_user_id=handler_id,
                complaint_id=pk,
                status=request.data.get("status", "in_progress"),
                action_taken=request.data.get("action_taken", ""),
                escalate_to_warden=bool(request.data.get("escalate_to_warden", False)),
                escalation_reason=request.data.get("escalation_reason", ""),
            )
            return Response(HostelComplaintSerializer(comp).data)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


# -- 7. Guest Room Views (3.6, HM-UC-020..022, CW-HM-03) -----------------------

class GuestBookingListCreateView(APIView):
    permission_classes = [RequireHostelModule, CanViewGuestRoom]

    def get(self, request):
        p = _get_principal(request)
        student_id = request.query_params.get("student_user_id")
        if p and p.kind == "student":
            student_id = p.user_id
        bookings = list_guest_bookings(
            hostel_id=request.query_params.get("hostel_id"),
            student_user_id=int(student_id) if student_id else None,
            status=request.query_params.get("status"),
        )
        return Response(GuestRoomBookingSerializer(bookings, many=True).data)

    def post(self, request):
        if not CanRequestGuestRoom().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        p = _get_principal(request)
        student_id = p.user_id if p else int(request.data.get("student_user_id", 1))
        roll = p.username if p else request.data.get("student_roll_number", "TEST_ROLL")
        name = p.display_name if p else request.data.get("student_name", "Test Student")
        try:
            booking = submit_guest_room_request(
                student_user_id=student_id,
                student_roll_number=roll,
                student_name=name,
                hostel_id=int(request.data["hostel_id"]),
                guest_name=request.data["guest_name"],
                guest_relation=request.data["guest_relation"],
                guest_gender=request.data.get("guest_gender", "unspecified"),
                check_in_date=_parse_date(request.data["check_in_date"]),
                check_out_date=_parse_date(request.data["check_out_date"]),
                number_of_guests=int(request.data.get("number_of_guests", 1)),
                reason=request.data.get("reason", ""),
            )
            return Response(GuestRoomBookingSerializer(booking).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class GuestBookingDecisionView(APIView):
    permission_classes = [RequireHostelModule, CanReviewGuestRoom]

    def post(self, request, pk):
        p = _get_principal(request)
        caretaker_id = p.user_id if p else 1
        try:
            room_id = request.data.get("assigned_room_id")
            booking = record_guest_room_decision(
                caretaker_user_id=caretaker_id,
                booking_id=pk,
                decision=request.data["decision"],
                assigned_room_id=int(room_id) if room_id else None,
                remarks=request.data.get("remarks", ""),
            )
            return Response(GuestRoomBookingSerializer(booking).data)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


# -- 8. Extended Stay Views (3.7, HM-UC-023..025, CW-HM-04) --------------------

class ExtendedStayListCreateView(APIView):
    permission_classes = [RequireHostelModule, CanViewExtendedStay]

    def get(self, request):
        p = _get_principal(request)
        student_id = request.query_params.get("student_user_id")
        if p and p.kind == "student":
            student_id = p.user_id
        stays = list_extended_stays(
            hostel_id=request.query_params.get("hostel_id"),
            student_user_id=int(student_id) if student_id else None,
            status=request.query_params.get("status"),
        )
        return Response(ExtendedStayRequestSerializer(stays, many=True).data)

    def post(self, request):
        if not CanApplyExtendedStay().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        p = _get_principal(request)
        student_id = p.user_id if p else int(request.data.get("student_user_id", 1))
        roll = p.username if p else request.data.get("student_roll_number", "TEST_ROLL")
        name = p.display_name if p else request.data.get("student_name", "Test Student")
        try:
            stay = submit_extended_stay_request(
                student_user_id=student_id,
                student_roll_number=roll,
                student_name=name,
                hostel_id=int(request.data["hostel_id"]),
                stay_reason=request.data.get("stay_reason", "academic"),
                start_date=_parse_date(request.data["start_date"]),
                end_date=_parse_date(request.data["end_date"]),
                remarks=request.data.get("remarks", ""),
            )
            return Response(ExtendedStayRequestSerializer(stay).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class ExtendedStayDecisionView(APIView):
    permission_classes = [RequireHostelModule, CanReviewExtendedStay]

    def post(self, request, pk):
        p = _get_principal(request)
        warden_id = p.user_id if p else 1
        try:
            stay = record_extended_stay_decision(
                warden_user_id=warden_id,
                request_id=pk,
                decision=request.data["decision"],
                remarks=request.data.get("remarks", ""),
            )
            return Response(ExtendedStayRequestSerializer(stay).data)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class ExtendedStayComplianceView(APIView):
    permission_classes = [RequireHostelModule, CanReviewExtendedStay]

    def post(self, request, pk):
        try:
            stay = record_charge_and_compliance(
                request_id=pk,
                charge_amount=request.data.get("charge_amount", 0),
                payment_deadline=_parse_date(request.data.get("payment_deadline")),
                payment_status=request.data.get("payment_status"),
            )
            return Response(ExtendedStayRequestSerializer(stay).data)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


# -- 9. Fine Management Views (3.8, HM-UC-026, HM-UC-027, HM-UC-038) -----------

class FineListCreateView(APIView):
    permission_classes = [RequireHostelModule, CanViewFine]

    def get(self, request):
        p = _get_principal(request)
        student_id = request.query_params.get("student_user_id")
        if p and p.kind == "student":
            student_id = p.user_id
        fines = list_fines(
            hostel_id=request.query_params.get("hostel_id"),
            student_user_id=int(student_id) if student_id else None,
        )
        return Response(HostelFineSerializer(fines, many=True).data)

    def post(self, request):
        if not CanRecordFine().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        p = _get_principal(request)
        caretaker_id = p.user_id if p else 1
        try:
            fine = record_fine(
                caretaker_user_id=caretaker_id,
                hostel_id=int(request.data["hostel_id"]),
                student_user_id=int(request.data["student_user_id"]),
                student_roll_number=request.data["student_roll_number"],
                student_name=request.data.get("student_name", ""),
                reason=request.data["reason"],
                amount=request.data["amount"],
                date_val=_parse_date(request.data["date"]),
                fine_type=request.data.get("fine_type", "rule_violation"),
            )
            return Response(HostelFineSerializer(fine).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


# -- 10. Inventory & Staff Coordination Views (3.9, HM-UC-028, HM-UC-029) ------

class InventoryListCreateView(APIView):
    permission_classes = [RequireHostelModule, CanViewInventory]

    def get(self, request):
        items = list_inventory(
            hostel_id=request.query_params.get("hostel_id"),
            category=request.query_params.get("category"),
        )
        return Response(HostelInventoryItemSerializer(items, many=True).data)

    def post(self, request):
        if not CanManageInventory().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        p = _get_principal(request)
        user_id = p.user_id if p else 1
        try:
            item = create_or_update_inventory_item(
                user_id=user_id,
                hostel_id=int(request.data["hostel_id"]),
                item_name=request.data["item_name"],
                category=request.data.get("category", "furniture"),
                total_quantity=int(request.data.get("total_quantity", 1)),
                in_use_quantity=int(request.data.get("in_use_quantity", 0)),
                condition=request.data.get("condition", "good"),
                location=request.data.get("location", "Hostel Storage"),
            )
            return Response(HostelInventoryItemSerializer(item).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


class InventoryAuditListView(APIView):
    permission_classes = [RequireHostelModule, CanViewInventory]

    def get(self, request):
        item_id = request.query_params.get("item_id")
        audits = list_inventory_audits(item_id=int(item_id) if item_id else None)
        return Response(InventoryAuditLogSerializer(audits, many=True).data)


class StaffAssignmentListCreateView(APIView):
    permission_classes = [RequireHostelModule, CanViewStaff]

    def get(self, request):
        staff = list_staff_assignments(hostel_id=request.query_params.get("hostel_id"))
        return Response(StaffAssignmentSerializer(staff, many=True).data)

    def post(self, request):
        if not CanManageStaff().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        p = _get_principal(request)
        user_id = p.user_id if p else 1
        try:
            staff = create_or_update_staff_assignment(
                user_id=user_id,
                hostel_id=int(request.data["hostel_id"]),
                staff_name=request.data["staff_name"],
                role_designation=request.data.get("role_designation", "attendant"),
                shift=request.data.get("shift", "general"),
                contact_number=request.data.get("contact_number", ""),
                duty_location=request.data.get("duty_location", ""),
            )
            return Response(StaffAssignmentSerializer(staff).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


# -- 11. Security Guard Shifts Views (3.10, HM-UC-030) -------------------------

class SecurityShiftListCreateView(APIView):
    permission_classes = [RequireHostelModule, CanViewSecurity]

    def get(self, request):
        shifts = list_security_shifts(
            hostel_id=request.query_params.get("hostel_id"),
            shift_date=_parse_date(request.query_params.get("shift_date")),
        )
        return Response(SecurityGuardShiftSerializer(shifts, many=True).data)

    def post(self, request):
        if not CanManageSecurity().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        p = _get_principal(request)
        warden_id = p.user_id if p else 1
        try:
            shift = create_or_update_security_shift(
                warden_user_id=warden_id,
                hostel_id=int(request.data["hostel_id"]),
                guard_name=request.data["guard_name"],
                shift_date=_parse_date(request.data["shift_date"]),
                shift_type=request.data.get("shift_type", "night"),
                agency_or_badge_number=request.data.get("agency_or_badge_number", ""),
                gate_or_post=request.data.get("gate_or_post", "Main Gate"),
                contact_number=request.data.get("contact_number", ""),
                supervisor_name=request.data.get("supervisor_name", ""),
            )
            return Response(SecurityGuardShiftSerializer(shift).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


# -- 12. Notices & Notice Board Views (3.11, HM-UC-031, HM-UC-032) -------------

class NoticeListCreateView(APIView):
    permission_classes = [RequireHostelModule, CanViewNotice]

    def get(self, request):
        hostel_id = request.query_params.get("hostel_id")
        h_id = int(hostel_id) if hostel_id else None
        notices = list_notices(hostel_id=h_id)
        return Response(HostelNoticeSerializer(notices, many=True).data)

    def post(self, request):
        if not CanPublishNotice().has_permission(request, self):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        p = _get_principal(request)
        user_id = p.user_id if p else 1
        role = p.active_role or (p.roles[0] if p and p.roles else "staff")
        try:
            h_id = request.data.get("hostel_id")
            notice = publish_notice(
                publisher_user_id=user_id,
                publisher_role=role,
                title=request.data["title"],
                body=request.data["body"],
                hostel_id=int(h_id) if h_id else None,
                category=request.data.get("category", "general"),
                is_pinned=bool(request.data.get("is_pinned", False)),
            )
            return Response(HostelNoticeSerializer(notice).data, status=status.HTTP_201_CREATED)
        except HostelDomainError as e:
            return Response({"error": e.message, "code": e.code}, status=status.HTTP_400_BAD_REQUEST)


# -- 13. Reports Views (3.12, HM-UC-033, BR-HM-032) ----------------------------

class ReportsView(APIView):
    permission_classes = [RequireHostelModule, CanViewReports]

    def get(self, request):
        report_type = request.query_params.get("report_type", "dashboard_summary")
        hostel_id = request.query_params.get("hostel_id")
        h_id = int(hostel_id) if hostel_id else None
        data = generate_operational_report(report_type=report_type, hostel_id=h_id)
        return Response(data)


# -- 14. Notifications Views (3.13, HM-UC-034, BR-HM-034) ----------------------

class NotificationListView(APIView):
    permission_classes = [RequireHostelModule, IsAuthenticatedPrincipal]

    def get(self, request):
        p = _get_principal(request)
        user_id = p.user_id if p else 1
        is_read = request.query_params.get("is_read")
        read_bool = is_read.lower() in ("true", "1") if is_read is not None else None
        notifs = list_notifications(user_id=user_id, is_read=read_bool)
        return Response(NotificationRecordSerializer(notifs, many=True).data)


class NotificationMarkReadView(APIView):
    permission_classes = [RequireHostelModule, IsAuthenticatedPrincipal]

    def post(self, request, pk):
        p = _get_principal(request)
        user_id = p.user_id if p else 1
        notif = NotificationRecord.objects.filter(id=pk, recipient_user_id=user_id).first()
        if not notif:
            return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
        notif.is_read = True
        notif.save(update_fields=["is_read"])
        return Response({"status": "ok"})
