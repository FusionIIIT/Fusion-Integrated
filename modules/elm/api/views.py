"""HTTP layer for ELM endpoints."""
from __future__ import annotations

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.elm.api import serializers as s
from modules.elm.domain import categories as c
from modules.elm.domain import permissions as p
from modules.elm.domain import state_machine as sm
from modules.elm.domain.counting import (
    InvalidPeriod,
    chargeable_days,
    validate_rh_dates,
    validate_vacation,
)
from modules.elm.domain.overlap import Interval, overlaps
from modules.elm.domain.policy import NotEligible
from modules.elm.domain.routing import (
    RouteUnresolved,
    resolve_route,
    resumption_verifier,
)
from modules.elm.models import (
    CalendarVersion,
    LeaveRequest,
    LeaveTransition,
    LedgerEntry,
    Notification,
    OfflineLeaveRecord,
    PolicyVersion,
)
from modules.elm.selectors.config import (
    effective_calendar,
    effective_calendar_version,
    effective_policy,
)
from modules.elm.services import config as config_service
from modules.elm.services import ledger as ledger_service

MODULE = HasModuleGrant("elm")


def _actor(request):
    return getattr(request, "principal", None)


def _names_context(qs) -> dict:
    uids = set()
    for r in qs:
        uids.add(r.user_id)
        if r.substitute_user_id:
            uids.add(r.substitute_user_id)
    if not uids:
        return {}
    return directory.get_users(list(uids))


def _record_transition(req: LeaveRequest, frm: str, to: str, event: str,
                       actor_uid: int | None, actor_role: str = "", note: str = "") -> None:
    LeaveTransition.objects.create(
        request=req,
        from_status=frm,
        to_status=to,
        event=event,
        actor_user_id=actor_uid,
        actor_role=actor_role,
        note=note,
    )


class RequestListView(generics.ListCreateAPIView):
    serializer_class = s.LeaveRequestSerializer

    def get_permissions(self):
        perm = p.P_CREATE if self.request.method == "POST" else p.P_VIEW
        return [MODULE, HasPermission(perm)]

    def get_queryset(self):
        actor = _actor(self.request)
        return LeaveRequest.objects.filter(user_id=actor.user_id).order_by("-created_at", "-id")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["names"] = _names_context(self.get_queryset())
        return ctx

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        inp = s.LeaveInputSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        d = inp.validated_data
        actor = _actor(request)
        pv, policy = effective_policy()
        if pv is None or policy is None:
            raise BadRequestError("No published leave policy is active.", code="no_policy")

        users = directory.get_users([actor.user_id])
        prof = users.get(actor.user_id)
        kind = getattr(prof, "kind", "") or "faculty"
        unit = getattr(prof, "department", "") or ""
        try:
            policy.check_eligible(kind, d["category"])
        except NotEligible as exc:
            raise BadRequestError(str(exc), code="not_eligible") from exc

        if d["category"] in (c.RH, c.VL) and effective_calendar_version() is None:
            raise BadRequestError("No holiday calendar is published.", code="no_calendar")
        cal = effective_calendar()
        try:
            if d["category"] == c.RH:
                validate_rh_dates(d["start_date"], d["end_date"], cal)
            elif d["category"] == c.VL:
                validate_vacation(d["start_date"], d["end_date"], cal)
            days = chargeable_days(
                d["category"], d["start_date"], d["end_date"], d.get("half") or None, cal
            )
        except InvalidPeriod as exc:
            raise BadRequestError(str(exc), code="invalid_period") from exc

        for existing in LeaveRequest.objects.filter(
            user_id=actor.user_id, status__in=list(sm.ACTIVE)
        ):
            if overlaps(
                Interval(d["start_date"], d["end_date"], d.get("half") or None),
                Interval(existing.start_date, existing.end_date, existing.half or None),
            ):
                raise ConflictError("Overlaps with an existing leave request.", code="overlap")

        try:
            steps = resolve_route(
                category=d["category"],
                kind=kind,
                unit=unit,
                applicant_roles=getattr(actor, "roles", []),
                hierarchy=pv.hierarchy,
            )
        except RouteUnresolved as exc:
            raise BadRequestError(str(exc), code="route_unresolved") from exc

        sub_uid = d.get("substitute_user_id")
        if sub_uid:
            init_status = sm.AWAITING_SUBSTITUTE
            cur_role = ""
            sub_status = "pending"
        else:
            init_status = sm.STATE_FOR_STEP[steps[0].step]
            cur_role = steps[0].role
            sub_status = ""

        req = LeaveRequest.objects.create(
            user_id=actor.user_id,
            kind=LeaveRequest.LEAVE,
            category=d["category"],
            applicant_kind=kind,
            applicant_unit=unit,
            start_date=d["start_date"],
            end_date=d["end_date"],
            half=d.get("half") or "",
            days=days,
            purpose=d["purpose"],
            medical_evidence=d.get("medical_evidence") or "",
            station_leave=bool(d.get("station_leave")),
            station_from=d.get("station_from"),
            station_to=d.get("station_to"),
            station_address=d.get("station_address") or "",
            substitute_user_id=sub_uid,
            substitute_status=sub_status,
            responsibility=d.get("responsibility") or "",
            status=init_status,
            route=[st.as_dict() for st in steps],
            stage=0,
            current_role=cur_role,
            stage_entered_at=timezone.now(),
            policy_version_id=pv.pk,
        )
        _record_transition(req, sm.NEW, init_status, sm.SUBMIT, actor.user_id)
        return Response(
            s.LeaveRequestSerializer(req, context={"names": _names_context([req])}).data,
            status=status.HTTP_201_CREATED,
        )


