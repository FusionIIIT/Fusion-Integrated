from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.mms.api import serializers as s
from modules.mms.models import (
    Announcement,
    BillingInput,
    Enrollment,
    Feedback,
    MenuWeek,
    MonthlyBill,
    RebateRequest,
    RegistrationWindow,
    RoleAssignment,
    SpecialFoodRequest,
    StudentRequest,
    VacationResponse,
    VacationSurvey,
)
from modules.mms.selectors import operational as selectors
from modules.mms.services import operations, roles

MODULE = HasModuleGrant("mess_management")
P_STUDENT = "mess_management.student.use"
P_OPS = "mess_management.operations.view"
P_MANAGE = "mess_management.operations.manage"
P_REVIEW = "mess_management.requests.review"
P_MENU = "mess_management.menu.manage"
P_BILL = "mess_management.billing.manage"
P_FEEDBACK = "mess_management.feedback.view"
P_SURVEY = "mess_management.surveys.manage"
P_ANNOUNCE = "mess_management.announcements.publish"
P_WARDEN_REPORT = "mess_management.reports.warden"
P_CARE_REPORT = "mess_management.reports.caretaker"
P_ROLES = "mess_management.roles.manage"


def _actor(request):
    return request.principal


def _require_active_operator(actor):
    if not (roles.is_active_role(actor.user_id, "caretaker")
            or roles.is_active_role(actor.user_id, "warden")):
        from core.api.exceptions import PermissionDeniedError

        raise PermissionDeniedError(
            "An active Mess Caretaker or Warden assignment is required.",
            code="active_role_required")


def _datetime(data, name):
    raw = data.get(name, "")
    value = parse_datetime(raw) if isinstance(raw, str) else None
    if value is None:
        raise BadRequestError(f"{name} must be an ISO 8601 date and time.",
                              code="invalid_datetime")
    return timezone.make_aware(value) if timezone.is_naive(value) else value


def _date(data, name):
    raw = data.get(name, "")
    value = parse_date(raw) if isinstance(raw, str) else None
    if value is None:
        raise BadRequestError(f"{name} must be an ISO 8601 date.",
                              code="invalid_date")
    return value


class RoleAssignmentsView(APIView):
    permission_classes = [MODULE, HasPermission(P_ROLES)]

    def get(self, request):
        rows = RoleAssignment.objects.order_by("-starts_at")
        people = directory.get_users(list(rows.values_list("user_id", flat=True)))
        active = roles.current_assignments()
        return Response({
            "current": [{
                **s.RoleAssignmentSerializer(row).data,
                "employee": (people[row.user_id].__dict__ if row.user_id in people else None),
            } for row in active.values() if row is not None],
            "history": s.RoleAssignmentSerializer(rows, many=True).data,
            "employees": [person.__dict__ for person in directory.get_employees()],
        })

    def post(self, request):
        role = request.data.get("role")
        try:
            row = roles.assign(
                actor=_actor(request), role=role,
                user_id=int(request.data.get("user_id")),
                ends_at=_datetime(request.data, "ends_at"))
        except (TypeError, ValueError) as exc:
            raise BadRequestError("user_id must be an integer.", code="invalid_user_id") from exc
        return Response(s.RoleAssignmentSerializer(row).data, status=status.HTTP_201_CREATED)


