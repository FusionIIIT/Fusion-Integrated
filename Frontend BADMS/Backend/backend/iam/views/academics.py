from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import CookieTokenAuthentication
from iam.authentication import (IamServiceAuthentication, IamTokenAuthentication,
                                ServicePrincipal)
from iam.services import academic_directory, academic_filters, academic_standings

MAX_IDS = 500
MAX_PAGE = 200


class AcademicStandingsView(APIView):
    """GET /api/iam/v1/academics/standings?ids=1,2,3

    Declared CPI, earned credits and active backlogs, batched — an eligibility
    sweep asks for every applicant at once. A student with no declared result
    is ABSENT, never zero.

    Narrower than the directory, because a CPI is sensitive academic data
    (PC-BR-023): a service credential may read in bulk, a signed-in student
    may read exactly one row, their own.
    """

    authentication_classes = [IamServiceAuthentication, IamTokenAuthentication,
                              CookieTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        raw = request.query_params.get("ids", "")
        try:
            ids = [int(x) for x in raw.split(",") if x.strip()]
        except ValueError:
            return Response({"detail": "ids must be comma-separated integers."},
                            status=400)
        if not ids:
            return Response({"results": []})

        if not isinstance(request.user, ServicePrincipal):
            # A person may only ever see their own standing. Note this narrows
            # the query rather than rejecting it, so asking about someone else
            # yields an empty result — not a 403 that would confirm the id
            # exists and carries a CPI.
            own = getattr(request.user, "erp_user_id", None)
            ids = [i for i in ids if i == own]

        return Response({"results": academic_standings(ids[:MAX_IDS])})


class AcademicDirectoryView(APIView):
    """GET /api/iam/v1/academics/directory

        ?q=          roll number or name
        ?discipline= CSE, ECE, …
        ?batch_year= 2022
        ?programme=  B.Tech
        ?only_declared=true
        ?limit= &offset=

    The whole cohort's academic standing, for the placement office.

    Narrower than /academics/standings, which answers "what is the CPI of
    these people I already have reason to ask about". This one enumerates
    everybody, so a student cannot reach it at all — their own row comes from
    /me — and it is limited to a peer service or an operator.
    """

    authentication_classes = [IamServiceAuthentication, CookieTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        p = request.query_params
        try:
            limit = min(int(p.get("limit", 50)), MAX_PAGE)
            offset = max(int(p.get("offset", 0)), 0)
            batch_year = int(p["batch_year"]) if p.get("batch_year") else None
        except ValueError:
            return Response({"detail": "limit, offset and batch_year must be "
                                       "integers."}, status=400)

        return Response(academic_directory(
            q=p.get("q", "").strip(),
            discipline=p.get("discipline", "").strip(),
            batch_year=batch_year,
            programme=p.get("programme", "").strip(),
            only_declared=p.get("only_declared") in ("1", "true", "yes"),
            limit=limit, offset=offset,
        ))


class AcademicFiltersView(APIView):
    """The distinct disciplines, batches and programmes actually present, so
    the UI never hard-codes a list that goes stale when a new batch arrives."""

    authentication_classes = [IamServiceAuthentication, CookieTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(academic_filters())
