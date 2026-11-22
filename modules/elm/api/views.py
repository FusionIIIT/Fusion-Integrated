# from datetime import date
# # from rest_framework import permissions, status
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from rest_framework import status
# from fusion_auth.permissions import HasModuleGrant, HasPermission

# MODULE = HasModuleGrant("elm")

# P_VIEW_SELF = "elm.leave.view_self"
# P_APPLY = "elm.leave.apply"
# P_SUBSTITUTE = "elm.leave.substitute"
# P_APPROVE = "elm.leave.approve"

# from modules.elm.api.serializers import (
#     ApplyLeaveInputSerializer,
#     DecisionInputSerializer,
#     HolidayCalendarSerializer,
#     LeaveBalanceSerializer,
#     LeaveRequestSerializer,
#     SubstituteResponseSerializer,
# )
# from modules.elm.models import HolidayCalendar, LeaveRequest
# from modules.elm.selectors.leave import (
#     get_employee_leave_requests,
#     get_leave_balances,
#     get_pending_substitute_requests,
# )
# from modules.elm.services.leave import (
#     apply_leave,
#     cancel_leave,
#     record_decision,
#     respond_substitute,
#     withdraw_leave,
# )


# class LeaveBalanceView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def get(self, request):
#         user_id = request.user.id
#         year = request.query_params.get("year", date.today().year)
#         try:
#             year = int(year)
#         except ValueError:
#             year = date.today().year
#         balances = get_leave_balances(employee_id=user_id, year=year)
#         serializer = LeaveBalanceSerializer(balances, many=True)
#         return Response(serializer.data)


# class LeaveRequestListView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def get(self, request):
#         user_id = request.user.id
#         requests = get_employee_leave_requests(employee_id=user_id)
#         serializer = LeaveRequestSerializer(requests, many=True)
#         return Response(serializer.data)

#     def post(self, request):
#         serializer = ApplyLeaveInputSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         data = serializer.validated_data

#         try:
#             leave_req = apply_leave(
#                 applicant_id=request.user.id,
#                 leave_type=data["leave_type"],
#                 start_date=data["start_date"],
#                 end_date=data["end_date"],
#                 purpose=data["purpose"],
#                 is_half_day=data.get("is_half_day", False),
#                 half_day_period=data.get("half_day_period"),
#                 is_station_leave=data.get("is_station_leave", False),
#                 station_details=data.get("station_details"),
#                 substitute_id=data.get("substitute_id"),
#             )
#         except ValueError as err:
#             return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

#         return Response(LeaveRequestSerializer(leave_req).data, status=status.HTTP_201_CREATED)


# class LeaveRequestDetailView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def get(self, request, pk: int):
#         leave_req = LeaveRequest.objects.filter(id=pk).first()
#         if not leave_req:
#             return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
#         return Response(LeaveRequestSerializer(leave_req).data)


# class SubstituteRequestsView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def get(self, request):
#         requests = get_pending_substitute_requests(substitute_id=request.user.id)
#         return Response(LeaveRequestSerializer(requests, many=True).data)


# class SubstituteRespondView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, pk: int):
#         serializer = SubstituteResponseSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         data = serializer.validated_data

#         try:
#             leave_req = respond_substitute(
#                 request_id=pk,
#                 substitute_id=request.user.id,
#                 accepted=data["accepted"],
#                 comments=data.get("comments", ""),
#             )
#         except (PermissionError, ValueError) as err:
#             return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

#         return Response(LeaveRequestSerializer(leave_req).data)


# class DecisionView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, pk: int):
#         serializer = DecisionInputSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         data = serializer.validated_data

#         try:
#             leave_req = record_decision(
#                 request_id=pk,
#                 actor_id=request.user.id,
#                 action=data["action"],
#                 comments=data.get("comments", ""),
#             )
#         except (PermissionError, ValueError) as err:
#             return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

#         return Response(LeaveRequestSerializer(leave_req).data)


# class WithdrawLeaveView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, pk: int):
#         reason = request.data.get("reason", "")
#         try:
#             leave_req = withdraw_leave(
#                 request_id=pk,
#                 applicant_id=request.user.id,
#                 reason=reason,
#             )
#         except (PermissionError, ValueError) as err:
#             return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

#         return Response(LeaveRequestSerializer(leave_req).data)


# class CancelLeaveView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, pk: int):
#         reason = request.data.get("reason", "")
#         try:
#             leave_req = cancel_leave(
#                 request_id=pk,
#                 applicant_id=request.user.id,
#                 reason=reason,
#             )
#         except (PermissionError, ValueError) as err:
#             return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

#         return Response(LeaveRequestSerializer(leave_req).data)


# class HolidayCalendarView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def get(self, request):
#         year = request.query_params.get("year", date.today().year)
#         try:
#             year = int(year)
#         except ValueError:
#             year = date.today().year
#         holidays = HolidayCalendar.objects.filter(year=year)
#         return Response(HolidayCalendarSerializer(holidays, many=True).data)





