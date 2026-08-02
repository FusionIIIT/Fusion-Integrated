"""HTTP layer: parse, scope, delegate, serialise.

Every view takes its queryset from `selectors.scoping`, so authorisation is
never re-derived per endpoint. Anything out of scope is simply absent, which
is why detail views 404 rather than 403.
"""
from __future__ import annotations

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import csrf
from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.client import IamUnavailable
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.directory import contracts as directory
from modules.placement.api import serializers as s
from modules.placement.api.permissions import ScopedCollection
from modules.placement.authentication import (
    COOKIE_NAME as RECRUITER_COOKIE,
)
from modules.placement.authentication import (
    COOKIE_PATH as RECRUITER_COOKIE_PATH,
)
from modules.placement.authentication import (
    RecruiterAuthentication,
)
from modules.placement.models import (
    PlacementPolicy,
    RecruiterAccount,
)
from modules.placement.selectors import scoping
from modules.placement.services import announcements as announcement_service
from modules.placement.services import applications as application_service
from modules.placement.services import companies as company_service
from modules.placement.services import interviews as interview_service
from modules.placement.services import offers as offer_service
from modules.placement.services import postings as posting_service
from modules.placement.services import profiles as profile_service
from modules.placement.services import recruiters as recruiter_service
from modules.placement.services import stats as stats_service

MODULE = HasModuleGrant("placement_cell")

P_VIEW_POSTINGS = "placement_cell.job_posting.view"
P_MANAGE_POSTINGS = "placement_cell.job_posting.manage"
P_VIEW_APPS = "placement_cell.application.view"
P_VIEW_SELF = "placement_cell.application.view_self"
P_MANAGE_COMPANIES = "placement_cell.company.manage"
P_VIEW_REPORTS = "placement_cell.report.view"


def _actor(request):
    return getattr(request, "principal", None)


def _int_param(params, name):
    """A non-integer filter is a 400, not a ValueError deep in the ORM."""
    raw = params.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise BadRequestError(f"{name} must be a number.",
                              code="invalid_filter") from exc


def _client_ip(request):
    """The hop our proxy added, not the first one the client claimed."""
    from rest_framework.settings import api_settings

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    hops = api_settings.NUM_PROXIES or 0
    if forwarded and hops:
        addrs = [a.strip() for a in forwarded.split(",") if a.strip()]
        if addrs:
            return addrs[-min(hops, len(addrs))]
    return request.META.get("REMOTE_ADDR")


class _Scoped(generics.GenericAPIView):
    """Recruiters authenticate on a separate scheme; both pools land on
    `request.principal`."""

    authentication_classes = [RecruiterAuthentication,
                              *generics.GenericAPIView.authentication_classes]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["actor"] = _actor(self.request)
        return ctx


# -- Postings ------------------------------------------------------------------
class PostingListView(_Scoped, generics.ListCreateAPIView):
    serializer_class = s.JobPostingSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        qs = scoping.postings_for(_actor(self.request))
        year = self.request.query_params.get("placement_year")
        kind = self.request.query_params.get("kind")
        if year:
            qs = qs.filter(placement_year=year)
        if kind:
            qs = qs.filter(kind=kind)
        return qs.order_by("-created_at")

    def create(self, request, *args, **kwargs):
        actor = _actor(request)
        payload = s.JobPostingWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)

        if getattr(actor, "kind", None) == "recruiter":
            # From the credential, never the body: a one-field escalation.
            data.pop("company_id", None)
            company_id = actor.company_id
        else:
            company_id = data.pop("company_id", None)
            if company_id is None:
                raise ConflictError("company_id is required.",
                                    code="company_required")

        posting = posting_service.create(
            company_id=company_id, actor=actor,
            placement_year=data.pop("placement_year"), **data)
        return Response(s.JobPostingSerializer(posting).data,
                        status=status.HTTP_201_CREATED)


