from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
try:
    from hostel_management.models import (
        Hostel, Room, AccommodationRequest, AttendanceRecord,
        LeaveRequest, HostelComplaint, GuestRoomBooking,
        ExtendedStayRequest, HostelFine, HostelInventory,
        SecurityGuardShift, HostelNotice
    )
    from hostel_management.serializers import (
        HostelSerializer, RoomSerializer, AccommodationRequestSerializer,
        AttendanceRecordSerializer, LeaveRequestSerializer,
        HostelComplaintSerializer, GuestRoomBookingSerializer,
        ExtendedStayRequestSerializer, HostelFineSerializer,
        HostelInventorySerializer, SecurityGuardShiftSerializer,
        HostelNoticeSerializer
    )
    from hostel_management import services
except ImportError:
    from .models import (
        Hostel, Room, AccommodationRequest, AttendanceRecord,
        LeaveRequest, HostelComplaint, GuestRoomBooking,
        ExtendedStayRequest, HostelFine, HostelInventory,
        SecurityGuardShift, HostelNotice
    )
    from .serializers import (
        HostelSerializer, RoomSerializer, AccommodationRequestSerializer,
        AttendanceRecordSerializer, LeaveRequestSerializer,
        HostelComplaintSerializer, GuestRoomBookingSerializer,
        ExtendedStayRequestSerializer, HostelFineSerializer,
        HostelInventorySerializer, SecurityGuardShiftSerializer,
        HostelNoticeSerializer
    )
    from . import services


class HostelListCreateView(APIView):
    def get(self, request):
        hostels = Hostel.objects.all()
        return Response(HostelSerializer(hostels, many=True).data)

    def post(self, request):
        name = request.data.get("name")
        code = request.data.get("code")
        cap = request.data.get("total_capacity", 100)
        hostel = services.create_hostel(name, code, cap)
        return Response(HostelSerializer(hostel).data, status=status.HTTP_201_CREATED)


