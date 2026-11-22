"""Role-gated MMS endpoints; self-service actors never choose their user ID."""

from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.mms.api import serializers as s
from modules.mms.models import (
    Announcement,
    Feedback,
    MenuItem,
    RebateRequest,
    RegistrationWindow,
    RoleAssignment,
    SpecialFoodRequest,
    StudentRegistration,
    VacationResponse,
    VacationSurvey,
)
from modules.mms.selectors.roles import is_active_holder
from modules.mms.services import workflows

MODULE = HasModuleGrant("mms")


def actor_id(request) -> int:
    return request.principal.user_id


def _caretaker_active(user_id: int) -> bool:
    return is_active_holder(role="caretaker", user_id=user_id)


def _warden_active(user_id: int) -> bool:
    return is_active_holder(role="warden", user_id=user_id)


def _require_caretaker(request) -> None:
    if not _caretaker_active(actor_id(request)):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("Only the active Mess Caretaker may perform this operation.")


def _require_operational_reader(request) -> None:
    if not (_caretaker_active(actor_id(request)) or _warden_active(actor_id(request))):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied(
            "Only the active Mess Caretaker or Warden may view operational records."
        )


class RoleAssignmentsView(GenericAPIView):
    serializer_class = s.RoleAssignmentSerializer
    permission_classes = [MODULE, HasPermission("mms.role.assign")]

    def get(self, request):
        rows = RoleAssignment.objects.order_by("role", "-starts_at")
        return Response(s.RoleAssignmentSerializer(rows, many=True).data)

    def post(self, request):
        role = request.data.get("role")
        if role not in {"caretaker", "warden"}:
            raise BadRequestError("Role must be caretaker or warden.", code="invalid_role")
        payload = s.RoleAssignmentInputSerializer(
            data={
                "role": role,
                "user_id": request.data.get("user_id"),
                "ends_at": request.data.get("ends_at"),
            }
        )
        payload.is_valid(raise_exception=True)
        from modules.directory.contracts import get_users

        employee = get_users([payload.validated_data["user_id"]]).get(
            payload.validated_data["user_id"]
        )
        if employee is None or employee.kind not in {"faculty", "staff"}:
            raise BadRequestError(
                "Role assignments require an active institute employee.", code="employee_not_found"
            )
        row = workflows.assign_role(
            role=role,
            user_id=payload.validated_data["user_id"],
            actor_id=actor_id(request),
            ends_at=payload.validated_data["ends_at"],
        )
        return Response(s.RoleAssignmentSerializer(row).data, status=status.HTTP_201_CREATED)


class RegistrationWindowsView(GenericAPIView):
    serializer_class = s.WindowSerializer
    permission_classes = [MODULE, HasPermission("mms.registration.decide")]

    def get(self, request):
        _require_caretaker(request)
        return Response(
            s.WindowSerializer(RegistrationWindow.objects.order_by("-opens_at"), many=True).data
        )

    def post(self, request):
        _require_caretaker(request)
        payload = s.WindowSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = payload.save(created_by_user_id=actor_id(request))
        return Response(s.WindowSerializer(row).data, status=status.HTTP_201_CREATED)