class RegistrationWindowsView(APIView):
    permission_classes = [MODULE]

    def get_permissions(self):
        codes = (P_OPS, P_STUDENT) if self.request.method == "GET" else (P_MANAGE,)
        return [MODULE(), HasPermission(*codes)()]

    def get(self, request):
        actor = _actor(request)
        if not actor.has_permission(P_STUDENT):
            _require_active_operator(actor)
        return Response({"results": s.RegistrationWindowSerializer(
            RegistrationWindow.objects.order_by("-opens_at"), many=True).data})

    def post(self, request):
        row = operations.open_registration_window(
            actor=_actor(request), cycle=str(request.data.get("cycle", "")),
            opens_at=_datetime(request.data, "opens_at"),
            closes_at=_datetime(request.data, "closes_at"))
        return Response(s.RegistrationWindowSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class StudentRequestsView(APIView):
    permission_classes = [MODULE]

    def get_permissions(self):
        codes = (P_STUDENT, P_OPS) if self.request.method == "GET" else (P_STUDENT,)
        return [MODULE(), HasPermission(*codes)()]

    def get(self, request):
        actor = _actor(request)
        if actor.has_permission(P_STUDENT):
            rows = selectors.student_requests(actor.user_id)
        else:
            _require_active_operator(actor)
            rows = selectors.oversight_requests()["registration"]
        return Response({"results": s.StudentRequestSerializer(rows, many=True).data})

    def post(self, request):
        actor = _actor(request)
        kind = request.data.get("kind")
        if kind == "registration":
            try:
                window_id = int(request.data.get("window_id", 0))
            except (TypeError, ValueError) as exc:
                raise BadRequestError("window_id must be an integer.",
                                      code="invalid_window_id") from exc
            row = operations.request_registration(
                actor=actor, window_id=window_id)
        elif kind == "deregistration":
            row = operations.request_deregistration(actor=actor)
        else:
            raise BadRequestError("kind must be registration or deregistration.",
                                  code="invalid_request_kind")
        return Response(s.StudentRequestSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class StudentStatusView(APIView):
    permission_classes = [MODULE, HasPermission(P_STUDENT)]

    def get(self, request):
        enrollment = Enrollment.objects.filter(
            user_id=_actor(request).user_id).first()
        return Response({
            "registered": bool(enrollment and enrollment.deregistered_at is None),
            "registered_at": enrollment.registered_at if enrollment else None,
            "deregistered_at": enrollment.deregistered_at if enrollment else None,
        })


class StudentRequestDecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    def post(self, request, request_id):
        if not isinstance(request.data.get("approve"), bool):
            raise BadRequestError("approve must be true or false.", code="invalid_decision")
        row = operations.decide_student_request(
            actor=_actor(request), request_id=request_id,
            approve=request.data["approve"])
        return Response(s.StudentRequestSerializer(row).data)


class MenuView(APIView):
    permission_classes = [MODULE]

    def get_permissions(self):
        codes = (P_STUDENT, P_OPS) if self.request.method == "GET" else (P_MENU,)
        return [MODULE(), HasPermission(*codes)()]

    def get(self, request):
        actor = _actor(request)
        if not actor.has_permission(P_STUDENT):
            _require_active_operator(actor)
        weeks = MenuWeek.objects.prefetch_related("entries").order_by("-week_start")
        return Response({"results": s.MenuWeekSerializer(weeks, many=True).data})

    def post(self, request):
        entries = request.data.get("entries")
        if not isinstance(entries, list) or any(
                not isinstance(entry, dict)
                or not isinstance(entry.get("item"), str)
                for entry in entries):
            raise BadRequestError("entries must be a list.", code="invalid_menu")
        row = operations.publish_menu(
            actor=_actor(request), week_start=_date(request.data, "week_start"),
            entries=entries)
        return Response(s.MenuWeekSerializer(row).data, status=status.HTTP_201_CREATED)


class RebatesView(APIView):
    permission_classes = [MODULE]

    def get_permissions(self):
        codes = (
            (P_STUDENT, P_OPS, P_WARDEN_REPORT)
            if self.request.method == "GET" else (P_STUDENT,)
        )
        return [MODULE(), HasPermission(*codes)()]

    def get(self, request):
        actor = _actor(request)
        if actor.has_permission(P_STUDENT):
            rows = RebateRequest.objects.filter(user_id=actor.user_id)
        else:
            _require_active_operator(actor)
            rows = RebateRequest.objects.all()
        rows = rows.prefetch_related("history")
        return Response({"results": s.RebateSerializer(rows.order_by("-created_at"),
                                                       many=True).data})

    def post(self, request):
        row = operations.submit_rebate(
            actor=_actor(request), reason=request.data.get("reason", ""),
            explanation=request.data.get("explanation", ""),
            starts_on=_date(request.data, "starts_on"),
            ends_on=_date(request.data, "ends_on"))
        return Response(s.RebateSerializer(row).data, status=status.HTTP_201_CREATED)


class RebateDecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    def post(self, request, request_id):
        if not isinstance(request.data.get("approve"), bool):
            raise BadRequestError("approve must be true or false.", code="invalid_decision")
        has_start = bool(request.data.get("starts_on"))
        has_end = bool(request.data.get("ends_on"))
        if has_start != has_end:
            raise BadRequestError("Both rebate dates are required when modifying dates.",
                                  code="invalid_rebate_dates")
        starts_on = ends_on = None
        if has_start:
            starts_on = _date(request.data, "starts_on")
            ends_on = _date(request.data, "ends_on")
        row = operations.decide_rebate(
            actor=_actor(request), request_id=request_id,
            approve=request.data["approve"],
            starts_on=starts_on, ends_on=ends_on)
        return Response(s.RebateSerializer(row).data)


class VacationSurveysView(APIView):
    permission_classes = [MODULE]

    def get_permissions(self):
        codes = (
            (P_STUDENT, P_SURVEY, P_WARDEN_REPORT)
            if self.request.method == "GET" else (P_SURVEY,)
        )
        return [MODULE(), HasPermission(*codes)()]

    def get(self, request):
        actor = _actor(request)
        if actor.has_permission(P_STUDENT):
            if not Enrollment.objects.filter(
                    user_id=actor.user_id, deregistered_at__isnull=True).exists():
                return Response({"results": []})
            return Response({"results": s.VacationSurveySerializer(
                VacationSurvey.objects.filter(
                deadline__gt=timezone.now()),
                many=True).data})
        _require_active_operator(actor)
        return Response({"results": s.VacationSurveySerializer(
            VacationSurvey.objects.all(), many=True).data})

    def post(self, request):
        row = operations.create_vacation_survey(
            actor=_actor(request), title=request.data.get("title", ""),
            starts_on=_date(request.data, "vacation_starts_on"),
            ends_on=_date(request.data, "vacation_ends_on"),
            deadline=_datetime(request.data, "deadline"))
        return Response(s.VacationSurveySerializer(row).data,
                        status=status.HTTP_201_CREATED)


class VacationResponsesView(APIView):
    permission_classes = [MODULE]

    def get_permissions(self):
        codes = (
            (P_STUDENT, P_SURVEY, P_WARDEN_REPORT)
            if self.request.method == "GET" else (P_STUDENT,)
        )
        return [MODULE(), HasPermission(*codes)()]

    def get(self, request, survey_id):
        actor = _actor(request)
        if actor.has_permission(P_STUDENT):
            if not Enrollment.objects.filter(
                    user_id=actor.user_id, deregistered_at__isnull=True).exists():
                from core.api.exceptions import PermissionDeniedError
                raise PermissionDeniedError(
                    "Vacation surveys are available to currently registered students only.")
            rows = VacationResponse.objects.filter(survey_id=survey_id,
                                                    user_id=actor.user_id)
        else:
            _require_active_operator(actor)
            rows = VacationResponse.objects.filter(survey_id=survey_id)
        return Response({"results": s.VacationResponseSerializer(rows, many=True).data})

    def post(self, request, survey_id):
        row = operations.respond_vacation(
            actor=_actor(request), survey_id=survey_id,
            response=request.data.get("response", ""))
        return Response(s.VacationResponseSerializer(row).data)


class VacationReminderView(APIView):
    permission_classes = [MODULE, HasPermission(P_SURVEY)]

    def post(self, request, survey_id):
        sent = operations.send_vacation_reminder(actor=_actor(request),
                                                 survey_id=survey_id)
        return Response({"queued": sent})


class SpecialFoodView(APIView):
    permission_classes = [MODULE]

    def get_permissions(self):
        codes = (P_STUDENT, P_OPS) if self.request.method == "GET" else (P_STUDENT,)
        return [MODULE(), HasPermission(*codes)()]

    def get(self, request):
        actor = _actor(request)
        rows = SpecialFoodRequest.objects.prefetch_related("history")
        if actor.has_permission(P_STUDENT):
            rows = rows.filter(user_id=actor.user_id)
        else:
            _require_active_operator(actor)
        return Response({"results": s.SpecialFoodSerializer(
            rows.order_by("-created_at"), many=True).data})

    def post(self, request):
        row = operations.create_special_food(
            actor=_actor(request), reason=request.data.get("reason", ""),
            details=request.data.get("details", ""),
            requested_for=_date(request.data, "requested_for"))
        return Response(s.SpecialFoodSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class SpecialFoodDecisionView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    def post(self, request, request_id):
        if not isinstance(request.data.get("approve"), bool):
            raise BadRequestError("approve must be true or false.", code="invalid_decision")
        charge = request.data.get("charge_amount")
        try:
            charge_amount = Decimal(str(charge)) if charge is not None else None
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise BadRequestError("charge_amount must be a valid decimal.",
                                  code="invalid_special_food_charge") from exc
        row = operations.decide_special_food(
            actor=_actor(request), request_id=request_id,
            approve=request.data["approve"],
            charge_amount=charge_amount)
        return Response(s.SpecialFoodSerializer(row).data)


class SpecialFoodFulfillmentView(APIView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    def post(self, request, request_id):
        row = operations.update_special_fulfillment(
            actor=_actor(request), request_id=request_id,
            status=request.data.get("status", ""))
        return Response(s.SpecialFoodSerializer(row).data)


class AnnouncementsView(APIView):
    permission_classes = [MODULE]

    def get_permissions(self):
        codes = (P_STUDENT, P_OPS) if self.request.method == "GET" else (P_ANNOUNCE,)
        return [MODULE(), HasPermission(*codes)()]

    def get(self, request):
        actor = _actor(request)
        if not actor.has_permission(P_STUDENT):
            _require_active_operator(actor)
        rows = Announcement.objects.all()
        return Response({"results": s.AnnouncementSerializer(rows, many=True).data})

    def post(self, request):
        row = operations.publish_announcement(
            actor=_actor(request), title=request.data.get("title", ""),
            body=request.data.get("body", ""))
        return Response(s.AnnouncementSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class BillsView(APIView):
    permission_classes = [MODULE]

    def get_permissions(self):
        codes = (P_STUDENT, P_BILL) if self.request.method == "GET" else (P_BILL,)
        return [MODULE(), HasPermission(*codes)()]

    def get(self, request):
        actor = _actor(request)
        if actor.has_permission(P_STUDENT):
            rows = selectors.student_bills(actor.user_id)
            return Response({"results": s.BillSerializer(
                rows.order_by("-year", "-month"), many=True).data,
                "balance": operations.balance_for(actor.user_id)})
        roles.require_role(actor, "caretaker")
        rows = MonthlyBill.objects.all()
        return Response({"results": s.BillSerializer(
            rows.order_by("-year", "-month"), many=True).data})


class BillableStudentsView(APIView):
    permission_classes = [MODULE, HasPermission(P_BILL)]

    def get(self, request):
        roles.require_role(_actor(request), "caretaker")
        try:
            year = int(request.query_params["year"])
            month = int(request.query_params["month"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BadRequestError("Valid year and month are required.",
                                  code="invalid_billing_period") from exc
        if not 1 <= year <= 9998 or not 1 <= month <= 12:
            raise BadRequestError("Valid year and month are required.",
                                  code="invalid_billing_period")
        start = date(year, month, 1)
        end = (date(year + 1, 1, 1) if month == 12
               else date(year, month + 1, 1))
        start_at = timezone.make_aware(datetime.combine(start, time.min))
        end_at = timezone.make_aware(datetime.combine(end, time.min))
        users = Enrollment.objects.filter(registered_at__lt=end_at).filter(
            Q(deregistered_at__isnull=True) | Q(deregistered_at__gt=start_at)
        ).order_by("user_id")
        known_inputs = {
            row.user_id: row for row in BillingInput.objects.filter(year=year, month=month)
        }
        return Response({"results": [
            {
                "user_id": row.user_id,
                "served_days": (known_inputs[row.user_id].served_days
                                if row.user_id in known_inputs else None),
                "daily_rate": (known_inputs[row.user_id].daily_rate
                               if row.user_id in known_inputs else None),
            }
            for row in users
        ]})


class BillingInputsView(APIView):
    permission_classes = [MODULE, HasPermission(P_BILL)]

    def post(self, request):
        try:
            year, month = int(request.data.get("year", 0)), int(request.data.get("month", 0))
        except (TypeError, ValueError) as exc:
            raise BadRequestError("year and month must be integers.",
                                  code="invalid_billing_period") from exc
        count = operations.save_billing_inputs(
            actor=_actor(request), year=year, month=month,
            inputs=request.data.get("students"))
        return Response({"saved": count, "generation": "scheduled"})


class BillActionView(APIView):
    permission_classes = [MODULE, HasPermission(P_BILL)]

    def post(self, request, bill_id, action):
        if action == "finalize":
            row = operations.finalize_bill(actor=_actor(request), bill_id=bill_id)
        elif action == "publish":
            row = operations.publish_bill(actor=_actor(request), bill_id=bill_id)
        else:
            raise BadRequestError("Action must be finalize or publish.",
                                  code="invalid_bill_action")
        return Response(s.BillSerializer(row).data)


class FeedbackView(APIView):
    permission_classes = [MODULE]

    def get_permissions(self):
        codes = (P_STUDENT, P_FEEDBACK) if self.request.method == "GET" else (P_STUDENT,)
        return [MODULE(), HasPermission(*codes)()]

    def get(self, request):
        actor = _actor(request)
        if actor.has_permission(P_STUDENT):
            rows = Feedback.objects.filter(user_id=actor.user_id)
        else:
            _require_active_operator(actor)
            rows = Feedback.objects.all()
        return Response({"results": s.FeedbackSerializer(
            rows.order_by("-created_at"), many=True).data})

    def post(self, request):
        row = operations.submit_feedback(
            actor=_actor(request), message=request.data.get("message", ""))
        return Response(s.FeedbackSerializer(row).data,
                        status=status.HTTP_201_CREATED)


class ReportsView(APIView):
    permission_classes = [MODULE, HasPermission(P_WARDEN_REPORT, P_CARE_REPORT)]

    def get(self, request):
        actor = _actor(request)
        report = request.query_params.get("type")
        if report in {"registered", "rebates", "vacation"}:
            if not actor.has_permission(P_WARDEN_REPORT):
                from core.api.exceptions import PermissionDeniedError
                raise PermissionDeniedError("This supervisory report is Warden-only.")
            roles.require_role(actor, "warden")
            if report == "registered":
                rows = Enrollment.objects.filter(deregistered_at__isnull=True)
                return Response({"results": list(rows.values("user_id", "registered_at"))})
            if report == "rebates":
                rows = RebateRequest.objects.values(
                    "user_id", "reason", "starts_on", "ends_on", "status",
                    "created_at").order_by("-created_at")
                return Response({"results": list(rows)})
            surveys = []
            for survey in VacationSurvey.objects.all():
                counts = {row["response"]: row["count"] for row in
                          survey.responses.values("response").annotate(
                              count=Count("id"))}
                surveys.append({
                    **s.VacationSurveySerializer(survey).data,
                    "yes": counts.get("yes", 0), "no": counts.get("no", 0),
                })
            return Response({"results": surveys})
        if not actor.has_permission(P_CARE_REPORT):
            from core.api.exceptions import PermissionDeniedError
            raise PermissionDeniedError("Operational reports are Caretaker-only.")
        roles.require_role(actor, "caretaker")
        if report == "registration_trends":
            rows = StudentRequest.objects.filter(kind="registration").values(
                "created_at__date", "status").annotate(count=Count("id")).order_by(
                    "created_at__date")
            return Response({"results": list(rows)})
        if report == "special_meals":
            return Response({"results": s.SpecialFoodSerializer(
                SpecialFoodRequest.objects.all(), many=True).data})
        if report == "billing_summary":
            rows = MonthlyBill.objects.values("year", "month").annotate(
                total=Sum("total")).order_by("year", "month")
            return Response({"results": list(rows)})
        raise BadRequestError("Unsupported MMS report type.", code="invalid_report")


class OperationalOverviewView(APIView):
    permission_classes = [MODULE, HasPermission(P_OPS)]

    def get(self, request):
        actor = _actor(request)
        active_roles = [
            role for role in ("caretaker", "warden")
            if roles.is_active_role(actor.user_id, role)
        ]
        if not active_roles:
            _require_active_operator(actor)
        dashboard = selectors.operational_dashboard()
        return Response({
            "active_roles": active_roles,
            "requests": s.StudentRequestSerializer(
                dashboard["requests"],
                many=True).data,
            "rebates": s.RebateSerializer(
                dashboard["rebates"].prefetch_related("history"), many=True).data,
            "special_food": s.SpecialFoodSerializer(
                dashboard["special_food"].prefetch_related("history"), many=True).data,
            "surveys": s.VacationSurveySerializer(dashboard["surveys"], many=True).data,
            "announcements": s.AnnouncementSerializer(
                dashboard["announcements"], many=True).data,
            "feedback": s.FeedbackSerializer(dashboard["feedback"].order_by("-created_at"),
                                             many=True).data,
            "enrollment_count": dashboard["registered_students"].count(),
            "special_food_auto_rejection_enabled":
                (settings.MMS_SPECIAL_FOOD_DECISION_HOURS is not None
                 and settings.MMS_SPECIAL_FOOD_DECISION_HOURS > 0),
        })