class RequestDetailView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_VIEW)]

    def get(self, request, pk: int):
        actor = _actor(request)
        req = LeaveRequest.objects.filter(pk=pk, user_id=actor.user_id).first()
        if req is None:
            raise NotFoundError("Leave request not found.")
        data = s.LeaveRequestSerializer(req, context={"names": _names_context([req])}).data
        data["history"] = s.TransitionSerializer(
            req.transitions.order_by("at", "id"), many=True
        ).data
        return Response(data)


class ModifyView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_UPDATE)]

    @transaction.atomic
    def post(self, request, pk: int):
        actor = _actor(request)
        req = LeaveRequest.objects.select_for_update().filter(
            pk=pk, user_id=actor.user_id
        ).first()
        if req is None:
            raise NotFoundError("Leave request not found.")
        if req.status not in sm.PENDING:
            raise ConflictError("Only pending requests can be modified.", code="not_pending")
        inp = s.LeaveInputSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        d = inp.validated_data
        cal = effective_calendar()
        try:
            days = chargeable_days(
                d["category"], d["start_date"], d["end_date"], d.get("half") or None, cal
            )
        except InvalidPeriod as exc:
            raise BadRequestError(str(exc), code="invalid_period") from exc

        frm = req.status
        sub_uid = d.get("substitute_user_id")
        if sub_uid:
            to_status = sm.AWAITING_SUBSTITUTE
            cur_role = ""
            sub_status = "pending"
        else:
            step0 = req.route[0]
            to_status = sm.STATE_FOR_STEP[step0["step"]]
            cur_role = step0["role"]
            sub_status = ""

        req.category = d["category"]
        req.start_date = d["start_date"]
        req.end_date = d["end_date"]
        req.half = d.get("half") or ""
        req.days = days
        req.purpose = d["purpose"]
        req.medical_evidence = d.get("medical_evidence") or ""
        req.station_leave = bool(d.get("station_leave"))
        req.station_from = d.get("station_from")
        req.station_to = d.get("station_to")
        req.station_address = d.get("station_address") or ""
        req.substitute_user_id = sub_uid
        req.substitute_status = sub_status
        req.responsibility = d.get("responsibility") or ""
        req.status = to_status
        req.stage = 0
        req.current_role = cur_role
        req.stage_entered_at = timezone.now()
        req.save()
        _record_transition(req, frm, to_status, sm.MODIFY, actor.user_id)
        return Response(s.LeaveRequestSerializer(req).data)


class WithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_WITHDRAW)]

    @transaction.atomic
    def post(self, request, pk: int):
        actor = _actor(request)
        req = LeaveRequest.objects.select_for_update().filter(
            pk=pk, user_id=actor.user_id
        ).first()
        if req is None:
            raise NotFoundError("Leave request not found.")
        if req.status not in sm.PENDING:
            raise ConflictError("Only pending requests can be withdrawn.", code="not_pending")
        inp = s.ReasonSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        frm = req.status
        req.status = sm.WITHDRAWN
        req.current_role = ""
        req.save(update_fields=["status", "current_role", "updated_at"])
        _record_transition(
            req, frm, sm.WITHDRAWN, sm.WITHDRAW, actor.user_id, note=inp.validated_data["reason"]
        )
        return Response(s.LeaveRequestSerializer(req).data)


class CancelView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_UPDATE)]

    @transaction.atomic
    def post(self, request, pk: int):
        actor = _actor(request)
        req = LeaveRequest.objects.select_for_update().filter(
            pk=pk, user_id=actor.user_id
        ).first()
        if req is None:
            raise NotFoundError("Leave request not found.")
        if req.status != sm.APPROVED or req.start_date <= timezone.localdate():
            raise ConflictError("Leave can only be cancelled before it starts.", code="invalid_state")
        inp = s.ReasonSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        req.status = sm.CANCELLATION_PENDING
        req.stage = 0
        req.current_role = req.route[0]["role"] if req.route else ""
        req.stage_entered_at = timezone.now()
        req.save()
        _record_transition(
            req, sm.APPROVED, sm.CANCELLATION_PENDING, sm.REQUEST_CANCELLATION,
            actor.user_id, note=inp.validated_data["reason"]
        )
        return Response(s.LeaveRequestSerializer(req).data)


class RenominateView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_UPDATE)]

    @transaction.atomic
    def post(self, request, pk: int):
        actor = _actor(request)
        req = LeaveRequest.objects.select_for_update().filter(
            pk=pk, user_id=actor.user_id
        ).first()
        if req is None:
            raise NotFoundError("Leave request not found.")
        if req.status != sm.SUBSTITUTE_DECLINED:
            raise ConflictError("Request is not awaiting renomination.", code="invalid_state")
        inp = s.RenominateSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        d = inp.validated_data
        req.substitute_user_id = d["substitute_user_id"]
        req.substitute_status = "pending"
        req.responsibility = d.get("responsibility") or req.responsibility
        req.status = sm.AWAITING_SUBSTITUTE
        req.save()
        _record_transition(
            req, sm.SUBSTITUTE_DECLINED, sm.AWAITING_SUBSTITUTE, sm.RENOMINATE, actor.user_id
        )
        return Response(s.LeaveRequestSerializer(req).data)


class ExtendView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_CREATE)]

    @transaction.atomic
    def post(self, request, pk: int):
        actor = _actor(request)
        parent = LeaveRequest.objects.select_for_update().filter(
            pk=pk, user_id=actor.user_id
        ).first()
        if parent is None:
            raise NotFoundError("Leave request not found.")
        if parent.status != sm.APPROVED or parent.category not in c.EXTENDABLE:
            raise ConflictError("Only ongoing EL, COL or VL can be extended.", code="invalid_state")
        inp = s.ExtensionSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        d = inp.validated_data
        from datetime import timedelta

        ext_start = parent.end_date + timedelta(days=1)
        cal = effective_calendar()
        try:
            days = chargeable_days(parent.category, ext_start, d["end_date"], None, cal)
        except InvalidPeriod as exc:
            raise BadRequestError(str(exc), code="invalid_period") from exc
        step0 = parent.route[0]
        init_status = sm.STATE_FOR_STEP[step0["step"]]
        ext = LeaveRequest.objects.create(
            user_id=actor.user_id,
            kind=LeaveRequest.EXTENSION,
            parent=parent,
            category=parent.category,
            applicant_kind=parent.applicant_kind,
            applicant_unit=parent.applicant_unit,
            start_date=ext_start,
            end_date=d["end_date"],
            days=days,
            purpose=d["purpose"],
            status=init_status,
            route=parent.route,
            stage=0,
            current_role=step0["role"],
            stage_entered_at=timezone.now(),
            policy_version_id=parent.policy_version_id,
        )
        _record_transition(ext, sm.NEW, init_status, sm.SUBMIT, actor.user_id)
        return Response(s.LeaveRequestSerializer(ext).data, status=status.HTTP_201_CREATED)


