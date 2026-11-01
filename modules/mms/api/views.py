"""API views for Mess Management System (MMS)."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.mms.api.serializers import (
    AssignRoleInputSerializer,
    DailyMenuItemSerializer,
    MessFeedbackSerializer,
    MessRegistrationSerializer,
    MessRoleAssignmentSerializer,
    OpenWindowInputSerializer,
    RebateRequestSerializer,
    RegistrationWindowSerializer,
    ReviewRebateInputSerializer,
    ReviewRegistrationInputSerializer,
    SubmitDeregistrationInputSerializer,
    SubmitFeedbackInputSerializer,
    SubmitRebateInputSerializer,
    SubmitRegistrationInputSerializer,
    UpdateMenuItemInputSerializer,
)
from modules.mms.selectors import mms as selectors
from modules.mms.services import mms as services


class RoleAssignmentView(APIView):
    """MMS-UC-001: Assign or reassign MMS operational roles (Mess Admin)."""

    permission_classes = [
        HasModuleGrant("mess_module"),
        HasPermission("mess_module.role.manage"),
    ]

    def get(self, request):
        role = request.query_params.get("role")
        assignments = selectors.list_role_assignments(role=role)
        ser = MessRoleAssignmentSerializer(assignments, many=True)
        return Response(ser.data)

    def post(self, request):
        ser = AssignRoleInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            assignment = services.assign_mess_role(
                employee_id=data["employee_id"],
                role=data["role"],
                start_date=data["start_date"],
                end_date=data.get("end_date"),
                assigned_by_id=request.principal.user_id,
                remarks=data.get("remarks", ""),
            )
            return Response(
                MessRoleAssignmentSerializer(assignment).data,
                status=status.HTTP_201_CREATED,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ActiveRolesView(APIView):
    """View active Caretaker and Warden (BR-MMS-003, BR-MMS-004)."""

    permission_classes = [
        HasModuleGrant("mess_module"),
        HasPermission("mess_module.menu.view"),
    ]

    def get(self, request):
        caretaker = selectors.get_active_role_assignment("caretaker")
        warden = selectors.get_active_role_assignment("warden")
        return Response({
            "caretaker": MessRoleAssignmentSerializer(caretaker).data if caretaker else None,
            "warden": MessRoleAssignmentSerializer(warden).data if warden else None,
        })


class RegistrationWindowView(APIView):
    """MMS-UC-002: Open or view mess registration window."""

    permission_classes = [
        HasModuleGrant("mess_module"),
        HasPermission("mess_module.menu.view"),
    ]

    def get(self, request):
        mess_name = request.query_params.get("mess_name", "Central Mess")
        window = selectors.get_current_registration_window(mess_name=mess_name)
        if not window:
            return Response(
                {"detail": "No open registration window."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(RegistrationWindowSerializer(window).data)

    def post(self, request):
        # Only Caretaker can open window (BR-MMS-008)
        if not request.principal.has_permission("mess_module.registration.review"):
            return Response(
                {"detail": "Only active Caretaker can open registration window."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = OpenWindowInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            window = services.open_registration_window(
                opened_by_id=request.principal.user_id,
                name=data["name"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                mess_name=data.get("mess_name", "Central Mess"),
            )
            return Response(
                RegistrationWindowSerializer(window).data,
                status=status.HTTP_201_CREATED,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class StudentRegistrationView(APIView):
    """MMS-UC-003: Student submit registration and view own registration."""

    permission_classes = [
        HasModuleGrant("mess_module"),
        HasPermission("mess_module.registration.submit"),
    ]

    def get(self, request):
        reg = selectors.get_student_registration(student_id=request.principal.user_id)
        if not reg:
            return Response(
                {"detail": "No registration record found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(MessRegistrationSerializer(reg).data)

    def post(self, request):
        ser = SubmitRegistrationInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            reg = services.submit_registration(
                student_id=request.principal.user_id,
                start_date=data["start_date"],
                end_date=data.get("end_date"),
                mess_name=data.get("mess_name", "Central Mess"),
                remarks=data.get("remarks", ""),
            )
            return Response(MessRegistrationSerializer(reg).data, status=status.HTTP_201_CREATED)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class StudentDeregistrationView(APIView):
    """MMS-UC-005: Student submit deregistration request."""

    permission_classes = [
        HasModuleGrant("mess_module"),
        HasPermission("mess_module.registration.submit"),
    ]

    def post(self, request, registration_id: int):
        ser = SubmitDeregistrationInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            reg = services.submit_deregistration(
                registration_id=registration_id,
                student_id=request.principal.user_id,
                reason=data["reason"],
            )
            return Response(MessRegistrationSerializer(reg).data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class RegistrationsListView(APIView):
    """MMS-UC-007: Caretaker and Warden view student registrations."""

    permission_classes = [
        HasModuleGrant("mess_module"),
        HasPermission("mess_module.registration.review"),
    ]

    def get(self, request):
        status_filter = request.query_params.get("status")
        mess_name = request.query_params.get("mess_name")
        regs = selectors.list_registrations(status=status_filter, mess_name=mess_name)
        ser = MessRegistrationSerializer(regs, many=True)
        return Response(ser.data)


class ReviewRegistrationView(APIView):
    """MMS-UC-004: Caretaker review registration request."""

    permission_classes = [
        HasModuleGrant("mess_module"),
        HasPermission("mess_module.registration.review"),
    ]

    def post(self, request, registration_id: int):
        ser = ReviewRegistrationInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            reg = services.review_registration(
                registration_id=registration_id,
                reviewed_by_id=request.principal.user_id,
                approve=data["approve"],
                remarks=data.get("remarks", ""),
            )
            return Response(MessRegistrationSerializer(reg).data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class ReviewDeregistrationView(APIView):
    """MMS-UC-006: Caretaker review deregistration request."""

    permission_classes = [
        HasModuleGrant("mess_module"),
        HasPermission("mess_module.registration.review"),
    ]

    def post(self, request, registration_id: int):
        approve = request.data.get("approve", True)
        remarks = request.data.get("remarks", "")
        try:
            reg = services.review_deregistration(
                registration_id=registration_id,
                reviewed_by_id=request.principal.user_id,
                approve=approve,
                remarks=remarks,
            )
            return Response(MessRegistrationSerializer(reg).data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class WeeklyMenuView(APIView):
    """MMS-UC-008 & MMS-UC-009: View or update weekly menu."""

    permission_classes = [
        HasModuleGrant("mess_module"),
        HasPermission("mess_module.menu.view"),
    ]

    def get(self, request):
        mess_name = request.query_params.get("mess_name", "Central Mess")
        items = selectors.get_weekly_menu(mess_name=mess_name)
        ser = DailyMenuItemSerializer(items, many=True)
        return Response(ser.data)

    def post(self, request):
        if not request.principal.has_permission("mess_module.menu.manage"):
            return Response(
                {"detail": "Only Caretaker can update weekly menu."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = UpdateMenuItemInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        item = services.update_menu_item(
            updated_by_id=request.principal.user_id,
            day_of_week=data["day_of_week"],
            meal_time=data["meal_time"],
            items=data["items"],
            mess_name=data.get("mess_name", "Central Mess"),
        )
        return Response(DailyMenuItemSerializer(item).data)


class StudentRebatesView(APIView):
    """MMS-UC-014: Student view and apply for rebate."""

    permission_classes = [
        HasModuleGrant("mess_module"),
        HasPermission("mess_module.rebate.apply"),
    ]

    def get(self, request):
        rebates = selectors.list_rebate_requests(student_id=request.principal.user_id)
        ser = RebateRequestSerializer(rebates, many=True)
        return Response(ser.data)

    def post(self, request):
        ser = SubmitRebateInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            rebate = services.submit_rebate_request(
                student_id=request.principal.user_id,
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data["reason"],
                mess_name=data.get("mess_name", "Central Mess"),
            )
            return Response(
                RebateRequestSerializer(rebate).data,
                status=status.HTTP_201_CREATED,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class RebatesListView(APIView):
    """MMS-UC-015: Caretaker list and review rebate requests."""

    permission_classes = [
        HasModuleGrant("mess_module"),
        HasPermission("mess_module.rebate.review"),
    ]

    def get(self, request):
        status_filter = request.query_params.get("status")
        student_id = request.query_params.get("student_id")
        sid = int(student_id) if student_id else None
        rebates = selectors.list_rebate_requests(student_id=sid, status=status_filter)
        ser = RebateRequestSerializer(rebates, many=True)
        return Response(ser.data)


class ReviewRebateView(APIView):
    """MMS-UC-015: Caretaker approve/reject rebate."""

    permission_classes = [
        HasModuleGrant("mess_module"),
        HasPermission("mess_module.rebate.review"),
    ]

    def post(self, request, rebate_id: int):
        ser = ReviewRebateInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            rebate = services.review_rebate_request(
                rebate_id=rebate_id,
                reviewed_by_id=request.principal.user_id,
                approve=data["approve"],
                approved_start_date=data.get("approved_start_date"),
                approved_end_date=data.get("approved_end_date"),
                remarks=data.get("remarks", ""),
            )
            return Response(RebateRequestSerializer(rebate).data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class FeedbackView(APIView):
    """MMS-UC-012 & MMS-UC-013: Submit and view feedback."""

    permission_classes = [
        HasModuleGrant("mess_module"),
        HasPermission("mess_module.feedback.submit"),
    ]

    def get(self, request):
        if not request.principal.has_permission("mess_module.feedback.view"):
            return Response(
                {"detail": "Not authorized to view feedback."},
                status=status.HTTP_403_FORBIDDEN,
            )
        mess_name = request.query_params.get("mess_name")
        feedbacks = selectors.list_feedbacks(mess_name=mess_name)
        ser = MessFeedbackSerializer(feedbacks, many=True)
        return Response(ser.data)

    def post(self, request):
        ser = SubmitFeedbackInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            fb = services.submit_feedback(
                student_id=request.principal.user_id,
                rating=data["rating"],
                category=data["category"],
                comments=data["comments"],
                mess_name=data.get("mess_name", "Central Mess"),
            )
            return Response(MessFeedbackSerializer(fb).data, status=status.HTTP_201_CREATED)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
