from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.authentication import CookieTokenAuthentication
from iam.authentication import IamServiceAuthentication, IamTokenAuthentication
from iam.services import directory_users, employee_page, search_directory


class DirectoryUsersView(APIView):
    """GET /api/iam/v1/directory/users

        ?ids=1,2,3     batched lookup — the platform's normal path
        ?q=asha&kind=  type-ahead search
        ?employees=1   the whole payroll, paged, for a consumer's projection

    Accepts an ERP-user session, an operator cookie, or a peer service's
    credential — Fusion-Integrated calls this server-to-server as well as on
    behalf of a signed-in user.

    Served entirely from the projection in system_db; the ERP is not
    consulted. See ADR-0014 Phase 1.
    """

    authentication_classes = [IamServiceAuthentication, IamTokenAuthentication,
                              CookieTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        raw_ids = request.query_params.get("ids")
        if raw_ids:
            try:
                ids = [int(x) for x in raw_ids.split(",") if x.strip()]
            except ValueError:
                return Response({"detail": "ids must be comma-separated integers."},
                                status=400)
            return Response({"results": directory_users(ids[:500])})

        if request.query_params.get("employees"):
            return Response(employee_page(
                limit=min(int(request.query_params.get("limit", 500)), 1000),
                offset=int(request.query_params.get("offset", 0)),
            ))

        return Response({"results": search_directory(
            q=request.query_params.get("q", ""),
            kind=request.query_params.get("kind"),
            limit=min(int(request.query_params.get("limit", 25)), 100),
        )})
