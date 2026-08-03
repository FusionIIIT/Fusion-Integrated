from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasPermission
from modules.directory import contracts
from modules.directory.api.serializers import UserSearchResultSerializer

MAX_LIMIT = 100

#: Below this a "search" is an enumeration: every name, roll number and
#: institute email in one page.
MIN_QUERY = 2


@extend_schema(responses=UserSearchResultSerializer)
class UserSearchView(APIView):
    """Type-ahead over the local projection. Read-only by construction —
    directory data is owned by IAM and edited there."""

    permission_classes = [HasPermission("directory.user.search")]
    throttle_scope = "directory_search"

    def get(self, request):
        raw = request.query_params.get("limit", 25)
        try:
            limit = min(int(raw), MAX_LIMIT)
        except (TypeError, ValueError) as exc:
            raise BadRequestError("limit must be a number.",
                                  code="invalid_filter") from exc

        q = (request.query_params.get("q") or "").strip()
        if len(q) < MIN_QUERY:
            return Response({"results": []})

        rows = contracts.search(
            q=q,
            kind=request.query_params.get("kind"),
            limit=max(limit, 1),
        )
        return Response({"results": [r.__dict__ for r in rows]})