class ResumeView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_UPDATE)]

    @transaction.atomic
    def post(self, request, pk: int):
        actor = _actor(request)
        req = LeaveRequest.objects.select_for_update().filter(
            pk=pk, user_id=actor.user_id
        ).first()
        if req is None:
            raise NotFoundError("Leave request not found.")
        if req.status != sm.APPROVED or req.category not in c.RESUMABLE:
            raise ConflictError("Resumption is not applicable.", code="invalid_state")
        inp = s.ResumptionSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        d = inp.validated_data
        pv, _ = effective_policy()
        verifier = resumption_verifier(req.route, pv.hierarchy if pv else {})
        req.actual_return_date = d["actual_return_date"]
        req.resumption_note = d.get("note") or ""
        req.status = sm.RESUMPTION_PENDING
        req.current_role = verifier
        req.stage_entered_at = timezone.now()
        req.save()
        _record_transition(
            req, sm.APPROVED, sm.RESUMPTION_PENDING, sm.SUBMIT_RESUMPTION,
            actor.user_id, note=req.resumption_note
        )
        return Response(s.LeaveRequestSerializer(req).data)


class PrintView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_VIEW)]

    def get(self, request, pk: int):
        actor = _actor(request)
        req = LeaveRequest.objects.filter(pk=pk, user_id=actor.user_id).first()
        if req is None:
            raise NotFoundError("Leave request not found.")
        body = (
            f"Leave Application #{req.pk}\n"
            f"Category: {c.LABELS.get(req.category, req.category)}\n"
            f"Period: {req.start_date} to {req.end_date} ({req.days} days)\n"
            f"Status: {req.status}\n"
            f"Purpose: {req.purpose}\n"
        )
        res = HttpResponse(body, content_type="text/plain; charset=utf-8")
        res["Content-Disposition"] = f'attachment; filename="leave-{req.pk}.txt"'
        return res


class BalanceView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_BALANCE)]

    def get(self, request):
        actor = _actor(request)
        users = directory.get_users([actor.user_id])
        prof = users.get(actor.user_id)
        kind = getattr(prof, "kind", "") or "faculty"
        acc = ledger_service.get_account(actor.user_id, kind)
        return Response(s.BalanceSerializer(acc).data)


class EmployeeSearchView(APIView):
    permission_classes = [MODULE]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        actor = _actor(request)
        if len(q) < 2:
            return Response({"results": []})
        hits = directory.search(q, limit=20)
        results = [
            {
                "user_id": u.user_id,
                "display_name": u.display_name,
                "username": u.username,
                "kind": u.kind,
                "department": u.department,
            }
            for u in hits
            if u.kind in c.EMPLOYEE_KINDS and u.user_id != getattr(actor, "user_id", None)
        ]
        return Response({"results": results})


class NotificationListView(generics.ListAPIView):
    permission_classes = [MODULE]
    serializer_class = s.NotificationSerializer

    def get_queryset(self):
        actor = _actor(self.request)
        roles = list(getattr(actor, "roles", []) or [])
        from django.db.models import Q

        return Notification.objects.filter(
            Q(recipient_user_id=actor.user_id) | Q(recipient_role__in=roles)
        ).order_by("-created_at", "-id")


