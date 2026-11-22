"""MMS HTTP layer: parse, scope, delegate, serialize.

Every view scopes through `selectors.scoping`, ensuring users only access
rows appropriate to their role and context.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.mms.api import serializers as s
from modules.mms.models import RegistrationWindow
from modules.mms.selectors import scoping
from modules.mms.services import (
    announcement as announcement_service,
)
from modules.mms.services import (
    billing as billing_service,
)
from modules.mms.services import (
    deregistration as dereg_service,
)
from modules.mms.services import (
    feedback as feedback_service,
)
from modules.mms.services import (
    menu as menu_service,
)
from modules.mms.services import (
    rebate as rebate_service,
)
from modules.mms.services import (
    registration as reg_service,
)
from modules.mms.services import (
    reports as reports_service,
)
from modules.mms.services import (
    roles as role_service,
)
from modules.mms.services import (
    special_food as sf_service,
)
from modules.mms.services import (
    survey as survey_service,
)

MODULE = HasModuleGrant("mms")


def _actor(request):
    return getattr(request, "principal", None)


# ---------------------------------------------------------------------------
# Special Food Requests
# ---------------------------------------------------------------------------


class SpecialFoodRequestListCreateView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.SpecialFoodRequestSerializer(many=True)})
    def get(self, request):
        actor = _actor(request)
        qs = scoping.special_food_requests_for(actor)
        return Response(s.SpecialFoodRequestSerializer(qs, many=True).data)

    @extend_schema(
        request=s.SpecialFoodRequestCreateSerializer,
        responses={201: s.SpecialFoodRequestSerializer},
    )
    def post(self, request):
        actor = _actor(request)
        ser = s.SpecialFoodRequestCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = sf_service.submit(
            actor=actor,
            reason=ser.validated_data["reason"],
            requested_date=ser.validated_data["requested_date"],
        )
        return Response(s.SpecialFoodRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class SpecialFoodRequestDetailView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.SpecialFoodRequestSerializer})
    def get(self, request, pk: int):
        actor = _actor(request)
        qs = scoping.special_food_request_for(actor, pk)
        req = qs.first()
        if not req:
            raise NotFoundError("Special food request not found.")
        return Response(s.SpecialFoodRequestSerializer(req).data)


class SpecialFoodDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("mms.special_food.review")]

    @extend_schema(
        request=s.SpecialFoodDecisionSerializer, responses={200: s.SpecialFoodRequestSerializer}
    )
    def post(self, request, pk: int):
        actor = _actor(request)
        ser = s.SpecialFoodDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = sf_service.decide(
            actor,
            pk,
            approve=ser.validated_data["approve"],
            note=ser.validated_data.get("note", ""),
        )
        return Response(s.SpecialFoodRequestSerializer(req).data)


class SpecialFoodFulfillView(APIView):
    permission_classes = [MODULE, HasPermission("mms.special_food.update")]

    @extend_schema(
        request=s.SpecialFoodFulfillSerializer, responses={200: s.SpecialFoodRequestSerializer}
    )
    def post(self, request, pk: int):
        actor = _actor(request)
        ser = s.SpecialFoodFulfillSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = sf_service.fulfill(
            actor,
            pk,
            to_status=ser.validated_data["status"],
            note=ser.validated_data.get("note", ""),
        )
        return Response(s.SpecialFoodRequestSerializer(req).data)


# ---------------------------------------------------------------------------
# Registration Requests
# ---------------------------------------------------------------------------


class RegistrationListCreateView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.RegistrationSerializer(many=True)})
    def get(self, request):
        actor = _actor(request)
        qs = scoping.registration_requests_for(actor)
        return Response(s.RegistrationSerializer(qs, many=True).data)

    @extend_schema(request=None, responses={201: s.RegistrationSerializer})
    def post(self, request):
        actor = _actor(request)
        reg = reg_service.submit(actor=actor)
        return Response(s.RegistrationSerializer(reg).data, status=status.HTTP_201_CREATED)


class RegistrationDetailView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.RegistrationSerializer})
    def get(self, request, pk: int):
        actor = _actor(request)
        qs = scoping.registration_requests_for(actor).filter(pk=pk)
        reg = qs.first()
        if not reg:
            raise NotFoundError("Registration request not found.")
        return Response(s.RegistrationSerializer(reg).data)


class RegistrationDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("mms.registration.review")]

    @extend_schema(
        request=s.RegistrationDecisionSerializer, responses={200: s.RegistrationSerializer}
    )
    def post(self, request, pk: int):
        actor = _actor(request)
        ser = s.RegistrationDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reg = reg_service.decide(
            actor,
            pk,
            approve=ser.validated_data["approve"],
            reason=ser.validated_data.get("reason", ""),
        )
        return Response(s.RegistrationSerializer(reg).data)


class RegistrationWindowView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.RegistrationWindowSerializer(many=True)})
    def get(self, request):
        windows = RegistrationWindow.objects.all().order_by("-opens_at")
        return Response(s.RegistrationWindowSerializer(windows, many=True).data)

    @extend_schema(
        request=s.RegistrationWindowCreateSerializer,
        responses={201: s.RegistrationWindowSerializer},
    )
    def post(self, request):
        actor = _actor(request)
        ser = s.RegistrationWindowCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        win = reg_service.open_window(
            actor=actor,
            cycle_or_period=ser.validated_data["cycle_or_period"],
            opens_at=ser.validated_data["opens_at"],
            closes_at=ser.validated_data["closes_at"],
        )
        return Response(s.RegistrationWindowSerializer(win).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Deregistration Requests
# ---------------------------------------------------------------------------


class DeregistrationListCreateView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.DeregistrationSerializer(many=True)})
    def get(self, request):
        actor = _actor(request)
        qs = scoping.deregistration_requests_for(actor)
        return Response(s.DeregistrationSerializer(qs, many=True).data)

    @extend_schema(request=None, responses={201: s.DeregistrationSerializer})
    def post(self, request):
        actor = _actor(request)
        dereg = dereg_service.submit(actor=actor)
        return Response(s.DeregistrationSerializer(dereg).data, status=status.HTTP_201_CREATED)


class DeregistrationDetailView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.DeregistrationSerializer})
    def get(self, request, pk: int):
        actor = _actor(request)
        qs = scoping.deregistration_requests_for(actor).filter(pk=pk)
        dereg = qs.first()
        if not dereg:
            raise NotFoundError("Deregistration request not found.")
        return Response(s.DeregistrationSerializer(dereg).data)


class DeregistrationDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("mms.deregistration.review")]

    @extend_schema(
        request=s.DeregistrationDecisionSerializer, responses={200: s.DeregistrationSerializer}
    )
    def post(self, request, pk: int):
        actor = _actor(request)
        ser = s.DeregistrationDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        dereg = dereg_service.decide(
            actor,
            pk,
            approve=ser.validated_data["approve"],
            reason=ser.validated_data.get("reason", ""),
        )
        return Response(s.DeregistrationSerializer(dereg).data)


# ---------------------------------------------------------------------------
# Rebate Requests
# ---------------------------------------------------------------------------


class RebateRequestListCreateView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.RebateRequestSerializer(many=True)})
    def get(self, request):
        actor = _actor(request)
        qs = scoping.rebate_requests_for(actor)
        return Response(s.RebateRequestSerializer(qs, many=True).data)

    @extend_schema(
        request=s.RebateRequestCreateSerializer, responses={201: s.RebateRequestSerializer}
    )
    def post(self, request):
        actor = _actor(request)
        ser = s.RebateRequestCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rebate = rebate_service.submit(
            actor=actor,
            reason=ser.validated_data["reason"],
            explanation=ser.validated_data.get("explanation", ""),
            start_date=ser.validated_data["start_date"],
            end_date=ser.validated_data["end_date"],
        )
        return Response(s.RebateRequestSerializer(rebate).data, status=status.HTTP_201_CREATED)


class RebateRequestDetailView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.RebateRequestSerializer})
    def get(self, request, pk: int):
        actor = _actor(request)
        qs = scoping.rebate_requests_for(actor).filter(pk=pk)
        rebate = qs.first()
        if not rebate:
            raise NotFoundError("Rebate request not found.")
        return Response(s.RebateRequestSerializer(rebate).data)


class RebateDecisionView(APIView):
    permission_classes = [MODULE, HasPermission("mms.rebate.review")]

    @extend_schema(request=s.RebateDecisionSerializer, responses={200: s.RebateRequestSerializer})
    def post(self, request, pk: int):
        actor = _actor(request)
        ser = s.RebateDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rebate = rebate_service.decide(
            actor,
            pk,
            approve=ser.validated_data["approve"],
            approved_start_date=ser.validated_data.get("approved_start_date"),
            approved_end_date=ser.validated_data.get("approved_end_date"),
            reason=ser.validated_data.get("reason", ""),
        )
        return Response(s.RebateRequestSerializer(rebate).data)


# ---------------------------------------------------------------------------
# Weekly Menu
# ---------------------------------------------------------------------------


class MenuListView(APIView):
    permission_classes = [MODULE, HasPermission("mms.menu.view")]

    @extend_schema(responses={200: s.MenuItemSerializer(many=True)})
    def get(self, request):
        actor = _actor(request)
        qs = scoping.menu_items_for(actor)
        return Response(s.MenuItemSerializer(qs, many=True).data)


class MenuItemManageView(APIView):
    permission_classes = [MODULE, HasPermission("mms.menu.manage")]

    @extend_schema(request=s.MenuItemCreateSerializer, responses={201: s.MenuItemSerializer})
    def post(self, request):
        actor = _actor(request)
        ser = s.MenuItemCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        item = menu_service.upsert_item(
            actor,
            day=ser.validated_data["day"],
            meal=ser.validated_data["meal"],
            item=ser.validated_data["item"],
        )
        return Response(s.MenuItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses={204: None})
    def delete(self, request):
        actor = _actor(request)
        item_id = request.query_params.get("id")
        if not item_id:
            raise BadRequestError("id query parameter is required.")
        menu_service.delete_item(actor, pk=int(item_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Monthly Billing
# ---------------------------------------------------------------------------


class MonthlyBillListView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.MonthlyBillSerializer(many=True)})
    def get(self, request):
        actor = _actor(request)
        qs = scoping.monthly_bills_for(actor)
        return Response(s.MonthlyBillSerializer(qs, many=True).data)


class MonthlyBillDetailView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.MonthlyBillSerializer})
    def get(self, request, pk: int):
        actor = _actor(request)
        qs = scoping.monthly_bills_for(actor).filter(pk=pk)
        bill = qs.first()
        if not bill:
            raise NotFoundError("Bill not found.")
        return Response(s.MonthlyBillSerializer(bill).data)


class MonthlyBillGenerateView(APIView):
    permission_classes = [MODULE, HasPermission("mms.billing.manage")]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        count = billing_service.generate_monthly()
        return Response({"generated_count": count})


class MonthlyBillFinalizeView(APIView):
    permission_classes = [MODULE, HasPermission("mms.billing.approve")]

    @extend_schema(request=None, responses={200: s.MonthlyBillSerializer})
    def post(self, request, pk: int):
        actor = _actor(request)
        bill = billing_service.finalize(actor, pk)
        return Response(s.MonthlyBillSerializer(bill).data)


class MonthlyBillPublishView(APIView):
    permission_classes = [MODULE, HasPermission("mms.billing.publish")]

    @extend_schema(request=None, responses={200: s.MonthlyBillSerializer})
    def post(self, request, pk: int):
        actor = _actor(request)
        bill = billing_service.publish(actor, pk)
        return Response(s.MonthlyBillSerializer(bill).data)


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


class FeedbackListCreateView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.FeedbackSerializer(many=True)})
    def get(self, request):
        actor = _actor(request)
        qs = scoping.feedback_for(actor)
        return Response(s.FeedbackSerializer(qs, many=True).data)

    @extend_schema(request=s.FeedbackCreateSerializer, responses={201: s.FeedbackSerializer})
    def post(self, request):
        actor = _actor(request)
        ser = s.FeedbackCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        fb = feedback_service.submit(actor=actor, text=ser.validated_data["text"])
        return Response(s.FeedbackSerializer(fb).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Vacation Surveys & Responses
# ---------------------------------------------------------------------------


class VacationSurveyListCreateView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.VacationSurveySerializer(many=True)})
    def get(self, request):
        actor = _actor(request)
        qs = scoping.vacation_surveys_for(actor)
        return Response(s.VacationSurveySerializer(qs, many=True).data)

    @extend_schema(
        request=s.VacationSurveyCreateSerializer, responses={201: s.VacationSurveySerializer}
    )
    def post(self, request):
        actor = _actor(request)
        ser = s.VacationSurveyCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        survey = survey_service.create(
            actor=actor,
            vacation=ser.validated_data["vacation"],
            response_deadline=ser.validated_data["response_deadline"],
        )
        return Response(s.VacationSurveySerializer(survey).data, status=status.HTTP_201_CREATED)


class VacationResponseCreateView(APIView):
    permission_classes = [MODULE, HasPermission("mms.survey_response.create")]

    @extend_schema(
        request=s.VacationResponseCreateSerializer, responses={201: s.VacationResponseSerializer}
    )
    def post(self, request, survey_id: int):
        actor = _actor(request)
        ser = s.VacationResponseCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        resp = survey_service.respond(
            actor,
            survey_id,
            response=ser.validated_data["response"],
        )
        return Response(s.VacationResponseSerializer(resp).data, status=status.HTTP_201_CREATED)


class VacationSurveySummaryView(APIView):
    permission_classes = [MODULE, HasPermission("mms.survey.view_summary")]

    @extend_schema(responses={200: dict})
    def get(self, request):
        from modules.mms.models import VacationResponse, VacationSurvey

        surveys = VacationSurvey.objects.all().order_by("-created_at")
        summaries = []
        for srv in surveys:
            yes = VacationResponse.objects.filter(survey=srv.pk, response="yes").count()
            no = VacationResponse.objects.filter(survey=srv.pk, response="no").count()
            default_no = VacationResponse.objects.filter(
                survey=srv.pk, response="default_no"
            ).count()
            summaries.append(
                {
                    "survey_id": srv.pk,
                    "vacation": srv.vacation,
                    "response_deadline": srv.response_deadline,
                    "is_open": srv.is_open,
                    "yes": yes,
                    "no": no,
                    "default_no": default_no,
                    "total": yes + no + default_no,
                }
            )
        return Response(summaries)


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------


class AnnouncementListCreateView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses={200: s.AnnouncementSerializer(many=True)})
    def get(self, request):
        actor = _actor(request)
        qs = scoping.announcements_for(actor)
        return Response(s.AnnouncementSerializer(qs, many=True).data)

    @extend_schema(
        request=s.AnnouncementCreateSerializer, responses={201: s.AnnouncementSerializer}
    )
    def post(self, request):
        actor = _actor(request)
        ser = s.AnnouncementCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ann = announcement_service.publish(
            actor=actor,
            title=ser.validated_data["title"],
            body=ser.validated_data["body"],
        )
        return Response(s.AnnouncementSerializer(ann).data, status=status.HTTP_201_CREATED)


class AnnouncementHistoryView(APIView):
    permission_classes = [MODULE, HasPermission("mms.announcement.view")]

    @extend_schema(responses={200: s.AnnouncementSerializer(many=True)})
    def get(self, request):
        from modules.mms.models import Announcement

        announcements = Announcement.objects.all().order_by("-published_at")
        return Response(s.AnnouncementSerializer(announcements, many=True).data)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class OperationalReportView(APIView):
    permission_classes = [MODULE, HasPermission("mms.report.operational")]

    @extend_schema(responses={200: s.OperationalReportSerializer})
    def get(self, request):
        actor = _actor(request)
        data = reports_service.get_operational_report(actor)
        return Response(s.OperationalReportSerializer(data).data)


class SupervisoryReportView(APIView):
    permission_classes = [MODULE, HasPermission("mms.report.supervisory")]

    @extend_schema(responses={200: s.SupervisoryReportSerializer})
    def get(self, request):
        actor = _actor(request)
        data = reports_service.get_supervisory_report(actor)
        return Response(s.SupervisoryReportSerializer(data).data)


# ---------------------------------------------------------------------------
# Role Assignments (Mess Admin)
# ---------------------------------------------------------------------------


class RoleAssignmentListCreateView(APIView):
    permission_classes = [MODULE, HasPermission("mms.role.assign")]

    @extend_schema(responses={200: s.RoleAssignmentSerializer(many=True)})
    def get(self, request):
        assignments = role_service.current_assignments()
        return Response(s.RoleAssignmentSerializer(assignments, many=True).data)

    @extend_schema(
        request=s.RoleAssignmentCreateSerializer, responses={201: s.RoleAssignmentSerializer}
    )
    def post(self, request):
        actor = _actor(request)
        ser = s.RoleAssignmentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        assignment = role_service.assign(
            actor=actor,
            designation=ser.validated_data["designation"],
            employee_user_id=ser.validated_data["employee_user_id"],
            effective_from=ser.validated_data["effective_from"],
            effective_until=ser.validated_data.get("effective_until"),
        )
        return Response(s.RoleAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Unified Student Requests Overview
# ---------------------------------------------------------------------------


class StudentRequestsOverviewView(APIView):
    permission_classes = [MODULE, HasPermission("mms.request.view_self")]

    @extend_schema(responses={200: dict})
    def get(self, request):
        actor = _actor(request)
        regs = scoping.registration_requests_for(actor)
        deregs = scoping.deregistration_requests_for(actor)
        rebates = scoping.rebate_requests_for(actor)
        sf_reqs = scoping.special_food_requests_for(actor)

        return Response(
            {
                "registrations": s.RegistrationSerializer(regs, many=True).data,
                "deregistrations": s.DeregistrationSerializer(deregs, many=True).data,
                "rebates": s.RebateRequestSerializer(rebates, many=True).data,
                "special_food": s.SpecialFoodRequestSerializer(sf_reqs, many=True).data,
            }
        )