class RegistrationsView(GenericAPIView):
    serializer_class = s.RegistrationSerializer
    permission_classes = [MODULE, HasPermission("mms.registration.self", "mms.registration.view")]

    def get(self, request):
        principal = request.principal
        if principal.has_any_permission("mms.registration.view"):
            _require_operational_reader(request)
        qs = StudentRegistration.objects.order_by("-submitted_at")
        if principal.has_any_permission(
            "mms.registration.self"
        ) and not principal.has_any_permission("mms.registration.view"):
            qs = qs.filter(user_id=actor_id(request))
        return Response(s.RegistrationSerializer(qs, many=True).data)

    def post(self, request):
        if not request.principal.has_any_permission("mms.registration.self"):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()
        payload = request.data
        request_type = payload.get("request_type")
        cycle = payload.get("cycle")
        if (
            request_type not in {"register", "deregister"}
            or not isinstance(cycle, str)
            or not cycle.strip()
        ):
            raise BadRequestError(
                "A cycle and valid request_type are required.", code="invalid_registration"
            )
        user_id = actor_id(request)
        if request_type == "register":
            now = timezone.now()
            if not RegistrationWindow.objects.filter(
                cycle=cycle, opens_at__lte=now, closes_at__gte=now
            ).exists():
                raise BadRequestError(
                    "Registration is only available during an open window.",
                    code="registration_closed",
                )
            if StudentRegistration.objects.filter(
                user_id=user_id,
                cycle=cycle,
                status__in=[
                    StudentRegistration.Status.PENDING,
                    StudentRegistration.Status.REGISTERED,
                ],
            ).exists():
                raise BadRequestError(
                    "An active registration request already exists for this cycle.",
                    code="duplicate_registration",
                )
        else:
            if not StudentRegistration.objects.filter(
                user_id=user_id,
                cycle=cycle,
                request_type="register",
                status=StudentRegistration.Status.REGISTERED,
            ).exists():
                raise BadRequestError(
                    "Only a registered student may request deregistration.", code="not_registered"
                )
            if StudentRegistration.objects.filter(
                user_id=user_id,
                cycle=cycle,
                request_type="deregister",
                status=StudentRegistration.Status.PENDING,
            ).exists():
                raise BadRequestError(
                    "A deregistration request is already pending.", code="duplicate_deregistration"
                )
        row = StudentRegistration.objects.create(
            user_id=user_id, cycle=cycle, request_type=request_type
        )
        return Response(s.RegistrationSerializer(row).data, status=status.HTTP_201_CREATED)


class RegistrationDecisionView(GenericAPIView):
    serializer_class = s.RegistrationSerializer
    permission_classes = [MODULE, HasPermission("mms.registration.decide")]

    def post(self, request, request_id: int):
        _require_caretaker(request)
        decision = request.data.get("decision")
        if decision not in {"approve", "reject"}:
            raise BadRequestError("Decision must be approve or reject.", code="invalid_decision")
        row = workflows.decide_registration(
            request_id=request_id, actor_id=actor_id(request), approve=decision == "approve"
        )
        return Response(s.RegistrationSerializer(row).data)


class MenuView(GenericAPIView):
    serializer_class = s.MenuItemSerializer
    permission_classes = [MODULE, HasPermission("mms.menu.view", "mms.menu.manage")]

    def get(self, request):
        if not request.principal.has_any_permission("mms.registration.self"):
            _require_operational_reader(request)
        rows = MenuItem.objects.order_by("week_start", "day", "meal", "item")
        return Response(s.MenuItemSerializer(rows, many=True).data)

    def post(self, request):
        _require_caretaker(request)
        if not request.principal.has_any_permission("mms.menu.manage"):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()
        payload = s.MenuItemSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = payload.save(updated_by_user_id=actor_id(request))
        return Response(s.MenuItemSerializer(row).data, status=status.HTTP_201_CREATED)


class RebateView(GenericAPIView):
    serializer_class = s.RebateSerializer
    permission_classes = [MODULE, HasPermission("mms.rebate.self", "mms.rebate.view")]

    def get(self, request):
        if request.principal.has_any_permission("mms.rebate.view"):
            _require_operational_reader(request)
        qs = RebateRequest.objects.order_by("-submitted_at")
        if request.principal.has_any_permission(
            "mms.rebate.self"
        ) and not request.principal.has_any_permission("mms.rebate.view"):
            qs = qs.filter(user_id=actor_id(request))
        return Response(s.RebateSerializer(qs, many=True).data)

    def post(self, request):
        if not request.principal.has_any_permission("mms.rebate.self"):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()
        payload = s.RebateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        row = workflows.submit_rebate(
            actor_id=actor_id(request),
            reason=data["reason"],
            explanation=data.get("explanation", ""),
            start_date=data["start_date"],
            end_date=data["end_date"],
        )
        return Response(s.RebateSerializer(row).data, status=status.HTTP_201_CREATED)


