"""Views for Hostel Management module.

Every endpoint requires HasModuleGrant("hm") and the exact action permission.
All scoped reads delegate to selectors/scoping.py. Invisible objects return 404.
All mutations delegate to services/.
"""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.hm.selectors import scoping
from modules.hm.services import (
    create_hostel,
    update_hostel,
    assign_hostel_role_binding,
    revoke_hostel_role_binding,
    update_room_capacity,
    submit_accommodation_request,
    allot_room_from_request,
    vacate_room_assignment,
    exchange_room_assignments,
    record_attendance,
    submit_leave_request,
    decide_leave_request,
    submit_complaint,
    record_complaint_event,
    submit_guest_booking,
    decide_guest_booking,
    submit_extended_stay,
    decide_extended_stay,
    record_fine,
    create_inventory_item,
    update_inventory_item,
    create_guard_shift,
    create_notice,
    publish_notice,
    withdraw_notice,
)
from modules.hm.api.serializers import (
    HostelSerializer,
    HostelRoleBindingSerializer,
    RoomSerializer,
    AccommodationRequestSerializer,
    RoomAssignmentSerializer,
    AttendanceRecordSerializer,
    LeaveRequestSerializer,
    ComplaintSerializer,
    GuestBookingSerializer,
    ExtendedStayRequestSerializer,
    FineRecordSerializer,
    InventoryItemSerializer,
    GuardShiftSerializer,
    NoticeSerializer,
)

MODULE = HasModuleGrant("hm")


class HMBaseView(APIView):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)


# 1. Hostels
class HostelListCreateView(HMBaseView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("hm.hostel.create")()]
        return [MODULE(), HasPermission("hm.hostel.view")()]

    def get(self, request):
        qs = scoping.scope_hostels(request.user)
        return Response(HostelSerializer(qs, many=True).data)

    def post(self, request):
        serializer = HostelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hostel = create_hostel(**serializer.validated_data)
        return Response(HostelSerializer(hostel).data, status=status.HTTP_201_CREATED)