class SubstitutionListView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(p.P_SUBSTITUTE)]
    serializer_class = s.LeaveRequestSerializer

    def get_queryset(self):
        actor = _actor(self.request)
        return LeaveRequest.objects.filter(substitute_user_id=actor.user_id).order_by(
            "-created_at", "-id"
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["names"] = _names_context(self.get_queryset())
        return ctx


class SubstitutionRespondView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_SUBSTITUTE)]

    @transaction.atomic
    def post(self, request, pk: int):
        actor = _actor(request)
        req = LeaveRequest.objects.select_for_update().filter(
            pk=pk, substitute_user_id=actor.user_id
        ).first()
        if req is None:
            raise NotFoundError("Substitution request not found.")
        if req.status != sm.AWAITING_SUBSTITUTE:
            raise ConflictError("Request is no longer awaiting substitute response.",
                                code="invalid_state")
        inp = s.SubstituteResponseSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        d = inp.validated_data
        if d["accept"]:
            step0 = req.route[0]
            to_status = sm.STATE_FOR_STEP[step0["step"]]
            req.substitute_status = "accepted"
            req.status = to_status
            req.stage = 0
            req.current_role = step0["role"]
            req.stage_entered_at = timezone.now()
            event = sm.SUBSTITUTE_ACCEPT
        else:
            to_status = sm.SUBSTITUTE_DECLINED
            req.substitute_status = "declined"
            req.status = to_status
            req.current_role = ""
            event = sm.SUBSTITUTE_DECLINE
        req.save()
        _record_transition(req, sm.AWAITING_SUBSTITUTE, to_status, event,
                           actor.user_id, note=d.get("note") or "")
        return Response(s.LeaveRequestSerializer(req).data)


class QueueView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(p.P_REVIEW)]
    serializer_class = s.LeaveRequestSerializer

    def get_queryset(self):
        actor = _actor(self.request)
        roles = list(getattr(actor, "roles", []) or [])
        return LeaveRequest.objects.filter(
            current_role__in=roles,
            status__in=[
                sm.AWAITING_UNIT_HEAD,
                sm.AWAITING_ESTABLISHMENT,
                sm.AWAITING_SANCTION,
                sm.AWAITING_DIRECTOR,
                sm.CANCELLATION_PENDING,
            ],
        ).order_by("created_at", "id")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["queue"] = True
        ctx["names"] = _names_context(self.get_queryset())
        return ctx


class DecideView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_REVIEW)]

    @transaction.atomic
    def post(self, request, pk: int):
        actor = _actor(request)
        roles = set(getattr(actor, "roles", []) or [])
        req = LeaveRequest.objects.select_for_update().filter(pk=pk).first()
        if req is None or req.current_role not in roles:
            raise NotFoundError("Leave request not in your queue.")
        inp = s.DecisionSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        event = inp.validated_data["event"]
        note = inp.validated_data.get("note") or ""
        frm = req.status
        role_used = req.current_role

        if event in (sm.RECOMMEND, sm.NOT_RECOMMEND, sm.FORWARD):
            if event in (sm.RECOMMEND, sm.NOT_RECOMMEND):
                req.recommendation = (
                    "recommended" if event == sm.RECOMMEND else "not_recommended"
                )
            req.stage += 1
            nxt = req.current_step
            if nxt is None:
                raise ConflictError("No next step in route.", code="invalid_route")
            to_status = sm.STATE_FOR_STEP[nxt["step"]]
            req.status = to_status
            req.current_role = nxt["role"]
            req.stage_entered_at = timezone.now()
        elif event == sm.APPROVE:
            to_status = sm.APPROVED
            req.status = to_status
            req.current_role = ""
            req.decision_note = note
            req.decided_at = timezone.now()
            LedgerEntry.objects.get_or_create(
                request=req,
                entry_type=LedgerEntry.DEBIT,
                defaults={
                    "user_id": req.user_id,
                    "category": req.category,
                    "delta": -req.days,
                    "year": req.start_date.year,
                    "note": f"Leave #{req.pk} approved",
                },
            )
        elif event == sm.REJECT:
            to_status = sm.REJECTED
            req.status = to_status
            req.current_role = ""
            req.decision_note = note
            req.decided_at = timezone.now()
        elif event == sm.CANCEL_ADVANCE:
            req.stage += 1
            nxt = req.current_step
            if nxt is None:
                raise ConflictError("No next step in route.", code="invalid_route")
            to_status = sm.CANCELLATION_PENDING
            req.current_role = nxt["role"]
            req.stage_entered_at = timezone.now()
        elif event == sm.CANCEL_APPROVE:
            to_status = sm.CANCELLED
            req.status = to_status
            req.current_role = ""
            LedgerEntry.objects.get_or_create(
                request=req,
                entry_type=LedgerEntry.REVERSAL,
                defaults={
                    "user_id": req.user_id,
                    "category": req.category,
                    "delta": req.days,
                    "year": req.start_date.year,
                    "note": f"Leave #{req.pk} cancelled",
                },
            )
        elif event == sm.CANCEL_REJECT:
            to_status = sm.APPROVED
            req.status = to_status
            req.current_role = ""
        else:
            raise BadRequestError("Unsupported decision event.", code="invalid_event")

        req.save()
        _record_transition(req, frm, to_status, event, actor.user_id, role_used, note)
        return Response(s.LeaveRequestSerializer(req).data)