class RebateDecisionView(GenericAPIView):
    serializer_class = s.RebateSerializer
    permission_classes = [MODULE, HasPermission("mms.rebate.decide")]

    def post(self, request, request_id: int):
        _require_caretaker(request)
        decision = request.data.get("decision")
        if decision not in {"approve", "reject"}:
            raise BadRequestError("Decision must be approve or reject.", code="invalid_decision")
        row = workflows.decide_rebate(
            request_id=request_id, actor_id=actor_id(request), approve=decision == "approve"
        )
        return Response(s.RebateSerializer(row).data)


class VacationSurveysView(GenericAPIView):
    serializer_class = s.VacationSurveySerializer
    permission_classes = [MODULE, HasPermission("mms.vacation.manage", "mms.vacation.view")]

    def get(self, request):
        if request.principal.has_any_permission("mms.vacation.view"):
            _require_operational_reader(request)
        rows = VacationSurvey.objects.order_by("-created_at")
        if request.principal.has_any_permission("mms.vacation.view"):
            return Response(
                [
                    {
                        "survey": s.VacationSurveySerializer(row).data,
                        "responses": list(
                            row.responses.values("response", "defaulted").annotate(
                                count=Count("id")
                            )
                        ),
                    }
                    for row in rows
                ]
            )
        own = VacationResponse.objects.filter(
            survey__in=rows, user_id=actor_id(request)
        ).select_related("survey")
        return Response(
            [
                {
                    "survey": s.VacationSurveySerializer(row.survey).data,
                    "response": row.response,
                    "responded_at": row.responded_at,
                    "defaulted": row.defaulted,
                }
                for row in own
            ]
        )

    def post(self, request):
        _require_caretaker(request)
        if not request.principal.has_any_permission("mms.vacation.manage"):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()
        payload = s.VacationSurveySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        if (
            data["vacation_end"] < data["vacation_start"]
            or data["response_deadline"] <= timezone.now()
        ):
            raise BadRequestError(
                "Vacation dates or response deadline are invalid.", code="invalid_survey"
            )
        with transaction.atomic():
            survey = payload.save(created_by_user_id=actor_id(request))
            active = (
                StudentRegistration.objects.filter(
                    Q(status=StudentRegistration.Status.REGISTERED)
                    | Q(
                        status=StudentRegistration.Status.DEREGISTERED,
                        effective_date__gt=timezone.localdate(),
                    ),
                )
                .values_list("user_id", flat=True)
                .distinct()
            )
            VacationResponse.objects.bulk_create(
                [VacationResponse(survey=survey, user_id=user_id) for user_id in active]
            )
        return Response(s.VacationSurveySerializer(survey).data, status=status.HTTP_201_CREATED)


class VacationResponseView(GenericAPIView):
    serializer_class = s.VacationResponseSerializer
    permission_classes = [MODULE, HasPermission("mms.vacation.self")]

    def post(self, request, survey_id: int):
        response = request.data.get("response")
        if response not in {"yes", "no"}:
            raise BadRequestError("Response must be yes or no.", code="invalid_response")
        row = workflows.respond_to_survey(
            survey_id=survey_id, actor_id=actor_id(request), response=response
        )
        return Response(s.VacationResponseSerializer(row).data)


class SpecialFoodView(GenericAPIView):
    serializer_class = s.SpecialFoodSerializer
    permission_classes = [MODULE, HasPermission("mms.special_food.self", "mms.special_food.view")]

    def get(self, request):
        if request.principal.has_any_permission("mms.special_food.view"):
            _require_operational_reader(request)
        qs = SpecialFoodRequest.objects.order_by("-submitted_at")
        if request.principal.has_any_permission(
            "mms.special_food.self"
        ) and not request.principal.has_any_permission("mms.special_food.view"):
            qs = qs.filter(user_id=actor_id(request))
        return Response(s.SpecialFoodSerializer(qs, many=True).data)

    def post(self, request):
        if not request.principal.has_any_permission("mms.special_food.self"):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()
        payload = s.SpecialFoodSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        if data["requested_date"] < timezone.localdate() + timedelta(days=1):
            raise BadRequestError(
                "Special food must be requested at least one calendar day ahead.",
                code="special_food_lead_time",
            )
        row = SpecialFoodRequest.objects.create(
            user_id=actor_id(request),
            requested_date=data["requested_date"],
            description=data["description"],
            charge=data.get("charge"),
        )
        return Response(s.SpecialFoodSerializer(row).data, status=status.HTTP_201_CREATED)