class PostingDetailView(_Scoped, generics.RetrieveUpdateAPIView):
    serializer_class = s.JobPostingSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        return scoping.postings_for(_actor(self.request))

    def update(self, request, *args, **kwargs):
        actor = _actor(request)
        payload = s.JobPostingWriteSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        data.pop("company_id", None)          # never reassignable
        data.pop("placement_year", None)      # never reassignable
        posting = posting_service.update(
            posting_id=kwargs["pk"], actor=actor, scope=self.get_queryset(),
            **data)
        return Response(s.JobPostingSerializer(posting).data)


@extend_schema(request=None, responses=s.JobPostingSerializer)
class PostingPublishView(_Scoped, APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        posting = posting_service.publish(
            posting_id=pk, actor=_actor(request),
            scope=scoping.postings_for(_actor(request)))
        return Response(s.JobPostingSerializer(posting).data)


@extend_schema(responses=s.EligibilityVerdictSerializer)
class PostingEligibilityView(_Scoped, APIView):
    """PC-UC-003's precondition, made visible to the student."""

    permission_classes = [MODULE, HasPermission(P_VIEW_POSTINGS, P_VIEW_SELF)]

    def get(self, request, pk):
        actor = _actor(request)
        posting = scoping.postings_for(actor).filter(pk=pk).first()
        if posting is None:
            raise NotFoundError("No such posting.")
        policy = PlacementPolicy.objects.filter(
            season=posting.placement_year).first()
        if policy is None:
            raise ConflictError("No placement policy for this season.",
                                code="policy_missing")
        try:
            verdict = application_service.evaluate_for(
                posting=posting, user_id=actor.user_id, policy=policy)
        except IamUnavailable as exc:
            # A 503 is truthful; "ineligible" would be a lie acted on.
            return Response(
                {"error": {"code": "identity_service_unavailable",
                           "message": f"Academic records are unavailable: {exc}",
                           "details": [], "request_id": ""}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(verdict)


# -- Applications --------------------------------------------------------------
class ApplicationListView(_Scoped, generics.ListAPIView):
    # A recruiter reaches this too; they are authorised by the company-scoped
    # queryset rather than by a permission code. See api/permissions.py.
    permission_classes = [MODULE, ScopedCollection(P_VIEW_APPS, P_VIEW_SELF)]

    def get_serializer_class(self):
        if getattr(_actor(self.request), "kind", None) == "recruiter":
            return s.ApplicantSerializer
        return s.ApplicationSerializer

    serializer_class = s.ApplicationSerializer     # the documented default

    def get_queryset(self):
        qs = scoping.applications_for(_actor(self.request))
        posting_id = _int_param(self.request.query_params, "posting")
        state = self.request.query_params.get("status")
        if posting_id:
            qs = qs.filter(posting_id=posting_id)
        if state:
            qs = qs.filter(status=state)
        return qs.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        actor = _actor(request)
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        rows = page if page is not None else list(queryset)

        # One batched directory call for the page. A student reading their
        # own list needs no names, so no call is made.
        context = {"actor": actor, "view": self, "request": request}
        if scoping.is_staff(actor) or getattr(actor, "kind", None) == "recruiter":
            context["people"] = directory.get_users([a.user_id for a in rows])

        data = self.get_serializer_class()(rows, many=True, context=context).data
        return (self.get_paginated_response(data) if page is not None
                else Response(data))


@extend_schema(request=s.TransitionSerializer, responses=s.ApplicationSerializer)
class ApplicationTransitionView(_Scoped, APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        payload = s.TransitionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        app = application_service.transition(
            application_id=pk, to_status=payload.validated_data["to_status"],
            actor=actor, reason=payload.validated_data["reason"],
            scope=scoping.applications_for(actor))
        return Response(s.ApplicationSerializer(
            app, context={"actor": actor}).data)


@extend_schema(request=s.ApplySerializer, responses=s.ApplicationSerializer)
class ApplyView(_Scoped, APIView):
    permission_classes = [MODULE, HasPermission("placement_cell.application.create")]
    throttle_scope = "apply"

    def post(self, request):
        payload = s.ApplySerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        try:
            app = application_service.apply_to(actor=actor,
                                               **payload.validated_data)
        except IamUnavailable as exc:
            return Response(
                {"error": {"code": "identity_service_unavailable",
                           "message": f"Academic records are unavailable: {exc}",
                           "details": [], "request_id": ""}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(s.ApplicationSerializer(app, context={"actor": actor}).data,
                        status=status.HTTP_201_CREATED)


# -- Profile -------------------------------------------------------------------
@extend_schema(request=s.StudentProfileSerializer,
               responses=s.StudentProfileSerializer)
class MyProfileView(_Scoped, APIView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        actor = _actor(request)
        profile = scoping.profiles_for(actor).filter(
            user_id=actor.user_id).first()
        if profile is None:
            return Response({"user_id": actor.user_id, "exists": False,
                             "completeness_percent": 0, "is_complete": False})
        return Response(s.StudentProfileSerializer(profile).data)

    def put(self, request):
        actor = _actor(request)
        payload = s.StudentProfileSerializer(data=request.data, partial=True)
        payload.is_valid(raise_exception=True)
        profile = profile_service.upsert(user_id=actor.user_id,
                                         data=payload.validated_data)
        return Response(s.StudentProfileSerializer(profile).data)


@extend_schema(responses=s.ResumeSerializer)
class MyResumeView(_Scoped, APIView):
    """PC-UC-002: a structured resume derived from the profile."""

    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        actor = _actor(request)
        standing = None
        try:
            from modules.placement.services import facts
            standing = (facts.academic_facts([actor.user_id])
                        .get(actor.user_id, {}).get("_standing"))
        except IamUnavailable:
            standing = None          # the resume still renders, minus the CPI
        return Response(profile_service.build_resume(
            user_id=actor.user_id, standing=standing))


class ProfileDetailView(_Scoped, generics.RetrieveAPIView):
    """A recruiter or the TPO reading a candidate's profile.

    Scoped so a recruiter reaches only their own live applicants — see
    selectors/scoping.profiles_for.
    """

    serializer_class = s.StudentProfileSerializer
    permission_classes = [MODULE]
    lookup_field = "user_id"

    def get_queryset(self):
        return scoping.profiles_for(_actor(self.request))


# -- Companies -----------------------------------------------------------------
class CompanyListView(_Scoped, generics.ListCreateAPIView):
    serializer_class = s.CompanySerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        return scoping.companies_for(_actor(self.request)).order_by("name")

    def create(self, request, *args, **kwargs):
        payload = s.CompanyRegisterSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        d = payload.validated_data
        company = company_service.register(
            name=d["name"], sector=d.get("sector", ""),
            website=d.get("website", ""), hq_city=d.get("hq_city", ""),
            contact={"name": d.get("contact_name", ""),
                     "email": d.get("contact_email", ""),
                     "phone": d.get("contact_phone", "")}
            if d.get("contact_email") else None,
            actor=_actor(request),
            registered_by_user_id=getattr(_actor(request), "user_id", None))
        return Response(s.CompanySerializer(company).data,
                        status=status.HTTP_201_CREATED)


class CompanyApprovalView(_Scoped, APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_COMPANIES)]

    @extend_schema(
        # Distinct from the company-create POST, which generates the same
        # operationId otherwise.
        operation_id="placement_company_decide",
        request=s.ApprovalSerializer, responses=s.CompanySerializer)
    def post(self, request, pk, action):
        payload = s.ApprovalSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        note = payload.validated_data["note"]
        actor = _actor(request)
        if action == "approve":
            company = company_service.approve(company_id=pk, actor=actor,
                                              note=note)
        elif action == "reject":
            company = company_service.reject(company_id=pk, actor=actor,
                                             note=note)
        elif action == "blacklist":
            company = company_service.blacklist(company_id=pk, actor=actor,
                                                note=note)
        else:
            raise NotFoundError("Unknown action.")
        return Response(s.CompanySerializer(company).data)


# -- Interviews ----------------------------------------------------------------
class InterviewRoundListView(_Scoped, generics.ListCreateAPIView):
    serializer_class = s.InterviewRoundSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        qs = scoping.interview_rounds_for(_actor(self.request))
        posting_id = _int_param(self.request.query_params, "posting")
        if posting_id:
            qs = qs.filter(posting_id=posting_id)
        return qs.order_by("posting_id", "seq")

    def create(self, request, *args, **kwargs):
        payload = s.InterviewRoundWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        round_ = interview_service.schedule_round(
            actor=actor, scope=scoping.postings_for(actor),
            **payload.validated_data)
        return Response(s.InterviewRoundSerializer(round_).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.AddCandidatesSerializer,
               responses=s.ScheduledCountSerializer)
class RoundCandidatesView(_Scoped, APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        payload = s.AddCandidatesSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        n = interview_service.add_candidates(
            round_id=pk, application_ids=payload.validated_data["application_ids"],
            actor=actor, scope=scoping.applications_for(actor))
        return Response({"scheduled": n}, status=status.HTTP_201_CREATED)


@extend_schema(request=s.RoundOutcomeSerializer,
               responses=s.RoundParticipationSerializer)
class RoundOutcomeView(_Scoped, APIView):
    permission_classes = [MODULE]

    def post(self, request, pk):
        payload = s.RoundOutcomeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        participation = interview_service.record_outcome(
            round_id=pk, actor=actor, scope=scoping.applications_for(actor),
            **payload.validated_data)
        return Response(s.RoundParticipationSerializer(participation).data)


# -- Offers --------------------------------------------------------------------
class OfferListView(_Scoped, generics.ListAPIView):
    serializer_class = s.OfferSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        return scoping.offers_for(_actor(self.request)).order_by("-created_at")


@extend_schema(request=s.OfferIssueSerializer, responses=s.OfferSerializer)
class OfferIssueView(_Scoped, APIView):
    permission_classes = [MODULE]

    def post(self, request):
        payload = s.OfferIssueSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        actor = _actor(request)
        offer = offer_service.issue(actor=actor,
                                    scope=scoping.applications_for(actor),
                                    **payload.validated_data)
        return Response(s.OfferSerializer(offer).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.OfferRespondSerializer, responses=s.OfferSerializer)
class OfferRespondView(_Scoped, APIView):
    permission_classes = [MODULE, HasPermission("placement_cell.offer.respond")]

    def post(self, request, pk):
        payload = s.OfferRespondSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        offer = offer_service.respond(
            offer_id=pk, accept=payload.validated_data["accept"],
            actor=_actor(request))
        return Response(s.OfferSerializer(offer).data)


# -- Announcements -------------------------------------------------------------
class AnnouncementListView(_Scoped, generics.ListCreateAPIView):
    serializer_class = s.AnnouncementSerializer
    permission_classes = [MODULE]

    def get_queryset(self):
        return scoping.announcements_for(_actor(self.request)).order_by(
            "-published_at", "-created_at")

    def create(self, request, *args, **kwargs):
        payload = s.AnnouncementWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        announcement = announcement_service.publish(actor=_actor(request),
                                                    **payload.validated_data)
        return Response(s.AnnouncementSerializer(announcement).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.WithdrawSerializer, responses=s.AnnouncementSerializer)
class AnnouncementWithdrawView(_Scoped, APIView):
    permission_classes = [MODULE,
                          HasPermission("placement_cell.announcement.publish")]

    def post(self, request, pk):
        payload = s.WithdrawSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        announcement = announcement_service.withdraw(
            announcement_id=pk, actor=_actor(request),
            reason=payload.validated_data["reason"])
        return Response(s.AnnouncementSerializer(announcement).data)


# -- Statistics ----------------------------------------------------------------
@extend_schema(responses=s.StaffStatsSerializer,
               description="Staff receive StaffStats; everyone else receives "
                           "the anonymised StudentStats shape (PC-BR-016).")
class StatsView(_Scoped, APIView):
    """Anonymised aggregates for a student (PC-BR-016), operational figures
    for staff (PC-UC-011/012)."""

    permission_classes = [MODULE]

    def get(self, request):
        actor = _actor(request)
        season = request.query_params.get("season") or _current_season()
        if getattr(actor, "kind", None) != "recruiter" and \
                actor.has_permission(P_VIEW_REPORTS):
            return Response(stats_service.staff_view(season=season))
        return Response(stats_service.student_view(season=season))


def _current_season() -> str:
    policy = PlacementPolicy.objects.filter(is_active=True).order_by(
        "-season").first()
    return policy.season if policy else str(timezone.now().year)


# -- Recruiter portal — the only unauthenticated surface in this module --------
@extend_schema(request=s.RecruiterInviteSerializer,
               responses=s.RecruiterInviteResultSerializer)
class RecruiterInviteView(_Scoped, APIView):
    permission_classes = [MODULE, HasPermission(P_MANAGE_COMPANIES)]

    def post(self, request):
        payload = s.RecruiterInviteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        # Returned once, to the TPO who created it. Not stored.
        account, raw = recruiter_service.invite(
            invited_by_user_id=_actor(request).user_id, **payload.validated_data)
        return Response({"account_id": account.pk, "email": account.email,
                         "invite_token": raw,
                         "expires_at": account.invite_expires_at},
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.RecruiterAcceptSerializer,
               responses=s.DetailSerializer)
class RecruiterAcceptView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    throttle_scope = "recruiter_invite_accept"

    def post(self, request):
        payload = s.RecruiterAcceptSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        recruiter_service.accept_invite(**payload.validated_data)
        return Response({"detail": "Password set. You can now sign in."})


@extend_schema(request=s.RecruiterLoginSerializer,
               responses=s.RecruiterLoginResultSerializer)
class RecruiterLoginView(APIView):
    authentication_classes: list = []
    permission_classes: list = []
    throttle_scope = "recruiter_login"

    def post(self, request):
        payload = s.RecruiterLoginSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            session = recruiter_service.sign_in(
                ip=_client_ip(request), **payload.validated_data)
        except recruiter_service.Locked as exc:
            msg = ("Too many failed attempts. Contact the placement office."
                   if exc.minutes is None else
                   f"Too many failed attempts. Try again in {exc.minutes} minute(s).")
            return Response({"error": {"code": "locked", "message": msg,
                                       "details": [], "request_id": ""}},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)
        response = Response({
            "expires_at": session.expires_at,
            "company_id": session.account.company_id,
            "csrf_token": csrf.token_for(session.raw_key),
        })
        # httpOnly so an XSS cannot exfiltrate it.
        response.set_cookie(
            RECRUITER_COOKIE, session.raw_key,
            max_age=int((session.expires_at - timezone.now()).total_seconds()),
            httponly=True, samesite="Lax", secure=not settings.DEBUG,
            path=RECRUITER_COOKIE_PATH,
        )
        return response


@extend_schema(request=None, responses=s.DetailSerializer)
class RecruiterLogoutView(_Scoped, APIView):
    permission_classes = [MODULE]

    def post(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        key = (auth.split(" ", 1)[1].strip() if auth.startswith("Recruiter ")
               else request.COOKIES.get(RECRUITER_COOKIE, ""))
        if key:
            recruiter_service.sign_out(session_key=key)
        # Already revoked server-side; this stops a shared browser
        # presenting a dead credential.
        response = Response({"detail": "Signed out."})
        response.delete_cookie(RECRUITER_COOKIE, path=RECRUITER_COOKIE_PATH)
        return response


@extend_schema(responses=s.RecruiterMeSerializer)
class RecruiterMeView(_Scoped, APIView):
    """Their company, and nothing about the institute."""

    permission_classes = [MODULE]

    def get(self, request):
        actor = _actor(request)
        if getattr(actor, "kind", None) != "recruiter":
            raise NotFoundError("Not a recruiter session.")
        account = RecruiterAccount.objects.select_related("company").get(
            pk=actor.account_id)
        return Response({
            "csrf_token": csrf.token_for(request.auth or ""),
            "email": account.email, "full_name": account.full_name,
            "company": {"id": account.company_id, "name": account.company.name,
                        "approval_status": account.company.approval_status},
            "modules": list(actor.modules),
        })