class ResumptionQueueView(generics.ListAPIView):
    permission_classes = [MODULE, HasPermission(p.P_RESUMPTION)]
    serializer_class = s.LeaveRequestSerializer

    def get_queryset(self):
        actor = _actor(self.request)
        roles = list(getattr(actor, "roles", []) or [])
        return LeaveRequest.objects.filter(
            status=sm.RESUMPTION_PENDING, current_role__in=roles
        ).order_by("created_at", "id")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["names"] = _names_context(self.get_queryset())
        return ctx


class VerifyView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_RESUMPTION)]

    @transaction.atomic
    def post(self, request, pk: int):
        actor = _actor(request)
        roles = set(getattr(actor, "roles", []) or [])
        req = LeaveRequest.objects.select_for_update().filter(
            pk=pk, status=sm.RESUMPTION_PENDING
        ).first()
        if req is None or req.current_role not in roles:
            raise NotFoundError("Resumption request not found.")
        inp = s.VerifySerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        d = inp.validated_data
        role_used = req.current_role
        if d["verified"]:
            req.status = sm.CLOSED
            req.current_role = ""
            req.save(update_fields=["status", "current_role", "updated_at"])
            _record_transition(
                req, sm.RESUMPTION_PENDING, sm.CLOSED, sm.VERIFY_RESUMPTION,
                actor.user_id, role_used, d.get("note") or ""
            )
        else:
            req.status = sm.APPROVED
            req.current_role = ""
            req.save(update_fields=["status", "current_role", "updated_at"])
            _record_transition(
                req, sm.RESUMPTION_PENDING, sm.APPROVED, "resumption_rejected",
                actor.user_id, role_used, d.get("note") or ""
            )
        return Response(s.LeaveRequestSerializer(req).data)


class PolicyListView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission(p.P_POLICY)]
    serializer_class = s.PolicyVersionSerializer
    queryset = PolicyVersion.objects.all().order_by("-effective_from", "-id")

    def perform_create(self, serializer):
        actor = _actor(self.request)
        d = serializer.validated_data
        pv = config_service.create_policy(
            name=d["name"],
            effective_from=d["effective_from"],
            params=d["params"],
            hierarchy=d["hierarchy"],
            actor_user_id=getattr(actor, "user_id", None),
        )
        serializer.instance = pv


class PolicyDetailView(generics.RetrieveAPIView):
    permission_classes = [MODULE, HasPermission(p.P_POLICY)]
    serializer_class = s.PolicyVersionSerializer
    queryset = PolicyVersion.objects.all()