class SpecialFoodDecisionView(GenericAPIView):
    serializer_class = s.SpecialFoodSerializer
    permission_classes = [MODULE, HasPermission("mms.special_food.decide")]

    def post(self, request, request_id: int):
        _require_caretaker(request)
        decision = request.data.get("decision")
        if decision not in {"approve", "reject"}:
            raise BadRequestError("Decision must be approve or reject.", code="invalid_decision")
        row = workflows.decide_special_food(
            request_id=request_id, actor_id=actor_id(request), approve=decision == "approve"
        )
        return Response(s.SpecialFoodSerializer(row).data)


class SpecialFoodFulfillmentView(GenericAPIView):
    serializer_class = s.SpecialFoodSerializer
    permission_classes = [MODULE, HasPermission("mms.special_food.decide")]

    def post(self, request, request_id: int):
        _require_caretaker(request)
        outcome = request.data.get("status")
        if outcome not in {"served", "cancelled"}:
            raise BadRequestError(
                "Fulfillment status must be served or cancelled.", code="invalid_fulfillment"
            )
        row = workflows.update_special_fulfillment(request_id=request_id, outcome=outcome)
        return Response(s.SpecialFoodSerializer(row).data)


class FeedbackView(GenericAPIView):
    serializer_class = s.FeedbackSerializer
    permission_classes = [MODULE, HasPermission("mms.feedback.self", "mms.feedback.view")]

    def get(self, request):
        rows = Feedback.objects.order_by("-created_at")
        if not request.principal.has_any_permission("mms.feedback.view"):
            rows = rows.filter(user_id=actor_id(request))
        else:
            _require_operational_reader(request)
        return Response(s.FeedbackSerializer(rows, many=True).data)

    def post(self, request):
        if not request.principal.has_any_permission("mms.feedback.self"):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()
        payload = s.FeedbackSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = payload.save(user_id=actor_id(request))
        return Response(s.FeedbackSerializer(row).data, status=status.HTTP_201_CREATED)


class AnnouncementsView(GenericAPIView):
    serializer_class = s.AnnouncementSerializer
    permission_classes = [
        MODULE,
        HasPermission("mms.announcement.view", "mms.announcement.publish"),
    ]

    def get(self, request):
        if request.principal.has_any_permission("mms.announcement.publish"):
            _require_operational_reader(request)
        return Response(
            s.AnnouncementSerializer(Announcement.objects.order_by("-created_at"), many=True).data
        )

    def post(self, request):
        user_id = actor_id(request)
        if not request.principal.has_any_permission("mms.announcement.publish"):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()
        if not (_caretaker_active(user_id) or _warden_active(user_id)):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only the active Caretaker or Warden may publish announcements.")
        payload = s.AnnouncementSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        owner = (
            "warden" if _warden_active(user_id) and not _caretaker_active(user_id) else "caretaker"
        )
        row = payload.save(owner_role=owner, created_by_user_id=user_id)
        return Response(s.AnnouncementSerializer(row).data, status=status.HTTP_201_CREATED)


class ReportsView(GenericAPIView):
    serializer_class = s.ReportSummarySerializer
    permission_classes = [MODULE, HasPermission("mms.report.view")]

    def get(self, request):
        _require_operational_reader(request)
        return Response(
            {
                "registrations": list(
                    StudentRegistration.objects.values("cycle", "status").annotate(
                        count=Count("id")
                    )
                ),
                "rebates": list(RebateRequest.objects.values("status").annotate(count=Count("id"))),
                "special_food": list(
                    SpecialFoodRequest.objects.values("status").annotate(count=Count("id"))
                ),
            }
        )