class AccommodationRequestView(APIView):
    def get(self, request):
        student_id = request.query_params.get("student_id")
        qs = AccommodationRequest.objects.all()
        if student_id:
            qs = qs.filter(student_id=student_id)
        return Response(AccommodationRequestSerializer(qs, many=True).data)

    def post(self, request):
        student_id = request.data.get("student_id")
        hostel_id = request.data.get("hostel_id")
        pref = request.data.get("preferred_room_type", "")
        req = services.submit_accommodation_request(student_id, hostel_id, pref)
        return Response(AccommodationRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class AllotRoomView(APIView):
    def post(self, request):
        req_id = request.data.get("request_id")
        room_id = request.data.get("room_id")
        admin_id = request.data.get("admin_id", 1)
        try:
            req = services.allot_room(req_id, room_id, admin_id)
            return Response(AccommodationRequestSerializer(req).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RoomExchangeView(APIView):
    def post(self, request):
        s1 = request.data.get("student1_id")
        r1 = request.data.get("room1_id")
        s2 = request.data.get("student2_id")
        r2 = request.data.get("room2_id")
        cid = request.data.get("caretaker_id", 1)
        try:
            services.exchange_rooms(s1, r1, s2, r2, cid)
            return Response({"message": "Room exchange successful"})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AttendanceView(APIView):
    def get(self, request):
        student_id = request.query_params.get("student_id")
        if student_id:
            records = services.get_student_attendance(student_id)
            return Response(AttendanceRecordSerializer(records, many=True).data)
        return Response(AttendanceRecordSerializer(AttendanceRecord.objects.all(), many=True).data)

    def post(self, request):
        sid = request.data.get("student_id")
        hid = request.data.get("hostel_id")
        dt = request.data.get("date")
        st = request.data.get("status")
        cid = request.data.get("caretaker_id", 1)
        rec = services.record_student_attendance(sid, hid, dt, st, cid)
        return Response(AttendanceRecordSerializer(rec).data, status=status.HTTP_201_CREATED)


class LeaveRequestView(APIView):
    def get(self, request):
        student_id = request.query_params.get("student_id")
        qs = LeaveRequest.objects.all()
        if student_id:
            qs = qs.filter(student_id=student_id)
        return Response(LeaveRequestSerializer(qs, many=True).data)

    def post(self, request):
        sid = request.data.get("student_id")
        hid = request.data.get("hostel_id")
        sdate = request.data.get("start_date")
        edate = request.data.get("end_date")
        reason = request.data.get("reason")
        req = services.submit_leave_request(sid, hid, sdate, edate, reason)
        return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class LeaveReviewView(APIView):
    def post(self, request):
        lid = request.data.get("leave_id")
        decision = request.data.get("decision")
        cid = request.data.get("caretaker_id", 1)
        note = request.data.get("note", "")
        try:
            req = services.review_leave_request(lid, decision, cid, note)
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ComplaintView(APIView):
    def get(self, request):
        hid = request.query_params.get("hostel_id")
        qs = HostelComplaint.objects.all()
        if hid:
            qs = qs.filter(hostel_id=hid)
        return Response(HostelComplaintSerializer(qs, many=True).data)

    def post(self, request):
        sid = request.data.get("student_id")
        hid = request.data.get("hostel_id")
        cat = request.data.get("category")
        desc = request.data.get("description")
        att = request.data.get("attachment_url", "")
        try:
            complaint = services.submit_hostel_complaint(sid, hid, cat, desc, att)
            return Response(HostelComplaintSerializer(complaint).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ComplaintUpdateView(APIView):
    def post(self, request):
        cid = request.data.get("complaint_id")
        st = request.data.get("status")
        action = request.data.get("action_taken", "")
        uid = request.data.get("updater_id", 1)
        try:
            c = services.update_complaint_status(cid, st, action, uid)
            return Response(HostelComplaintSerializer(c).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GuestRoomBookingView(APIView):
    def post(self, request):
        sid = request.data.get("student_id")
        hid = request.data.get("hostel_id")
        name = request.data.get("guest_name")
        rnum = request.data.get("room_number")
        sdate = request.data.get("start_date")
        edate = request.data.get("end_date")
        b = services.submit_guest_room_booking(sid, hid, name, rnum, sdate, edate)
        return Response(GuestRoomBookingSerializer(b).data, status=status.HTTP_201_CREATED)


class ExtendedStayView(APIView):
    def post(self, request):
        sid = request.data.get("student_id")
        hid = request.data.get("hostel_id")
        sdate = request.data.get("start_date")
        edate = request.data.get("end_date")
        reason = request.data.get("reason")
        req = services.submit_extended_stay_request(sid, hid, sdate, edate, reason)
        return Response(ExtendedStayRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class FineView(APIView):
    def get(self, request):
        sid = request.query_params.get("student_id")
        qs = HostelFine.objects.filter(student_id=sid) if sid else HostelFine.objects.all()
        return Response(HostelFineSerializer(qs, many=True).data)

    def post(self, request):
        sid = request.data.get("student_id")
        hid = request.data.get("hostel_id")
        reason = request.data.get("reason")
        amt = request.data.get("amount")
        fdate = request.data.get("date")
        cid = request.data.get("caretaker_id", 1)
        try:
            fine = services.record_hostel_fine(sid, hid, reason, amt, fdate, cid)
            return Response(HostelFineSerializer(fine).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class NoticeView(APIView):
    def get(self, request):
        hid = request.query_params.get("hostel_id")
        notices = services.get_hostel_notices(hid) if hid else HostelNotice.objects.all()
        return Response(HostelNoticeSerializer(notices, many=True).data)

    def post(self, request):
        hid = request.data.get("hostel_id")
        title = request.data.get("title")
        content = request.data.get("content")
        pid = request.data.get("poster_id", 1)
        role = request.data.get("role", "caretaker")
        notice = services.publish_hostel_notice(hid, title, content, pid, role)
        return Response(HostelNoticeSerializer(notice).data, status=status.HTTP_201_CREATED)


class OperationalReportView(APIView):
    def get(self, request):
        hid = request.query_params.get("hostel_id")
        if not hid:
            return Response({"error": "hostel_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        report = services.generate_hostel_summary_report(hid)
        return Response(report)