class HostelDetailUpdateView(HMBaseView):
    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [MODULE(), HasPermission("hm.hostel.update")()]
        return [MODULE(), HasPermission("hm.hostel.view")()]

    def get(self, request, id):
        hostel = get_object_or_404(scoping.scope_hostels(request.user), id=id)
        return Response(HostelSerializer(hostel).data)

    def patch(self, request, id):
        hostel = get_object_or_404(scoping.scope_hostels(request.user), id=id)
        serializer = HostelSerializer(hostel, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_hostel(hostel=hostel, **serializer.validated_data)
        return Response(HostelSerializer(updated).data)


# 2. Hostel Role Bindings
class HostelRoleBindingListCreateView(HMBaseView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("hm.hostel_role_binding.assign")()]
        return [MODULE(), HasPermission("hm.hostel_role_binding.view")()]

    def get(self, request, id):
        hostel = get_object_or_404(scoping.scope_hostels(request.user), id=id)
        qs = scoping.scope_role_bindings(request.user, hostel_id=hostel.id)
        return Response(HostelRoleBindingSerializer(qs, many=True).data)

    def post(self, request, id):
        hostel = get_object_or_404(scoping.scope_hostels(request.user), id=id)
        serializer = HostelRoleBindingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        binding = assign_hostel_role_binding(
            hostel=hostel,
            user_id=serializer.validated_data["user_id"],
            role_kind=serializer.validated_data["role_kind"],
            assigned_by_user_id=request.user.user_id,
            valid_from=serializer.validated_data.get("valid_from"),
            valid_to=serializer.validated_data.get("valid_to"),
        )
        return Response(HostelRoleBindingSerializer(binding).data, status=status.HTTP_201_CREATED)


class HostelRoleBindingRevokeView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.hostel_role_binding.revoke")]

    def patch(self, request, id):
        binding = get_object_or_404(scoping.scope_role_bindings(request.user), id=id)
        revoked = revoke_hostel_role_binding(binding=binding)
        return Response(HostelRoleBindingSerializer(revoked).data)


# 3. Accommodation Requests
class AccommodationRequestListCreateView(HMBaseView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("hm.accommodation_request.create")()]
        return [MODULE(), HasPermission("hm.accommodation_request.view")()]

    def get(self, request):
        qs = scoping.scope_accommodation_requests(request.user)
        return Response(AccommodationRequestSerializer(qs, many=True).data)

    def post(self, request):
        serializer = AccommodationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = submit_accommodation_request(
            user_id=request.user.user_id,
            hostel=serializer.validated_data.get("hostel"),
            preferred_room_type=serializer.validated_data.get("preferred_room_type", ""),
            reason=serializer.validated_data.get("reason", ""),
        )
        return Response(AccommodationRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class AccommodationRequestAllotView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.room_assignment.assign")]

    def post(self, request, id):
        req = get_object_or_404(scoping.scope_accommodation_requests(request.user), id=id)
        room_id = request.data.get("room_id")
        if not room_id:
            return Response({"detail": "room_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            assignment = allot_room_from_request(
                request_id=req.id,
                room_id=room_id,
                actor_user_id=request.user.user_id,
            )
            return Response(RoomAssignmentSerializer(assignment).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# 4. Rooms
class RoomListView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.room.view")]

    def get(self, request):
        hostel_id = request.query_params.get("hostel_id")
        qs = scoping.scope_rooms(request.user, hostel_id=hostel_id)
        return Response(RoomSerializer(qs, many=True).data)


class RoomDetailUpdateView(HMBaseView):
    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [MODULE(), HasPermission("hm.room.update")()]
        return [MODULE(), HasPermission("hm.room.view")()]

    def get(self, request, id):
        room = get_object_or_404(scoping.scope_rooms(request.user), id=id)
        return Response(RoomSerializer(room).data)

    def patch(self, request, id):
        room = get_object_or_404(scoping.scope_rooms(request.user), id=id)
        capacity = request.data.get("capacity")
        if capacity is None:
            return Response({"detail": "capacity is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            updated = update_room_capacity(room_id=room.id, new_capacity=int(capacity))
            return Response(RoomSerializer(updated).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# 5. Room Assignments
class RoomAssignmentListView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.room_assignment.view")]

    def get(self, request):
        qs = scoping.scope_room_assignments(request.user)
        return Response(RoomAssignmentSerializer(qs, many=True).data)


class RoomAssignmentVacateView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.room_assignment.update")]

    def post(self, request, id):
        assignment = get_object_or_404(scoping.scope_room_assignments(request.user), id=id)
        reason = request.data.get("reason", "")
        try:
            vacated = vacate_room_assignment(assignment_id=assignment.id, reason=reason)
            return Response(RoomAssignmentSerializer(vacated).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RoomAssignmentExchangeView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.room_assignment.assign")]

    def post(self, request, id):
        assignment = get_object_or_404(scoping.scope_room_assignments(request.user), id=id)
        target_assignment_id = request.data.get("target_assignment_id")
        if not target_assignment_id:
            return Response({"detail": "target_assignment_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        target = get_object_or_404(scoping.scope_room_assignments(request.user), id=target_assignment_id)
        try:
            a, b = exchange_room_assignments(
                assignment_a_id=assignment.id,
                assignment_b_id=target.id,
                actor_user_id=request.user.user_id,
                reason=request.data.get("reason", ""),
            )
            return Response({
                "assignment_a": RoomAssignmentSerializer(a).data,
                "assignment_b": RoomAssignmentSerializer(b).data,
            })
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# 6. Attendance
class AttendanceListCreateView(HMBaseView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("hm.attendance.create")()]
        return [MODULE(), HasPermission("hm.attendance.view")()]

    def get(self, request):
        qs = scoping.scope_attendance(request.user)
        return Response(AttendanceRecordSerializer(qs, many=True).data)

    def post(self, request):
        serializer = AttendanceRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = record_attendance(
            user_id=serializer.validated_data["user_id"],
            hostel=serializer.validated_data["hostel"],
            date=serializer.validated_data["date"],
            is_present=serializer.validated_data.get("is_present", True),
            recorded_by_user_id=request.user.user_id,
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(AttendanceRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class AttendanceSummaryView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.attendance.view")]

    def get(self, request):
        qs = scoping.scope_attendance(request.user)
        total = qs.count()
        present = qs.filter(is_present=True).count()
        absent = total - present
        return Response({"total": total, "present": present, "absent": absent})


# 7. Leave Requests
class LeaveRequestListCreateView(HMBaseView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("hm.leave_request.create")()]
        return [MODULE(), HasPermission("hm.leave_request.view")()]

    def get(self, request):
        qs = scoping.scope_leave_requests(request.user)
        return Response(LeaveRequestSerializer(qs, many=True).data)

    def post(self, request):
        serializer = LeaveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            req = submit_leave_request(
                user_id=request.user.user_id,
                hostel=serializer.validated_data["hostel"],
                start_date=serializer.validated_data["start_date"],
                end_date=serializer.validated_data["end_date"],
                reason=serializer.validated_data["reason"],
            )
            return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveRequestDecisionView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.leave_request.approve")]

    def post(self, request, id):
        req = get_object_or_404(scoping.scope_leave_requests(request.user), id=id)
        decision = request.data.get("decision")
        if decision not in ("approve", "reject"):
            return Response({"detail": "decision must be 'approve' or 'reject'"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            decided = decide_leave_request(
                request_id=req.id,
                decision=decision,
                decided_by_user_id=request.user.user_id,
                remarks=request.data.get("remarks", ""),
            )
            return Response(LeaveRequestSerializer(decided).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LeaveRequestSummaryView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.leave_request.view")]

    def get(self, request):
        qs = scoping.scope_leave_requests(request.user)
        return Response({
            "total": qs.count(),
            "submitted": qs.filter(status="submitted").count(),
            "approved": qs.filter(status="approved").count(),
            "rejected": qs.filter(status="rejected").count(),
        })


# 8. Complaints
class ComplaintListCreateView(HMBaseView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("hm.complaint.create")()]
        return [MODULE(), HasPermission("hm.complaint.view")()]

    def get(self, request):
        qs = scoping.scope_complaints(request.user)
        return Response(ComplaintSerializer(qs, many=True).data)

    def post(self, request):
        serializer = ComplaintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complaint = submit_complaint(
            user_id=request.user.user_id,
            hostel=serializer.validated_data["hostel"],
            category=serializer.validated_data["category"],
            description=serializer.validated_data["description"],
        )
        return Response(ComplaintSerializer(complaint).data, status=status.HTTP_201_CREATED)


class ComplaintEventCreateView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.complaint.update")]

    def post(self, request, id):
        complaint = get_object_or_404(scoping.scope_complaints(request.user), id=id)
        event = request.data.get("event")
        remarks = request.data.get("remarks", "")
        actor_kind = "caretaker" if request.user.kind != "warden" else "warden"
        try:
            updated = record_complaint_event(
                complaint_id=complaint.id,
                event=event,
                actor_user_id=request.user.user_id,
                actor_kind=actor_kind,
                remarks=remarks,
            )
            return Response(ComplaintSerializer(updated).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ComplaintSummaryView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.complaint.view")]

    def get(self, request):
        qs = scoping.scope_complaints(request.user)
        return Response({
            "total": qs.count(),
            "submitted": qs.filter(status="submitted").count(),
            "updated": qs.filter(status="updated").count(),
            "escalated": qs.filter(status="escalated").count(),
            "resolved": qs.filter(status="resolved").count(),
        })


# 9. Guest Bookings
class GuestBookingListCreateView(HMBaseView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("hm.guest_booking.create")()]
        return [MODULE(), HasPermission("hm.guest_booking.view")()]

    def get(self, request):
        qs = scoping.scope_guest_bookings(request.user)
        return Response(GuestBookingSerializer(qs, many=True).data)

    def post(self, request):
        serializer = GuestBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = submit_guest_booking(
                user_id=request.user.user_id,
                hostel=serializer.validated_data["hostel"],
                guest_name=serializer.validated_data["guest_name"],
                relation=serializer.validated_data["relation"],
                start_date=serializer.validated_data["start_date"],
                end_date=serializer.validated_data["end_date"],
            )
            return Response(GuestBookingSerializer(booking).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GuestBookingDecisionView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.guest_booking.approve")]

    def post(self, request, id):
        booking = get_object_or_404(scoping.scope_guest_bookings(request.user), id=id)
        decision = request.data.get("decision")
        try:
            decided = decide_guest_booking(
                booking_id=booking.id,
                decision=decision,
                decided_by_user_id=request.user.user_id,
                remarks=request.data.get("remarks", ""),
            )
            return Response(GuestBookingSerializer(decided).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# 10. Extended Stays
class ExtendedStayListCreateView(HMBaseView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("hm.extended_stay_request.create")()]
        return [MODULE(), HasPermission("hm.extended_stay_request.view")()]

    def get(self, request):
        qs = scoping.scope_extended_stays(request.user)
        return Response(ExtendedStayRequestSerializer(qs, many=True).data)

    def post(self, request):
        serializer = ExtendedStayRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            stay = submit_extended_stay(
                user_id=request.user.user_id,
                hostel=serializer.validated_data["hostel"],
                start_date=serializer.validated_data["start_date"],
                end_date=serializer.validated_data["end_date"],
                reason=serializer.validated_data["reason"],
            )
            return Response(ExtendedStayRequestSerializer(stay).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ExtendedStayDecisionView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.extended_stay_request.approve")]

    def post(self, request, id):
        stay = get_object_or_404(scoping.scope_extended_stays(request.user), id=id)
        decision = request.data.get("decision")
        try:
            decided = decide_extended_stay(
                request_id=stay.id,
                decision=decision,
                decided_by_user_id=request.user.user_id,
                remarks=request.data.get("remarks", ""),
            )
            return Response(ExtendedStayRequestSerializer(decided).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# 11. Fines
class FineListCreateView(HMBaseView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("hm.fine.create")()]
        return [MODULE(), HasPermission("hm.fine.view")()]

    def get(self, request):
        qs = scoping.scope_fines(request.user)
        return Response(FineRecordSerializer(qs, many=True).data)

    def post(self, request):
        serializer = FineRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fine = record_fine(
            user_id=serializer.validated_data["user_id"],
            hostel=serializer.validated_data["hostel"],
            amount=serializer.validated_data["amount"],
            reason=serializer.validated_data["reason"],
            imposed_by_user_id=request.user.user_id,
        )
        return Response(FineRecordSerializer(fine).data, status=status.HTTP_201_CREATED)


class FineSummaryView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.fine.view")]

    def get(self, request):
        qs = scoping.scope_fines(request.user)
        total_amount = sum(f.amount for f in qs)
        return Response({"total_fines": qs.count(), "total_amount": float(total_amount)})


# 12. Inventory
class InventoryListCreateView(HMBaseView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("hm.inventory_item.create")()]
        return [MODULE(), HasPermission("hm.inventory_item.view")()]

    def get(self, request):
        qs = scoping.scope_inventory(request.user)
        return Response(InventoryItemSerializer(qs, many=True).data)

    def post(self, request):
        serializer = InventoryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = create_inventory_item(
            hostel=serializer.validated_data["hostel"],
            name=serializer.validated_data["name"],
            quantity=serializer.validated_data.get("quantity", 0),
            description=serializer.validated_data.get("description", ""),
            user_id=request.user.user_id,
        )
        return Response(InventoryItemSerializer(item).data, status=status.HTTP_201_CREATED)


class InventoryUpdateView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.inventory_item.update")]

    def patch(self, request, id):
        item = get_object_or_404(scoping.scope_inventory(request.user), id=id)
        quantity_change = request.data.get("quantity_change")
        if quantity_change is None:
            return Response({"detail": "quantity_change is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            updated = update_inventory_item(
                item_id=item.id,
                quantity_change=int(quantity_change),
                reason=request.data.get("reason", ""),
                user_id=request.user.user_id,
            )
            return Response(InventoryItemSerializer(updated).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# 13. Guard Shifts
class GuardShiftListCreateView(HMBaseView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("hm.guard_shift.create")()]
        return [MODULE(), HasPermission("hm.guard_shift.view")()]

    def get(self, request):
        qs = scoping.scope_guard_shifts(request.user)
        return Response(GuardShiftSerializer(qs, many=True).data)

    def post(self, request):
        serializer = GuardShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shift = create_guard_shift(
            hostel=serializer.validated_data["hostel"],
            guard_name=serializer.validated_data["guard_name"],
            shift_date=serializer.validated_data["shift_date"],
            shift_type=serializer.validated_data["shift_type"],
            notes=serializer.validated_data.get("notes", ""),
        )
        return Response(GuardShiftSerializer(shift).data, status=status.HTTP_201_CREATED)


# 14. Notices
class NoticeListCreateView(HMBaseView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("hm.notice.create")()]
        return [MODULE(), HasPermission("hm.notice.view")()]

    def get(self, request):
        qs = scoping.scope_notices(request.user)
        return Response(NoticeSerializer(qs, many=True).data)

    def post(self, request):
        serializer = NoticeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notice = create_notice(
            hostel=serializer.validated_data["hostel"],
            title=serializer.validated_data["title"],
            content=serializer.validated_data["content"],
        )
        return Response(NoticeSerializer(notice).data, status=status.HTTP_201_CREATED)


class NoticePublishView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.notice.publish")]

    def post(self, request, id):
        notice = get_object_or_404(scoping.scope_notices(request.user), id=id)
        try:
            published = publish_notice(notice_id=notice.id, user_id=request.user.user_id)
            return Response(NoticeSerializer(published).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class NoticeWithdrawView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.notice.update")]

    def post(self, request, id):
        notice = get_object_or_404(scoping.scope_notices(request.user), id=id)
        try:
            withdrawn = withdraw_notice(notice_id=notice.id)
            return Response(NoticeSerializer(withdrawn).data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# 15. Reports
class ReportView(HMBaseView):
    permission_classes = [MODULE, HasPermission("hm.report.view")]

    def get(self, request, report_code):
        if report_code == "occupancy":
            rooms = scoping.scope_rooms(request.user)
            total_capacity = sum(r.capacity for r in rooms)
            total_occupied = sum(r.occupied_count for r in rooms)
            return Response({
                "report_code": report_code,
                "total_rooms": rooms.count(),
                "total_capacity": total_capacity,
                "total_occupied": total_occupied,
                "available_capacity": max(0, total_capacity - total_occupied),
            })
        return Response({"detail": f"Unknown report code: {report_code}"}, status=status.HTTP_404_NOT_FOUND)
