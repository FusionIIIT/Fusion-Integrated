"""API views for Mess Management System (MMS)."""

from datetime import date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.mms import selectors, services
from modules.mms.api import serializers

MODULE_GRANT = HasModuleGrant("mess_module")


class MenuView(APIView):
    permission_classes = [IsAuthenticated, MODULE_GRANT, HasPermission("mess_module.menu.view")]

    def get(self, request):
        mess_name = request.query_params.get("mess_name", "Central Mess")
        menu = selectors.get_weekly_menu(mess_name)
        serializer = serializers.DailyMenuItemSerializer(menu, many=True)
        return Response({"results": serializer.data})


class ManageMenuView(APIView):
    permission_classes = [IsAuthenticated, MODULE_GRANT, HasPermission("mess_module.menu.manage")]

    def post(self, request):
        item = services.update_menu_item(
            mess_name=request.data.get("mess_name"),
            day_of_week=request.data.get("day_of_week"),
            meal_time=request.data.get("meal_time"),
            menu_description=request.data.get("menu_description"),
            updated_by_id=request.user.id,
        )
        return Response(serializers.DailyMenuItemSerializer(item).data, status=status.HTTP_201_CREATED)


class RegistrationWindowView(APIView):
    permission_classes = [IsAuthenticated, MODULE_GRANT, HasPermission("mess_module.registration.review")]

    def get(self, request):
        windows = selectors.get_open_registration_windows()
        return Response({"results": serializers.RegistrationWindowSerializer(windows, many=True).data})

    def post(self, request):
        semester = request.data.get("semester")
        start_date = date.fromisoformat(request.data.get("start_date"))
        end_date = date.fromisoformat(request.data.get("end_date"))
        window = services.open_registration_window(
            semester=semester,
            start_date=start_date,
            end_date=end_date,
            created_by_id=request.user.id,
        )
        return Response(serializers.RegistrationWindowSerializer(window).data, status=status.HTTP_201_CREATED)


class RegistrationView(APIView):
    permission_classes = [IsAuthenticated, MODULE_GRANT, HasPermission("mess_module.registration.submit")]

    def get(self, request):
        student_id = request.query_params.get("student_id") or request.user.id
        regs = selectors.get_student_registrations(int(student_id))
        return Response({"results": serializers.MessRegistrationSerializer(regs, many=True).data})

    def post(self, request):
        try:
            reg = services.submit_registration(
                student_id=request.user.id,
                mess_name=request.data.get("mess_name"),
                window_id=int(request.data.get("window_id")),
            )
            return Response(serializers.MessRegistrationSerializer(reg).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReviewRegistrationView(APIView):
    permission_classes = [IsAuthenticated, MODULE_GRANT, HasPermission("mess_module.registration.review")]

    def post(self, request, pk: int):
        approve = request.data.get("approve", True)
        reason = request.data.get("rejection_reason", "")
        reg = services.review_registration(
            registration_id=pk,
            reviewer_id=request.user.id,
            approve=approve,
            rejection_reason=reason,
        )
        return Response(serializers.MessRegistrationSerializer(reg).data)


class RebateView(APIView):
    permission_classes = [IsAuthenticated, MODULE_GRANT, HasPermission("mess_module.rebate.submit")]

    def get(self, request):
        student_id = request.query_params.get("student_id") or request.user.id
        rebates = selectors.get_student_rebates(int(student_id))
        return Response({"results": serializers.RebateRequestSerializer(rebates, many=True).data})

    def post(self, request):
        try:
            start_date = date.fromisoformat(request.data.get("start_date"))
            end_date = date.fromisoformat(request.data.get("end_date"))
            rebate = services.submit_rebate_request(
                student_id=request.user.id,
                mess_name=request.data.get("mess_name"),
                start_date=start_date,
                end_date=end_date,
                reason=request.data.get("reason", ""),
            )
            return Response(serializers.RebateRequestSerializer(rebate).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReviewRebateView(APIView):
    permission_classes = [IsAuthenticated, MODULE_GRANT, HasPermission("mess_module.rebate.review")]

    def get(self, request):
        mess_name = request.query_params.get("mess_name")
        rebates = selectors.get_mess_rebates(mess_name)
        return Response({"results": serializers.RebateRequestSerializer(rebates, many=True).data})

    def post(self, request, pk: int):
        approve = request.data.get("approve", True)
        notes = request.data.get("review_notes", "")
        rebate = services.review_rebate_request(
            rebate_id=pk,
            reviewer_id=request.user.id,
            approve=approve,
            review_notes=notes,
        )
        return Response(serializers.RebateRequestSerializer(rebate).data)


class FeedbackView(APIView):
    permission_classes = [IsAuthenticated, MODULE_GRANT, HasPermission("mess_module.feedback.submit")]

    def get(self, request):
        feedbacks = selectors.get_feedbacks()
        return Response({"results": serializers.MessFeedbackSerializer(feedbacks, many=True).data})

    def post(self, request):
        feedback = services.submit_feedback(
            student_id=request.user.id,
            mess_name=request.data.get("mess_name"),
            category=request.data.get("category", "GENERAL"),
            comment=request.data.get("comment", ""),
        )
        return Response(serializers.MessFeedbackSerializer(feedback).data, status=status.HTTP_201_CREATED)


class AssignRoleView(APIView):
    permission_classes = [IsAuthenticated, MODULE_GRANT, HasPermission("mess_module.role.assign")]

    def post(self, request):
        try:
            assignment = services.assign_mess_role(
                mess_name=request.data.get("mess_name"),
                role=request.data.get("role"),
                employee_id=int(request.data.get("employee_id")),
                assigned_by_id=request.user.id,
            )
            return Response(serializers.MessRoleAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