from datetime import date

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission

from modules.elm.api.serializers import (
    ApplyLeaveInputSerializer,
    DecisionInputSerializer,
    HolidayCalendarSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    SubstituteResponseSerializer,
)
from modules.elm.models import HolidayCalendar, LeaveRequest
from modules.elm.selectors.leave import (
    get_employee_leave_requests,
    get_leave_balances,
    get_pending_substitute_requests,
)
from modules.elm.services.leave import (
    apply_leave,
    cancel_leave,
    record_decision,
    respond_substitute,
    withdraw_leave,
)

MODULE = HasModuleGrant("elm")

P_VIEW_SELF = "elm.leave.view_self"
P_APPLY = "elm.leave.apply"
P_SUBSTITUTE = "elm.leave.substitute"
P_APPROVE = "elm.leave.approve"


class LeaveBalanceView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        user_id = request.user.user_id
        year = request.query_params.get("year", date.today().year)
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = date.today().year

        balances = get_leave_balances(employee_id=user_id, year=year)
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class LeaveRequestListView(APIView):
    def get_permissions(self):
        code = P_APPLY if self.request.method == "POST" else P_VIEW_SELF
        return [MODULE(), HasPermission(code)()]

    def get(self, request):
        requests = get_employee_leave_requests(
            employee_id=request.user.user_id
        )
        return Response(LeaveRequestSerializer(requests, many=True).data)

    def post(self, request):
        serializer = ApplyLeaveInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            leave_req = apply_leave(
                applicant_id=request.user.user_id,
                leave_type=data["leave_type"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                purpose=data["purpose"],
                is_half_day=data.get("is_half_day", False),
                half_day_period=data.get("half_day_period"),
                is_station_leave=data.get("is_station_leave", False),
                station_details=data.get("station_details"),
                substitute_id=data.get("substitute_id"),
            )
        except ValueError as err:
            return Response(
                {"detail": str(err)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            LeaveRequestSerializer(leave_req).data,
            status=status.HTTP_201_CREATED,
        )


class LeaveRequestDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request, pk: int):
        leave_req = LeaveRequest.objects.filter(
            id=pk,
            applicant_id=request.user.user_id,
        ).first()

        if not leave_req:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(LeaveRequestSerializer(leave_req).data)


class SubstituteRequestsView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    def get(self, request):
        requests = get_pending_substitute_requests(
            substitute_id=request.user.user_id
        )
        return Response(LeaveRequestSerializer(requests, many=True).data)


class SubstituteRespondView(APIView):
    permission_classes = [MODULE, HasPermission(P_SUBSTITUTE)]

    def post(self, request, pk: int):
        serializer = SubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            leave_req = respond_substitute(
                request_id=pk,
                substitute_id=request.user.user_id,
                accepted=data["accepted"],
                comments=data.get("comments", ""),
            )
        except LeaveRequest.DoesNotExist:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except (PermissionError, ValueError) as err:
            return Response(
                {"detail": str(err)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(LeaveRequestSerializer(leave_req).data)


class DecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    def post(self, request, pk: int):
        serializer = DecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            leave_req = record_decision(
                request_id=pk,
                actor_id=request.user.user_id,
                action=data["action"],
                comments=data.get("comments", ""),
            )
        except LeaveRequest.DoesNotExist:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except (PermissionError, ValueError) as err:
            return Response(
                {"detail": str(err)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(LeaveRequestSerializer(leave_req).data)


class WithdrawLeaveView(APIView):
    permission_classes = [MODULE, HasPermission(P_APPLY)]

    def post(self, request, pk: int):
        reason = request.data.get("reason", "")
        try:
            leave_req = withdraw_leave(
                request_id=pk,
                applicant_id=request.user.user_id,
                reason=reason,
            )
        except LeaveRequest.DoesNotExist:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except (PermissionError, ValueError) as err:
            return Response(
                {"detail": str(err)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(LeaveRequestSerializer(leave_req).data)


class CancelLeaveView(APIView):
    permission_classes = [MODULE, HasPermission(P_APPLY)]

    def post(self, request, pk: int):
        reason = request.data.get("reason", "")
        try:
            leave_req = cancel_leave(
                request_id=pk,
                applicant_id=request.user.user_id,
                reason=reason,
            )
        except LeaveRequest.DoesNotExist:
            return Response(
                {"detail": "Not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except (PermissionError, ValueError) as err:
            return Response(
                {"detail": str(err)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(LeaveRequestSerializer(leave_req).data)


class HolidayCalendarView(APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        year = request.query_params.get("year", date.today().year)
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = date.today().year

        holidays = HolidayCalendar.objects.filter(year=year)
        return Response(HolidayCalendarSerializer(holidays, many=True).data)