class PolicyPublishView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_POLICY)]

    def post(self, request, pk: int):
        pv = config_service.publish_policy(pk)
        return Response(s.PolicyVersionSerializer(pv).data)


class CalendarListView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission(p.P_CALENDAR)]
    serializer_class = s.CalendarVersionSerializer
    queryset = CalendarVersion.objects.prefetch_related("entries").order_by(
        "-effective_from", "-id"
    )

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        actor = _actor(request)
        cv = config_service.create_calendar(
            name=d["name"],
            effective_from=d["effective_from"],
            entries=d.get("entries") or [],
            actor_user_id=getattr(actor, "user_id", None),
        )
        return Response(
            s.CalendarVersionSerializer(cv).data, status=status.HTTP_201_CREATED
        )


class CalendarDetailView(generics.RetrieveAPIView):
    permission_classes = [MODULE, HasPermission(p.P_CALENDAR)]
    serializer_class = s.CalendarVersionSerializer
    queryset = CalendarVersion.objects.prefetch_related("entries")


class CalendarPublishView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_CALENDAR)]

    def post(self, request, pk: int):
        cv = config_service.publish_calendar(pk)
        return Response(s.CalendarVersionSerializer(cv).data)


class OfflineListView(generics.ListCreateAPIView):
    permission_classes = [MODULE, HasPermission(p.P_OFFLINE)]
    serializer_class = s.OfflineRecordSerializer
    queryset = OfflineLeaveRecord.objects.select_related("request").order_by(
        "-created_at", "-id"
    )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        inp = s.OfflineInputSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        d = inp.validated_data
        actor = _actor(request)
        cal = effective_calendar()
        try:
            days = chargeable_days(
                d["category"], d["start_date"], d["end_date"], d.get("half") or None, cal
            )
        except InvalidPeriod as exc:
            raise BadRequestError(str(exc), code="invalid_period") from exc
        users = directory.get_users([d["user_id"]])
        prof = users.get(d["user_id"])
        kind = getattr(prof, "kind", "") or "faculty"
        unit = getattr(prof, "department", "") or ""
        req = LeaveRequest.objects.create(
            user_id=d["user_id"],
            kind=LeaveRequest.OFFLINE,
            category=d["category"],
            applicant_kind=kind,
            applicant_unit=unit,
            start_date=d["start_date"],
            end_date=d["end_date"],
            half=d.get("half") or "",
            days=days,
            purpose=d.get("purpose") or "Offline sanctioned leave",
            status=sm.APPROVED,
            decided_at=timezone.now(),
        )
        rec = OfflineLeaveRecord.objects.create(
            request=req,
            sanction_reference=d["sanction_reference"],
            sanctioned_by=d["sanctioned_by"],
            sanctioned_on=d["sanctioned_on"],
            evidence_note=d.get("evidence_note") or "",
            recorded_by_user_id=actor.user_id,
        )
        LedgerEntry.objects.create(
            user_id=d["user_id"],
            category=d["category"],
            entry_type=LedgerEntry.OFFLINE_DEBIT,
            delta=-days,
            year=d["start_date"].year,
            request=req,
            note=f"Offline ref {d['sanction_reference']}",
        )
        _record_transition(req, sm.NEW, sm.APPROVED, sm.RECORD_OFFLINE, actor.user_id)
        return Response(
            s.OfflineRecordSerializer(rec).data, status=status.HTTP_201_CREATED
        )


class AccountView(APIView):
    permission_classes = [MODULE, HasPermission(p.P_ACCOUNT_VIEW)]

    def get(self, request):
        raw_uid = request.query_params.get("user_id")
        try:
            uid = int(raw_uid)
        except (TypeError, ValueError) as exc:
            raise BadRequestError("user_id is required.", code="invalid_filter") from exc
        users = directory.get_users([uid])
        prof = users.get(uid)
        kind = getattr(prof, "kind", "") or ""
        acc = ledger_service.get_account(uid, kind)
        data = s.BalanceSerializer(acc).data
        if prof:
            data["display_name"] = prof.display_name
        return Response(data)
